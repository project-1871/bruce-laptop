#!/usr/bin/env bash
cd "$(dirname "$0")"
exec sudo python3 main.py "$@"
