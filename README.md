# llm-tools-mcp

> [!WARNING]
> Work in progress!
> Only alpha version was released for now.

[![PyPI](https://img.shields.io/pypi/v/llm-tools-mcp.svg)](https://pypi.org/project/llm-tools-mcp/)
[![Changelog](https://img.shields.io/github/v/release/VirtusLab/llm-tools-mcp?include_prereleases&label=changelog)](https://github.com/VirtusLab/llm-tools-mcp/releases)
[![Tests](https://github.com/VirtusLab/llm-tools-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/VirtusLab/llm-tools-mcp/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/VirtusLab/llm-tools-mcp/blob/main/LICENSE)

MCP support for LLM CLI tool.

<img src="./demo.svg">

## To do

- [x] Release alpha version
- [ ] Good test suite
- [ ] Redirect stdout/stderr from mcp sdk to file or some proper location
- [ ] Reuse stdio connections?
- [ ] Support non-stdio MCP servers
- [ ] Get feedback on `~/.llm-tools-mcp` directory name
- [ ] Better failure handling
    - [ ] When connection to MCP server fails
    - [ ] When `mcp.json` is invalid
- [ ] Better README.md
    - [ ] [Development](#development) section should mention uv (?)

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/).
```bash
llm install llm-tools-mcp
```
## Usage

Usage instructions go here.

## Development

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
