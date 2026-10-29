#!/usr/bin/env bash
set -e
echo "======================================================================"
echo "Launching Multimodal Classroom Intelligence Agent in Production"
echo "======================================================================"
python3 -m pip install -r requirements.txt
python3 -m unittest tests/test_system.py
echo "Starting Production Server (Waitress)..."
python3 wsgi.py

