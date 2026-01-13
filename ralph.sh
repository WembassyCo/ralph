#!/bin/bash
# Backwards-compatible wrapper for ralph.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Forward all arguments to ralph.py
python "$SCRIPT_DIR/ralph.py" "$@"
