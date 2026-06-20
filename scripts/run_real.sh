#!/usr/bin/env bash
# Run this ON YOUR MAC, in the repo, AFTER the model is serving and the tunnel is open:
#   ssh -L 8000:localhost:8000 ubuntu@<instance-ip>      # leave running in another terminal
# Then:  bash scripts/run_real.sh
# (Claude can run this for you once the tunnel is up — the harness talks to the GPU through it.)
set -euo pipefail
cd "$(dirname "$0")/.."

export LIFELINE_BASE_URL="${LIFELINE_BASE_URL:-http://localhost:8000/v1}"
export LIFELINE_MODEL="${LIFELINE_MODEL:-google/diffusiongemma-26B-A4B-it}"

echo ">> health check:"
curl -s "$LIFELINE_BASE_URL/models" | head -c 400; echo

echo ">> smoke test (cheap, confirms the pipeline talks to the real model):"
python3 -m lifeline.run --backend diffusion --resamples 3

echo ">> FULL run (the real number: wide sweep + tight stats, saturates all 8 GPUs):"
python3 -m lifeline.run --backend diffusion --resamples 8 --big

echo ">> done -> dashboard_lifeline/index.html  (banner should read REAL)"
