# mcp-smoke-test

Start any MCP stdio server, list its tools and, optionally, call one. The server comes
from an `mcpServers` JSON file (the format LM Studio's `mcp.json` and ollmcp's
`--servers-json` use) or from a command after `--`.

```text
mcp-smoke-test [--config FILE --server NAME | -- COMMAND ARGS...]
               [--call TOOL] [--args JSON] [--save-dir DIR]
               [--timeout SECONDS] [--max-chars N]
```

It prints the server name and every tool with the first line of its description. With
`--call`, it also prints the result: text is truncated to `--max-chars`, and images are
saved to `--save-dir`.

```sh
# list the tools of a configured server
mcp-smoke-test --config ~/.lmstudio/mcp.json --server markitdown

# call a tool with arguments
mcp-smoke-test --config mcp.json --server git \
  --call git_status --args '{"repo_path": "/path/to/repo"}'

# run a server straight from the command line and save the image it returns
mcp-smoke-test --save-dir out --call generate_image \
  --args '{"prompt": "a lighthouse at dusk"}' -- comfyui-image-mcp
```

On Windows, `npx`-style commands are resolved to their `.cmd` shims automatically.

Without installing, run it as a script: `python tools/mcp_smoke_test.py ...` (needs
`pip install "mcp>=1.20,<2"`).
