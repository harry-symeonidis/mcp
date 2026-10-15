# Using these servers with Ollama

Ollama serves models; it does not launch MCP servers itself. Put an MCP-capable client
between you and Ollama. Two that read the same `mcpServers` JSON as LM Studio:

- **[ollmcp](https://github.com/jonigl/mcp-client-for-ollama)**, an interactive terminal
  client for Ollama models with MCP tools.
- **[ollama-mcp-bridge](https://github.com/jonigl/ollama-mcp-bridge)**, an API proxy in
  front of Ollama that adds MCP tools to every chat request, so existing Ollama clients
  get the tools.

## ollmcp

```sh
pip install --upgrade ollmcp        # or: uv tool install --upgrade ollmcp
ollmcp --servers-json examples/mcp.posix.json --model <model>
```

- `--servers-json` / `-j` takes a file with a top-level `mcpServers` object. stdio
  entries use `command`, `args`, `env` and `disabled`.
- `--host` / `-H` points at a non-default Ollama (default `http://localhost:11434`).
- `/model` switches models during a session.

Pick a model trained for tool calling; models without tool support ignore the tools.

## Notes

- Everything in [third-party-servers.md](third-party-servers.md) and the
  [image server README](../servers/comfyui-image/README.md) applies unchanged. Only the
  client differs.
- Clients written in Python start servers with the Python MCP SDK. On Windows that SDK
  kills the server's whole process tree when the session ends, so ComfyUI auto-started by
  `comfyui-image-mcp` stops with the session. Start ComfyUI yourself if you want the
  model to stay loaded between sessions.
- Ollama and an image model share the GPU. Call `free_image_memory` before loading a
  large language model.
