#!/usr/bin/env bash
# Lifeline pre-flight: syntax + the full GPU-free test suite. Run before every commit / demo.
set -euo pipefail
cd "$(dirname "$0")"
echo "== syntax check =="
python3 -m py_compile lifeline/*.py tests/*.py
echo "ok"
echo "== test suite =="
python3 tests/test_lifeline.py
