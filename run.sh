#!/bin/bash

# Check if the first argument is "interactive"
if [ "$1" = "interactive" ]; then
    source .venv/bin/activate && python interactive.py
else
    source .venv/bin/activate && python armor.py "$@"
fi

