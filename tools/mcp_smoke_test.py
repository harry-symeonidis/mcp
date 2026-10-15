"""Smoke-test an MCP stdio server: start it, list its tools, optionally call one.

The server comes either from an mcpServers JSON file (the format LM Studio's
mcp.json and ollmcp's --servers-json use) or from a command after "--".

Examples:
  python mcp_smoke_test.py --config ~/.lmstudio/mcp.json --server markitdown
  python mcp_smoke_test.py --config mcp.json --server git \
      --call git_status --args '{"repo_path": "/path/to/repo"}'
  python mcp_smoke_test.py --save-dir out --call generate_image \
      --args '{"prompt": "a lighthouse at dusk"}' -- comfyui-image-mcp
  python mcp_smoke_test.py -- npx -y @playwright/mcp --headless

Requires the MCP Python SDK: pip install "mcp>=1.20,<2"
"""

import argparse
import asyncio
import base64
import json
import os
import shutil
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def load_server(config, name):
    servers = json.loads(Path(config).expanduser().read_text(encoding="utf-8")).get(
        "mcpServers", {})
    if name not in servers:
        sys.exit(f"{name!r} is not in {config}; available: {', '.join(servers) or 'none'}")
    entry = servers[name]
    if "command" not in entry:
        sys.exit(f"{name!r} is not a stdio server (it has no 'command')")
    return entry["command"], entry.get("args", []), entry.get("env")


def resolve(command):
    # On Windows, "npx" and similar are .cmd shims. Look for those explicitly:
    # shutil.which("npx") can return the extensionless Unix shell script that npm
    # installs alongside, which Windows cannot execute.
    if os.name != "nt" or Path(command).suffix:
        return command
    for ext in (".exe", ".cmd", ".bat"):
        found = shutil.which(command + ext)
        if found:
            return found
    return command


def is_error(result):
    # The SDK has exposed this as both isError and is_error across versions.
    return bool(getattr(result, "is_error", None) or getattr(result, "isError", False))


def report(result, max_chars, save_dir):
    print(f"  error: {is_error(result)}")
    for i, block in enumerate(result.content):
        if block.type == "text":
            text = block.text
            more = f" ... ({len(text)} chars total)" if len(text) > max_chars else ""
            print(f"  [text] {text[:max_chars]}{more}")
        elif block.type == "image":
            raw = base64.b64decode(block.data)
            line = f"  [image] {block.mimeType}, {len(raw):,} bytes"
            if save_dir:
                ext = block.mimeType.split("/")[-1]
                path = Path(save_dir) / f"result-{int(time.time())}-{i}.{ext}"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                line += f" -> {path}"
            print(line)
        else:
            print(f"  [{block.type}]")


async def run(command, args, env, call, call_args, timeout, max_chars, save_dir):
    params = StdioServerParameters(command=resolve(command), args=args, env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"server: {init.serverInfo.name} {init.serverInfo.version}")
            tools = (await session.list_tools()).tools
            print(f"{len(tools)} tools:")
            for tool in tools:
                summary = (tool.description or "").strip().splitlines()
                print(f"  {tool.name}: {summary[0] if summary else ''}")
            if call:
                print(f"\ncalling {call} {json.dumps(call_args)}")
                start = time.time()
                result = await asyncio.wait_for(session.call_tool(call, call_args), timeout)
                print(f"  took {time.time() - start:.1f}s")
                report(result, max_chars, save_dir)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n", 1)[0],
        epilog="Put a server command after -- instead of using --config/--server.")
    parser.add_argument("--config", help="JSON file with an mcpServers object")
    parser.add_argument("--server", help="server name in --config")
    parser.add_argument("--call", help="tool to call after listing tools")
    parser.add_argument("--args", default="{}", help="tool arguments as a JSON object")
    parser.add_argument("--timeout", type=float, default=900, help="seconds for the call")
    parser.add_argument("--max-chars", type=int, default=2000, help="text shown per block")
    parser.add_argument("--save-dir", help="save returned images here")
    parser.add_argument("command", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    opts = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    command = opts.command[1:] if opts.command[:1] == ["--"] else opts.command
    if command:
        cmd, args, env = command[0], command[1:], None
    elif opts.config and opts.server:
        cmd, args, env = load_server(opts.config, opts.server)
    else:
        parser.error("give --config and --server, or a command after --")

    asyncio.run(run(cmd, args, env, opts.call, json.loads(opts.args), opts.timeout,
                    opts.max_chars, opts.save_dir))


if __name__ == "__main__":
    main()
