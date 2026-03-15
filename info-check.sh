#/bin/bash

cd $(dirname `realpath $0`) && source .venv/bin/activate && exec uv run ./info-check.py "$@"

