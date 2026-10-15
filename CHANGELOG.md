# Changelog

All notable changes are listed here. Versions follow [Semantic Versioning](https://semver.org);
both packages (`comfyui-image-mcp` and `mcp-smoke-test`) are released together under one tag.

## [0.1.0] - 2026-10-15

First release.

### Added

- **comfyui-image-mcp**: an MCP server that generates images with a local ComfyUI.
  - Tools: `generate_image`, `list_checkpoints`, `free_image_memory`.
  - Configured through environment variables, with no hard-coded paths.
  - Starts ComfyUI on demand (loopback only, `--offline`) and leaves it running so the
    model stays loaded between sessions.
  - Returns the image to the client and reports where it was saved.
- **mcp-smoke-test**: starts any stdio MCP server from an `mcpServers` file or a command
  line, lists its tools, calls one, and saves any images it returns.
- Guides for the third-party servers (markitdown, Git, filesystem, Playwright), for
  ComfyUI with AMD ROCm on Windows, and for LM Studio and Ollama.
- Example `mcpServers` configs for Windows and Linux/macOS.

[0.1.0]: https://github.com/harry-symeonidis/mcp/releases/tag/v0.1.0
