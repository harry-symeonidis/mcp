# Using these servers with LM Studio

LM Studio runs MCP servers itself. Each server listed in its `mcp.json` becomes an
integration (`mcp/<name>`) that you turn on per chat.

## Where the config lives

| OS | Path |
|---|---|
| Windows | `%USERPROFILE%\.lmstudio\mcp.json` |
| macOS / Linux | `~/.lmstudio/mcp.json` |

The file uses the common `mcpServers` format (see [`examples/`](../examples)). LM Studio
picks up changes when the file is saved and creates a plugin folder per server under
`.lmstudio/extensions/plugins/mcp/`. Back the file up before editing it by hand.

## Using a server in a chat

1. Load a model trained for tool use.
2. Turn the integration on for the chat (`mcp/markitdown`, `mcp/git`, `mcp/image`, ...).
3. Ask for the task in plain words. Naming the tool and giving full paths helps smaller
   models, e.g. *"Use convert_to_markdown on file:///C:/docs/report.pdf and summarise it."*

## Things that trip people up

- **Context length.** Tool results go into the context. A browser snapshot or a long
  document can exceed a small context window; the server log then shows
  `request (N tokens) exceeds the available context size`. Load the model with a larger
  context, or ask for smaller pieces.
- **API server authentication.** If you use LM Studio's local API (`http://localhost:1234`)
  from scripts and it answers `invalid_api_key`, either send `Authorization: Bearer <token>`
  or turn authentication off in the server settings.
- **Images from tools.** Image results (for example from `comfyui-image-mcp`) are stored
  in the conversation's working folder under `.lmstudio/`. Whether they display inline and
  reach the model depends on the LM Studio version, so the image server also returns the
  file path.
- **Server logs.** Each MCP server's stderr goes to LM Studio's server log
  (`.lmstudio/server-logs/<yyyy-mm>/`), tagged `Plugin(mcp/<name>)`. Lines tagged `[ERROR]`
  there are often just stderr output, not failures.
- **Child processes.** LM Studio is a Node/Electron app, so a server's detached child
  processes (such as ComfyUI started by `comfyui-image-mcp`) keep running after LM Studio
  stops the server.

## Checking a server outside LM Studio

Use [`tools/mcp_smoke_test.py`](../tools/mcp_smoke_test.py) with the same `mcp.json`:

```sh
python tools/mcp_smoke_test.py --config ~/.lmstudio/mcp.json --server markitdown \
  --call convert_to_markdown --args '{"uri": "file:///C:/docs/report.pdf"}'
```
