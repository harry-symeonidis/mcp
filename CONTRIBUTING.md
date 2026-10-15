# Contributing

Thanks for your interest. Bug reports, ideas, docs fixes and pull requests are all welcome.
Everyone taking part is expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

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

`main` is protected. Every change, including the maintainers', goes in through a pull
request that passes CI and gets an approving review.

1. Fork the repository and create a branch from `main`, named as below.
2. Make a focused change: one fix or feature per pull request.
3. Test it (see below), update the docs it affects, and add a line to the
   `Unreleased` section of [CHANGELOG.md](CHANGELOG.md) (create the section if it's missing).
4. Open the pull request and describe what changed and why.

### Branch names

CI rejects pull requests from branches that don't follow this convention:

| Prefix | Use for | Example |
|---|---|---|
| `feature/` | New servers, tools or options | `feature/whisper-transcription` |
| `bugfix/` | Fixes for something broken | `bugfix/windows-npx-resolution` |
| `hotfix/` | Urgent fixes to a released version | `hotfix/0.1.1-startup-crash` |
| `issue/` | Work tied to an issue (start with its number) | `issue/42-flux-workflow` |
| `docs/` | Documentation only | `docs/ollama-open-webui` |
| `chore/` | CI, packaging, refactoring | `chore/bump-checkout-action` |
| `release/` | Preparing a release (maintainers) | `release/0.2.0` |

After the prefix, use letters, digits, `.`, `_`, `-` and `/`, e.g. lowercase words
separated by hyphens.

Signed commits are welcome but not required. Contributions are accepted under the
[MIT License](LICENSE).

## Development setup

```sh
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt     # Windows: .venv\Scripts\pip
```

This gives you the `comfyui-image-mcp` and `mcp-smoke-test` commands, both running from
your checkout.

## Testing

There is no unit-test suite yet. CI builds both packages on Linux, Windows and macOS,
checks that `comfyui-image-mcp` lists its tools and reports a missing ComfyUI cleanly,
and validates the example configs. Locally, exercise changes through MCP:

```sh
# the image server's tools are listed and callable
mcp-smoke-test -- comfyui-image-mcp
mcp-smoke-test --call generate_image --args '{"prompt": "test", "steps": 4}' \
  --save-dir out -- comfyui-image-mcp

# an example config still works
mcp-smoke-test --config examples/mcp.posix.json --server git
```

If you change behaviour on one OS, say which platforms you tested in the pull request.

## Releases (maintainers)

1. On a `release/<version>` branch, set `version` in `servers/comfyui-image/pyproject.toml`
   and `tools/pyproject.toml`, and rename the changelog's `Unreleased` section to
   `## [<version>] - <date>` with a link at the bottom.
2. Merge the pull request.
3. Tag `main` and push the tag: `git tag -s v<version> -m "v<version>"` then
   `git push origin v<version>`.

The Release workflow checks that the tag matches both package versions, builds the
wheels and source archives, smoke-tests them, and publishes a GitHub release with the
files, `SHA256SUMS` and the changelog section as notes. Only maintainers can create
`v*` tags.

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
