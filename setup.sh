#!/bin/bash

set -eu

main() {
  echo "[eulith] Initializing virtual environment"
  python3 -m venv .venv
  source .venv/bin/activate
  echo "[eulith] Installing dependencies"
  pip install --upgrade pip
  pip install eulith-web3
  echo "[eulith] Installed dependencies"
  echo
  echo
  echo "You are ready to go! See the README for further instructions."
}

main "$@"
