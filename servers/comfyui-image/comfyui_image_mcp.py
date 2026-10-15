"""MCP server that generates images with a local ComfyUI instance.

Exposes generate_image, list_checkpoints and free_image_memory over stdio. It
talks only to ComfyUI at COMFYUI_URL (default http://127.0.0.1:8188) and, when
COMFYUI_DIR is set, starts ComfyUI on demand and leaves it running so the model
stays loaded between client sessions.

Configuration (environment variables):
  COMFYUI_URL               ComfyUI address (default http://127.0.0.1:8188)
  COMFYUI_DIR               ComfyUI checkout; enables auto-start when set
  COMFYUI_PYTHON            Python that runs ComfyUI (default: a .venv/venv in or
                            next to COMFYUI_DIR)
  COMFYUI_EXTRA_ARGS        extra ComfyUI flags for auto-start, e.g. "--highvram"
  COMFYUI_LOG               ComfyUI log file (default <COMFYUI_DIR>/comfyui-mcp.log)
  IMAGE_OUTPUT_DIR          ComfyUI output directory (passed on auto-start and
                            used to report file paths)
  DEFAULT_CHECKPOINT        checkpoint file name (default sd_xl_base_1.0.safetensors)
  COMFYUI_STARTUP_TIMEOUT   seconds to wait for ComfyUI to start (default 300)
  COMFYUI_GENERATE_TIMEOUT  seconds to wait for one image (default 900)
"""

import json
import os
import random
import shlex
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Image

COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
COMFYUI_DIR = os.environ.get("COMFYUI_DIR")
COMFYUI_PYTHON = os.environ.get("COMFYUI_PYTHON")
COMFYUI_EXTRA_ARGS = shlex.split(os.environ.get("COMFYUI_EXTRA_ARGS", ""), posix=os.name != "nt")
COMFYUI_LOG = os.environ.get("COMFYUI_LOG")
OUTPUT_DIR = os.environ.get("IMAGE_OUTPUT_DIR")
DEFAULT_CHECKPOINT = os.environ.get("DEFAULT_CHECKPOINT", "sd_xl_base_1.0.safetensors")
STARTUP_TIMEOUT = int(os.environ.get("COMFYUI_STARTUP_TIMEOUT", "300"))
GENERATE_TIMEOUT = int(os.environ.get("COMFYUI_GENERATE_TIMEOUT", "900"))

# Loopback only; --offline disables the paid partner/API nodes and blocks the
# web UI from reaching the internet.
BASE_ARGS = ["--listen", "127.0.0.1", "--offline", "--disable-auto-launch"]

mcp = FastMCP("comfyui-image")
_comfy_proc = None


def _request(path, payload=None, timeout=10):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        COMFYUI_URL + path, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    return json.loads(body) if body else {}


def _comfy_running():
    try:
        _request("/system_stats", timeout=3)
        return True
    except (urllib.error.URLError, OSError):
        return False


def _comfy_python(comfy_dir):
    if COMFYUI_PYTHON:
        return COMFYUI_PYTHON
    exe = Path("Scripts", "python.exe") if os.name == "nt" else Path("bin", "python")
    for venv in (comfy_dir / ".venv", comfy_dir / "venv", comfy_dir.parent / ".venv"):
        if (venv / exe).exists():
            return str(venv / exe)
    raise RuntimeError("Set COMFYUI_PYTHON to the Python environment that has ComfyUI installed")


def _launch_comfy():
    comfy_dir = Path(COMFYUI_DIR).expanduser()
    port = urllib.parse.urlparse(COMFYUI_URL).port or 8188
    cmd = [_comfy_python(comfy_dir), "main.py", "--port", str(port), *BASE_ARGS]
    if OUTPUT_DIR:
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        cmd += ["--output-directory", OUTPUT_DIR]
    cmd += COMFYUI_EXTRA_ARGS
    log_path = Path(COMFYUI_LOG) if COMFYUI_LOG else comfy_dir / "comfyui-mcp.log"
    log = open(log_path, "ab")  # pylint: disable=consider-using-with
    common = {"cwd": comfy_dir, "stdout": log, "stderr": subprocess.STDOUT,
              "stdin": subprocess.DEVNULL}

    if os.name != "nt":
        return subprocess.Popen(cmd, start_new_session=True, **common)

    # Break away from the client's job object so ComfyUI outlives this server.
    # Clients whose job forbids breakaway (e.g. the Python MCP SDK) refuse this;
    # ComfyUI then stops when the client closes the server.
    base_flags = (subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
                  | subprocess.CREATE_NEW_PROCESS_GROUP)
    for flags in (base_flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, base_flags):
        try:
            return subprocess.Popen(cmd, creationflags=flags, **common)
        except PermissionError:
            continue
    raise RuntimeError("Could not start ComfyUI")


