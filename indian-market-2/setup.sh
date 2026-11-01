#!/usr/bin/env bash
echo "======================================================="
echo "  BREAKING MONEY / THE AI TRADING ARENA - Setup (macOS/Linux)"
echo "======================================================="
python3 -m pip install -r requirements.txt
if [ ! -f .env ]; then
    cp .env.example .env
fi
echo "Setup done."
