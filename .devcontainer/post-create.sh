#!/usr/bin/env bash
python3 -m venv .venv
source .venv/bin/activate

python3 ./setup.py develop --user
pip install -r requirements.txt
