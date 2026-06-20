#!/usr/bin/env bash
# Turnkey re-setup for DiffusionGemma on a FRESH Lambda instance (1x or 8x A100-80GB).
# Reproduces the exact working environment we fought to find. Re-spin = run this, then
# scp the lifeline/ folder over and launch.
#
#   export HF_TOKEN=hf_xxxx        # your (rotated) Hugging Face token
#   bash setup_diffusion_gpu.sh
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"

echo ">> installing transformers stack (vllm pulls the exact transformers 5.12 + torch that work)…"
pip install -U vllm accelerate huggingface_hub

echo ">> fixing the numpy-2 vs old-system-package binary conflicts (scipy/sklearn/pandas/ml_dtypes)…"
pip install -U scipy scikit-learn pandas ml_dtypes

echo ">> downloading DiffusionGemma weights (~48GB; token speeds this up)…"
python3 -c "from huggingface_hub import snapshot_download; snapshot_download('unsloth/diffusiongemma-26B-A4B-it')"

echo ""
echo ">> ENV READY. Now from your Mac:  scp -r lifeline ubuntu@<ip>:~/"
echo ">> Then on the box:"
echo "     export PATH=\$HOME/.local/bin:\$PATH"
echo "     python3 -m lifeline.diffusion_server          # the product (port 8080)"
echo "     python3 -m lifeline.diffusion_run --bestofn   # the accuracy experiment"
echo ">> Tunnel from your Mac:  ssh -L 8080:localhost:8080 ubuntu@<ip>   then open http://localhost:8080"
echo ">> Loads in ~17s on one A100-80GB. device_map={'':0} (single GPU) — do NOT use device_map=auto (it CPU-offloads and hangs)."
