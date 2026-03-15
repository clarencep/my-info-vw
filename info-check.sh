#!/bin/bash

# Info Check CLI entry point

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment and run
cd "$SCRIPT_DIR" 
exec uv run python info-check.py "$@"
