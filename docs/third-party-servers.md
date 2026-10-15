# Third-party MCP servers

These servers are installed from PyPI or npm rather than kept in this repository. This
page records what each one does, how to install it so it keeps working, and the quirks
found while setting them up with local models.

Give every Python server its own virtual environment so their dependencies can't
conflict, and point the client's `command` at the executable inside it. Python 3.12 is a
safe choice. Some optional dependencies may not yet have wheels for the newest Python
releases.

| Server | Purpose | Source | Runtime |
|---|---|---|---|
| [markitdown-mcp](#markitdown-mcp--read-pdf-docx-pptx-xlsx) | Read PDF, DOCX, PPTX, XLSX, HTML as Markdown | PyPI | Python ≥ 3.10 |
| [mcp-server-git](#mcp-server-git--local-git-repositories) | Status, diff, log, stage, commit, branch in local repos | PyPI | Python ≥ 3.10, `git` |
| [server-filesystem](#server-filesystem--read-and-write-files) | Read, write, search files in allowed folders | npm | Node.js |
| [@playwright/mcp](#playwrightmcp--browser-automation) | Drive a real browser | npm | Node.js, Chrome/Edge/Firefox |

---

## markitdown-mcp — read PDF, DOCX, PPTX, XLSX

Microsoft's [MarkItDown](https://github.com/microsoft/markitdown) as an MCP server. It
removes the need to write a one-off extraction script for each document.

Install:

```sh
python -m venv markitdown/.venv
markitdown/.venv/bin/pip install markitdown-mcp "markitdown[pdf,docx,pptx,xlsx]"
```

(Windows: `markitdown\.venv\Scripts\pip`.) The extras pull in the converters for each
format; without them those formats fail to convert.

Config:

```json
"markitdown": { "command": "<dir>/markitdown/.venv/Scripts/markitdown-mcp.exe" }
```

(`.../bin/markitdown-mcp` on Linux/macOS.)

Tool: `convert_to_markdown(uri)`, which accepts `file:`, `http:`, `https:` and `data:` URIs.

Notes:

- Use a `file:///` URI with forward slashes, e.g.
  `file:///C:/docs/report.pdf`. Percent-encoding is handled, so names with spaces and
  non-ASCII characters work.
- It is **not sandboxed**: it reads any path the user account can read, and fetches
  `http(s)` URLs if asked. Limit what you ask it to open, or run it under a restricted account.
- The `markitdown` CLI in the same environment is handy for checking a file outside the
  chat: `markitdown file.pdf`.

## mcp-server-git — local Git repositories

The reference [Git server](https://github.com/modelcontextprotocol/servers/tree/main/src/git).

Install:

```sh
python -m venv git/.venv
git/.venv/bin/pip install mcp-server-git
```

Config:

```json
"git": { "command": "<dir>/git/.venv/Scripts/mcp-server-git.exe" }
```

Add `"args": ["--repository", "<repo>"]` to fix a default repository. Without it, every
tool takes a `repo_path`.

Tools: `git_status`, `git_diff_unstaged`, `git_diff_staged`, `git_diff`, `git_commit`,
`git_add`, `git_reset`, `git_log`, `git_create_branch`, `git_checkout`, `git_show`,
`git_branch`.

Notes:

- There is no push, pull or fetch: nothing leaves the machine until you push yourself.
- Commits use the machine's Git identity (`user.name` / `user.email`), so they look like
  your own commits. Review `git log` before pushing, and ask the model to work on a branch.
- `git` must be on `PATH` (it uses GitPython).
- To let the model *edit* files in a repository, also give the filesystem server access
  to the repository folder.

## server-filesystem — read and write files

The reference [Filesystem server](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem).

Config (folders after the package name are the only ones it may touch):

```json
"filesystem": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "<workspace>", "<repos>"]
}
```

Notes:

- The log line `Client does not support MCP Roots, using allowed directories set from
  server args` is normal for clients without roots support.
- It reads text files only. Use markitdown-mcp for binary documents.

## @playwright/mcp — browser automation

Microsoft's [Playwright MCP](https://github.com/microsoft/playwright-mcp).

Config:

```json
"playwright": {
  "command": "npx",
  "args": ["-y", "@playwright/mcp", "--output-dir", "<workspace>/.playwright-mcp",
           "--file-paths", "absolute"]
}
```

Notes:

- By default it uses the installed **Google Chrome** (`--browser` picks `chrome`,
  `msedge`, `firefox` or `webkit`). The browser window is visible unless you pass `--headless`.
- `browser_navigate` does **not** return the page contents. It saves a snapshot file
  (`.playwright-mcp/page-<timestamp>.yml`) and returns only a link. The model must call
  `browser_snapshot` to read the page. If a model "loads pages but can't see them", that
  is why.
- Without `--output-dir`, those files land in the client's working directory, which the
  model usually can't read. Point `--output-dir` at a folder the filesystem server can read.
- Links in tool results are relative to the client's working directory by default
  (e.g. `..\..\AppData\...`). `--file-paths absolute` makes them full paths that the model
  can pass straight to the filesystem server.
- Snapshots of large pages can be tens of thousands of tokens. Give the model enough
  context length, or use `--snapshot-mode none` and ask for specific elements.
- `--isolated` keeps the browser profile in memory instead of on disk.

## Pinning versions and offline use

`npx -y <package>` asks the npm registry for the latest version **every time the server
starts**. That means a network call on launch, and behaviour can change without notice.
For a reproducible or offline setup, install once and run from the local copy:

```sh
npm install --prefix <dir>/npm @modelcontextprotocol/server-filesystem@<version> @playwright/mcp@<version>
```

```json
"playwright": {
  "command": "node",
  "args": ["<dir>/npm/node_modules/@playwright/mcp/cli.js", "--output-dir", "<workspace>/.playwright-mcp"]
}
```

Check the package's `bin` entry in its `package.json` for the exact script path. For
Python servers, pin with `pip install <package>==<version>`.

## MCP Python SDK 1.x vs 2.x

`mcp` 2.x renamed `FastMCP` to `MCPServer` (`from mcp.server.mcpserver import MCPServer`)
and changed other APIs. Servers and tools written for 1.x, including the ones in this
repository, need `mcp<2`. Installed into an environment that already has 2.x, they fail
with `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`.
