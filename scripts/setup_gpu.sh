#!/usr/bin/env bash
# Run this ON the 8x A100 instance (after: ssh ubuntu@<instance-ip>).
# Prereqs you must do FIRST (browser, one-time):
#   1. Accept the Gemma license at huggingface.co/google/diffusiongemma-26B-A4B-it
#   2. export HF_TOKEN=hf_xxx     (your Hugging Face token)
# Then:  bash setup_gpu.sh
set -euo pipefail

MODEL="${MODEL:-google/diffusiongemma-26B-A4B-it}"   # override: MODEL=inclusionAI/LLaDA2.1-mini bash setup_gpu.sh

echo ">> installing vllm…"
pip install -U vllm huggingface_hub

if [ -n "${HF_TOKEN:-}" ]; then
  echo ">> hugging face login…"
  huggingface-cli login --token "$HF_TOKEN"
fi

echo ">> serving $MODEL across all GPUs on :8000 …"
exec vllm serve "$MODEL" \
  --tensor-parallel-size 8 \
  --host 0.0.0.0 --port 8000 \
  --max-num-seqs 256 --max-model-len 4096

# If vllm errors "unknown architecture" (model is 10 days old), try the prebuilt image:
#   docker run --gpus all -p 8000:8000 vllm/vllm-openai:gemma --model "$MODEL" --tensor-parallel-size 8
# Or fall back to the proven diffusion LM:
#   MODEL=inclusionAI/LLaDA2.1-mini bash setup_gpu.sh
