#!/usr/bin/env bash
echo "Bruce demo script"
echo "Date: $(date)"
echo "Hostname: $(hostname)"
echo "Interfaces: $(ip -br link show | awk '{print $1}' | tr '\n' ' ')"
echo "Done."
