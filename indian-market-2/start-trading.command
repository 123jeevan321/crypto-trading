#!/usr/bin/env bash
cd "$(dirname "$0")"
open "http://127.0.0.1:5003"
python3 -m arena run
