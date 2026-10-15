# Contributing

Thanks for your interest. Bug reports, ideas, docs fixes and pull requests are all welcome.

## Getting in touch

| You want to... | Use |
|---|---|
| Ask a question or share a setup | [Discussions](../../discussions) |
| Report something broken | [New issue → Bug report](../../issues/new/choose) |
| Ask for a server, tool or doc | [New issue → Feature request](../../issues/new/choose) |
| Report a security problem | Privately, as described in [SECURITY.md](SECURITY.md) |

For bugs, include the client (LM Studio / ollmcp / other) and its version, the OS, the
server involved, and the output of `tools/mcp_smoke_test.py` for that server if you can.

## Pull requests

1. Fork the repository and create a branch from `main`.
2. Make a focused change: one fix or feature per pull request.
3. Test it (see below) and update the docs it affects.
4. Open the pull request and describe what changed and why.

Signed commits are welcome but not required. Contributions are accepted under the
[MIT License](LICENSE).

## Development setup

```sh
python -m venv .venv
.venv/bin/pip install -e ./servers/comfyui-image     # Windows: .venv\Scripts\pip
```

The editable install also provides the MCP SDK that `tools/mcp_smoke_test.py` needs.

## Testing

There is no unit-test suite yet. Exercise changes through MCP with the smoke-test tool:

```sh
# the image server's tools are listed and callable
python tools/mcp_smoke_test.py -- .venv/bin/comfyui-image-mcp
python tools/mcp_smoke_test.py --call generate_image --args '{"prompt": "test", "steps": 4}' \
  --save-dir out -- .venv/bin/comfyui-image-mcp

# an example config still works
python tools/mcp_smoke_test.py --config examples/mcp.posix.json --server git
```

If you change behaviour on one OS, say which platforms you tested in the pull request.

## Guidelines

- **Local first.** Servers here must not send prompts, files or results anywhere except
  the local service they front. No telemetry, no cloud APIs, no account requirements.
  Bind to loopback by default.
- **Few dependencies.** `comfyui-image-mcp` depends only on the MCP SDK and the standard
  library. Keep it that way unless there's a strong reason not to.
- **MCP SDK 1.x.** The code uses `mcp.server.fastmcp` and needs `mcp<2`. A port to 2.x
  is welcome as its own pull request.
- **Configuration through environment variables**, with sensible defaults and no
  hard-coded paths. Document new variables in the server's README table.
- **Match the existing style**: standard-library `urllib`, short docstrings that tell the
  model how to use each tool, comments only where the code isn't obvious.
- **Docs for third-party servers** should be checked against the upstream project. Note
  the version you tested if behaviour differs between releases.
