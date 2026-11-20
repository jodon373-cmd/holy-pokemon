#!/bin/zsh
cd "${0:A:h}/.." || exit 1
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv || exit 1
fi
.venv/bin/python -c 'import cv2,numpy' 2>/dev/null || .venv/bin/python -m pip install 'numpy>=1.26,<3' 'opencv-python-headless>=4.8,<5' || exit 1
.venv/bin/python -m holy_pokemon.centering_tool
