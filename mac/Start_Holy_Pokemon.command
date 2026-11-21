#!/bin/zsh
# Private Mac-local app. No credentials, trades or paid network calls at startup.
set -eu
cd "$(dirname "$0")/.."
if ! command -v python3 >/dev/null; then
  echo "Python 3.12+ is required. Install Python from python.org, then launch again."
  exit 1
fi
python3 -c 'import sys; assert sys.version_info >= (3,12), "Python 3.12+ required"'
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import PIL' 2>/dev/null; then
  .venv/bin/python -m pip install -e .
fi
PORT="${HOLY_PORT:-8876}"
if /usr/bin/curl --silent --fail "http://127.0.0.1:$PORT/api/status" | .venv/bin/python -c 'import sys,json; assert json.load(sys.stdin).get("application")=="holy-pokemon"' 2>/dev/null; then
  [[ "${HOLY_NO_OPEN:-0}" == 1 ]] || open "http://127.0.0.1:$PORT"
  echo "Holy Pokémon is already available on port $PORT."
  exit 0
fi
[[ "${HOLY_NO_OPEN:-0}" == 1 ]] || (sleep 1; open "http://127.0.0.1:$PORT") &
echo "Holy Pokémon → http://127.0.0.1:$PORT"
exec .venv/bin/python -m holy_pokemon.dashboard --port "$PORT"
