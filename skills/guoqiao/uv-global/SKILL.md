---
name: uv-global
description: Create a global uv environment as python playground or workbench.
metadata: {"openclaw":{"always":true,"emoji":"🦞","homepage":"https://github.com/guoqiao/skills/blob/main/uv-global/uv-global/SKILL.md","os":["darwin","linux"],"tags":["python","uv","global","venv"],"requires":{"anyBins":["brew","uv"]}}}
---

# UV Global

Create a global uv environment as python playground or workbench at `~/.uv-global`.
Lighnting Fast, freedom to install needed dependencies for your tasks, without polluting your system.

When the user asks for complex data processing, web scraping, or any task requiring Python libraries not available in the base system, use this skill to create and run scripts in a managed environment

## Requirements

- `uv` or `brew`

## Installation

```bash
bash ${baseDir}/uv-global.sh
```
This script will:
- use `brew` or `curl` to install `uv` if not available
- create a global uv project at `~/.uv-global`
- create a virtual env with common packages in `~/.uv-global/.venv`

Ideally but optional: prepend the venv bin to your $PATH, so you will be using python from here by default:

```
export PATH=~/.uv-global/.venv/bin:$PATH
```

## Usage

Whenever you are writing a python script which requires extra dependencies:

```bash
# install deps into this global env and use them in script
uv --project ~/.uv-global add <pkg0> <pkg1> ...

#  write your code
touch script.py

# run your script
uv --project ~/.uv-global run script.py
```