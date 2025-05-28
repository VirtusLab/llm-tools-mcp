# llm-tools-mcp

> [!WARNING]
> **Work in progress!**  
> Only an alpha version has been released so far.  
> **Please refrain from using it unless you know what you're doing.**  
> If you *do* decide to try it, make sure to use the `--ta` flag (manual approval required for every tool execution).

[![PyPI](https://img.shields.io/pypi/v/llm-tools-mcp.svg)](https://pypi.org/project/llm-tools-mcp/)
[![Changelog](https://img.shields.io/github/v/release/VirtusLab/llm-tools-mcp?include_prereleases&label=changelog)](https://github.com/VirtusLab/llm-tools-mcp/releases)
[![Tests](https://github.com/VirtusLab/llm-tools-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/VirtusLab/llm-tools-mcp/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/VirtusLab/llm-tools-mcp/blob/main/LICENSE)

MCP support for the LLM CLI tool.

<img src="./demo.svg" alt="Demo" />

## To Do

- [x] Release alpha version
- [ ] Build a solid test suite
  - [x] test sse with dummy server
  - [ ] test stdio with dummy server
  - [x] test http streamable with dummy server ([see #1](https://github.com/Virtuslab/llm-tools-mcp/issues/1))
  - [ ] test sse with real server
  - [x] test stdio with real server
  - [ ] test http streamable with real server
- [x] Redirect `stdout`/`stderr` from the MCP SDK to a file or designated location
- [ ] Reuse stdio connections
- [x] **Support non-stdio MCP servers**
- [ ] Handle tool name conflicts (prefix with mcp server name?)
- [ ] Gather feedback on the `~/.llm-tools-mcp` directory naming
- [ ] Improve failure handling:
  - [ ] When connecting to an MCP server fails
  - [ ] When `mcp.json` is malformed
- [ ] Improve this README:
  - [ ] Add more detail in the [Development](#development) section (mention `uv`?)

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/):

```bash
llm install llm-tools-mcp
```
## Usage

> [!WARNING]
> **Work in progress!**  
> Only an alpha version has been released so far.  
> **Please refrain from using it unless you know what you're doing.**  
> If you *do* decide to try it, make sure to use the `--ta` flag (manual approval required for every tool execution).

1. Create `mcp.json` file in `~/.llm-tols-mcp`
2. Run `llm`, for example:
    `llm --ta -T read_file -T list_allowed_directories -T list_directory "what files are in the demo directory? show me contents of one of the files (any)"`


## Development

### Now (to be verified)

- Sync dependencies: `uv sync --all-extras`
- Run linters / type checker: `./check.sh`
- Run tests: `./test.sh`

### Before

To set up this plugin locally, first checkout the code. Then create a new virtual environment:
```bash
cd llm-tools-mcp
python -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
python -m pip install -e '.[test]'
```
To run the tests:
```bash
python -m pytest
```
