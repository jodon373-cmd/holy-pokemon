#!/bin/zsh
# Run from a cloned Holy Pokémon repository. Read-only; binds localhost.
set -e
cd "$(dirname "$0")/.."
echo "Starting Holy Pokémon research console..."
echo "Open http://127.0.0.1:8765 in your browser"
python3 -m holy_pokemon.dashboard --port 8765