def _ensure_comfy():
    """Make sure ComfyUI answers at COMFYUI_URL, starting it if allowed."""
    global _comfy_proc  # pylint: disable=global-statement
    if _comfy_running():
        return
    if not COMFYUI_DIR:
        raise RuntimeError(f"ComfyUI is not running at {COMFYUI_URL}; start it, or set "
                           "COMFYUI_DIR so this server can start it")
    # Reuse a launch that is still starting instead of starting a second copy.
    if _comfy_proc is None or _comfy_proc.poll() is not None:
        _comfy_proc = _launch_comfy()
    deadline = time.time() + STARTUP_TIMEOUT
    while time.time() < deadline:
        if _comfy_running():
            return
        if _comfy_proc.poll() is not None:
            raise RuntimeError("ComfyUI exited during startup; check its log")
        time.sleep(2)
    raise RuntimeError(f"ComfyUI did not start within {STARTUP_TIMEOUT}s; check its log")


def _txt2img_workflow(prompt, negative_prompt, width, height, steps, cfg, seed,
                      sampler, scheduler, checkpoint):
    return {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"width": width, "height": height, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode",
              "inputs": {"text": negative_prompt, "clip": ["4", 1]}},
        "3": {"class_type": "KSampler",
              "inputs": {"seed": seed, "steps": steps, "cfg": cfg, "sampler_name": sampler,
                         "scheduler": scheduler, "denoise": 1.0, "model": ["4", 0],
                         "positive": ["6", 0], "negative": ["7", 0],
                         "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"filename_prefix": "mcp", "images": ["8", 0]}},
    }


def _fetch_image(img):
    query = urllib.parse.urlencode({"filename": img["filename"],
                                    "subfolder": img.get("subfolder", ""),
                                    "type": img.get("type", "output")})
    with urllib.request.urlopen(f"{COMFYUI_URL}/view?{query}", timeout=60) as resp:
        return resp.read()


def _image_location(img):
    rel = Path(img.get("subfolder", ""), img["filename"])
    return str(Path(OUTPUT_DIR) / rel) if OUTPUT_DIR else f"ComfyUI output/{rel.as_posix()}"


@mcp.tool()
def generate_image(
    prompt: str,
    negative_prompt: str = "blurry, low quality, distorted, watermark, text",
    width: int = 1024,
    height: int = 1024,
    steps: int = 25,
    cfg: float = 7.0,
    seed: int = -1,
    sampler: str = "euler",
    scheduler: str = "normal",
    checkpoint: str = "",
) -> list:
    """Generate an image locally from a text prompt and save it as a PNG.

    Write the prompt as a detailed visual description (subject, style, lighting,
    composition). Width and height are rounded down to multiples of 64; SDXL
    models work best around 1024x1024. seed=-1 picks a random seed; reuse a seed
    to reproduce or vary an image. checkpoint defaults to the configured model;
    list_checkpoints shows the installed ones. Returns the image and where it
    was saved.
    """
    _ensure_comfy()
    seed = random.randint(0, 2**32 - 1) if seed < 0 else seed
    width, height = max(64, width // 64 * 64), max(64, height // 64 * 64)
    workflow = _txt2img_workflow(prompt, negative_prompt, width, height, steps, cfg, seed,
                                 sampler, scheduler, checkpoint or DEFAULT_CHECKPOINT)
    try:
        prompt_id = _request("/prompt", {"prompt": workflow,
                                         "client_id": str(uuid.uuid4())})["prompt_id"]
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:800]
        raise RuntimeError(f"ComfyUI rejected the job: {detail}") from e

    deadline = time.time() + GENERATE_TIMEOUT
    while time.time() < deadline:
        history = _request(f"/history/{prompt_id}")
        if prompt_id in history:
            entry = history[prompt_id]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                raise RuntimeError(
                    f"ComfyUI job failed: {json.dumps(status.get('messages'))[:800]}")
            images = entry.get("outputs", {}).get("9", {}).get("images", [])
            if images:
                img = images[0]
                return [
                    f"Saved {_image_location(img)} ({width}x{height}, {steps} steps, "
                    f"seed {seed})",
                    Image(data=_fetch_image(img), format="png"),
                ]
        time.sleep(1)
    raise RuntimeError(f"Image not ready after {GENERATE_TIMEOUT}s (prompt_id {prompt_id})")


@mcp.tool()
def list_checkpoints() -> list[str]:
    """List the image models (checkpoints) installed in ComfyUI."""
    _ensure_comfy()
    info = _request("/object_info/CheckpointLoaderSimple")
    return info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]


@mcp.tool()
def free_image_memory() -> str:
    """Unload the image model from GPU memory (ComfyUI keeps running).

    Use this before loading a large language model; the next generate_image
    call reloads the image model automatically.
    """
    if not _comfy_running():
        return "ComfyUI is not running; nothing to free."
    _request("/free", {"unload_models": True, "free_memory": True})
    return "Image model unloaded from GPU memory."


def main():
    mcp.run()


if __name__ == "__main__":
    main()
