#!/bin/zsh
# Holy Pokemon authorized read-only monitoring launcher. No automated bidding.
set -eu
cd "$(dirname "$0")/.."
if [[ -x .venv/bin/python ]]; then
  PY=.venv/bin/python
else
  PY=python3
fi
SECRET_PATH="$HOME/.config/holy_pokemon/ebay.json"
if [[ -f "$SECRET_PATH" ]]; then
  echo "Starting read-only Holy Pokemon monitoring with private credentials file..."
  exec "$PY" -m holy_pokemon.automated_discovery --live --authorized-keyset \
    --credentials-file "$SECRET_PATH" --sync-app --notify-mac --watch
else
  echo "No private eBay keyset found at ~/.config/holy_pokemon/ebay.json."
  echo "Import a listing CSV with: python3 -m holy_pokemon.automated_discovery --import-csv YOUR.csv --sync-app --once"
  echo "Or configure authorized production credentials, then restart this launcher."
  exit 2
fi