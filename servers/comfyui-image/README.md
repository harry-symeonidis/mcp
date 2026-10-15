# comfyui-image-mcp

An MCP server that gives a chat model one simple image tool backed by a local
[ComfyUI](https://github.com/comfyanonymous/ComfyUI). The model passes a text prompt;
the server builds a fixed text-to-image workflow, runs it, and returns the PNG.

It talks only to ComfyUI on the address you configure (loopback by default), and when
it starts ComfyUI itself it binds it to `127.0.0.1` with `--offline`.

## Tools

| Tool | What it does |
|---|---|
| `generate_image(prompt, negative_prompt, width, height, steps, cfg, seed, sampler, scheduler, checkpoint)` | Runs text-to-image and returns the image plus where it was saved. Only `prompt` is required. |
| `list_checkpoints()` | Lists the checkpoint files ComfyUI can load. |
| `free_image_memory()` | Unloads models from GPU memory; ComfyUI keeps running. |

The workflow is a standard single-checkpoint pipeline (checkpoint → CLIP text encode →
KSampler → VAE decode → save), so it works with SDXL and SD 1.5 style checkpoints.
Models that need separate text encoders or UNet loaders (Flux, SD3, and so on) need a
different workflow.

## 1. Install ComfyUI

ComfyUI and PyTorch are large downloads and are not part of this repository. Install them
in their own virtual environment, separate from this server.

### AMD Radeon / Ryzen AI on Windows (ROCm)

Based on AMD's guide
[Local Image and Video Generation on AMD Ryzen AI Max+ (Windows)](https://rocm.blogs.amd.com/artificial-intelligence/comfyui-windows/README.html).
Needs a recent AMD Adrenalin driver and **Python 3.12** (AMD's Windows wheels are `cp312` only).

```powershell
py -3.12 -m venv comfyui-venv
.\comfyui-venv\Scripts\python.exe -m pip install --upgrade pip wheel

# ROCm PyTorch from AMD's repository. Use -f (find-links), not --index-url.
.\comfyui-venv\Scripts\python.exe -m pip install `
    -f https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1/ `
    "torch==2.9.1+rocm7.2.1" "torchvision==0.24.1+rocm7.2.1" "torchaudio==2.9.1+rocm7.2.1" `
    numpy pillow

git clone https://github.com/comfyanonymous/ComfyUI.git

# ComfyUI's requirements.txt lists torch unpinned, which can pull the CUDA build from PyPI.
# Pin the ROCm packages and install everything else.
.\comfyui-venv\Scripts\python.exe -m pip freeze |
    Select-String "^(torch|torchvision|torchaudio|rocm)" | ForEach-Object { $_.Line } |
    Out-File -Encoding utf8 torch-pin.txt
.\comfyui-venv\Scripts\python.exe -m pip install -c torch-pin.txt -r ComfyUI\requirements.txt
```

Check that the GPU is used:

```powershell
.\comfyui-venv\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

It should print a `+rocm` version, `True` and your Radeon GPU. If it prints `False`, pip
replaced the ROCm build; repeat the ROCm install command. Keep `-c torch-pin.txt` on every
later `pip install -r ComfyUI\requirements.txt`.

### NVIDIA, CPU, Linux and macOS

Follow the [ComfyUI installation instructions](https://github.com/comfyanonymous/ComfyUI#installing):
install the PyTorch build for your platform from [pytorch.org](https://pytorch.org/get-started/locally/),
then `pip install -r requirements.txt` in the ComfyUI checkout.

## 2. Add a model

Put a checkpoint in `ComfyUI/models/checkpoints/`. The server defaults to SDXL base 1.0,
which downloads without an account:

```sh
curl -L -o ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors \
  https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
```

Its SHA-256 is `31e35c80fc4829d14f90153f4c74cd59c90b779f6afe05a74cd6120b893f7e5b` (about 6.5 GB).
Download manually rather than through ComfyUI's model downloader, which can put files in
the wrong folder.

## 3. Install this server

Use a separate small environment (it needs only the MCP SDK):

```sh
python -m venv .venv
.venv/bin/pip install ./servers/comfyui-image          # Windows: .venv\Scripts\pip
```

This installs the `comfyui-image-mcp` command into that environment.

## 4. Configure your MCP client

Run `comfyui-image-mcp` as a stdio server. With `COMFYUI_DIR` set, it starts ComfyUI on
the first tool call and leaves it running, so the model stays loaded for later chats.
Without it, start ComfyUI yourself.

| Variable | Default | Purpose |
|---|---|---|
| `COMFYUI_URL` | `http://127.0.0.1:8188` | ComfyUI address |
| `COMFYUI_DIR` | (unset) | ComfyUI checkout; enables auto-start |
| `COMFYUI_PYTHON` | a `.venv` or `venv` in or next to `COMFYUI_DIR` | Python that has ComfyUI installed |
| `COMFYUI_EXTRA_ARGS` | (empty) | Extra ComfyUI flags for auto-start |
| `COMFYUI_LOG` | `<COMFYUI_DIR>/comfyui-mcp.log` | ComfyUI log when auto-started |
| `IMAGE_OUTPUT_DIR` | ComfyUI's `output/` | Where ComfyUI saves images (used on auto-start and in the reply) |
| `DEFAULT_CHECKPOINT` | `sd_xl_base_1.0.safetensors` | Checkpoint used when the model doesn't name one |
| `COMFYUI_STARTUP_TIMEOUT` | `300` | Seconds to wait for ComfyUI to start |
| `COMFYUI_GENERATE_TIMEOUT` | `900` | Seconds to wait for one image |

Example `mcpServers` entry (Windows paths; use `bin/comfyui-image-mcp` on Linux/macOS):

```json
"image": {
  "command": "C:\\mcp\\comfyui-image\\.venv\\Scripts\\comfyui-image-mcp.exe",
  "env": {
    "COMFYUI_DIR": "C:\\mcp\\comfyui\\ComfyUI",
    "COMFYUI_PYTHON": "C:\\mcp\\comfyui\\comfyui-venv\\Scripts\\python.exe",
    "IMAGE_OUTPUT_DIR": "C:\\mcp\\images"
  }
}
```

ComfyUI's first start after installation can take several minutes (Python compiles its
files and antivirus scans the new GPU libraries). Later starts take about 20 seconds.

## Performance notes

On integrated GPUs with unified memory (for example AMD Ryzen AI Max), ComfyUI's default
RAM-pressure cache can unload the model after every image, so each image pays the full
load time again. These flags keep it loaded and stop weights streaming during sampling:

```
COMFYUI_EXTRA_ARGS=--highvram --cache-classic --disable-async-offload --disable-dynamic-vram
```

On a Radeon 8060S (Windows, balanced power mode) this took a warm SDXL 1024×1024,
25-step image from about 85 s to about 35–55 s. On discrete GPUs with little VRAM, leave
`--highvram` out. Use `free_image_memory` before loading a large language model on the
same GPU.

Laptop power modes matter: GPU clocks follow the OS power mode, so expect longer times on
battery or in power-saving modes.

## Process lifetime

The server launches ComfyUI as a detached process so it survives the MCP session.

- **Node-based clients (LM Studio and others):** ComfyUI keeps running after the client
  closes the server.
- **Clients built on the Python MCP SDK:** on Windows these place the server in a job
  object that kills all child processes and forbids breakaway, so ComfyUI stops with the
  session. Start ComfyUI yourself (and leave `COMFYUI_DIR` unset) if you need it to persist.

To stop ComfyUI, end the process listening on its port, for example in PowerShell:

```powershell
Get-NetTCPConnection -LocalPort 8188 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess }
```

## Network behaviour

- The server contacts only `COMFYUI_URL`.
- Auto-started ComfyUI listens on `127.0.0.1` only. `--offline` disables the paid
  partner/API nodes and sets a Content-Security-Policy that stops the web UI from reaching
  the internet.
- Prompts and images never leave the machine. The internet is needed only to download
  ComfyUI, PyTorch and models.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `ComfyUI is not running at ...` | Start ComfyUI, or set `COMFYUI_DIR` so the server can start it. |
| `ComfyUI rejected the job: ... ckpt_name ...` | The checkpoint isn't installed; check `list_checkpoints`. |
| `ComfyUI exited during startup` | Read the log (`COMFYUI_LOG`). A common cause is port 8188 already in use. |
| `unrecognized arguments: --offline` | ComfyUI is too old; update it (`git pull`, then reinstall requirements with the pin). |
| Images are black | Try `COMFYUI_EXTRA_ARGS=--fp32-vae`. |
