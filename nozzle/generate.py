"""
Candidate generator (the firehose).

Backends:
  * vllm      -> OpenAI-compatible endpoint (your Lambda box running vLLM). THE real one.
  * anthropic -> Claude (premium; fine for low-volume, rate-limited).
  * smoke     -> OFFLINE plumbing only. Mutates gold to fake candidates so you can test the
                 pipeline with NO model. NEVER use smoke numbers in the demo — run.py stamps
                 every smoke artifact "SIMULATED" and refuses to call it a result.

Only stdlib (urllib) so there's nothing to install. Set the key/URL via env:
  VLLM_BASE_URL (default http://localhost:8000/v1), VLLM_MODEL, optional VLLM_API_KEY
  ANTHROPIC_API_KEY, ANTHROPIC_MODEL (default claude-opus-4-8)
"""
from __future__ import annotations
import json
import os
import re
import urllib.request

from nozzle.db import schema_text

PROMPT = """You are a senior data analyst. Write ONE SQLite query that answers the question.
Schema:
{schema}

Rules: SELECT-only. Return ONLY the SQL on a single line, no explanation, no markdown fences.

Question: {q}
SQL:"""


def _post(url: str, payload: dict, headers: dict, timeout: float = 60.0) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _clean_sql(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:sql)?|```$", "", text, flags=re.I | re.M).strip()
    # take first statement
    text = text.split(";")[0].strip()
    return text


def _gen_vllm(prompt: str, n: int, temperature: float) -> list[str]:
    base = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1").rstrip("/")
    model = os.environ.get("VLLM_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct")
    key = os.environ.get("VLLM_API_KEY", "EMPTY")
    out = _post(f"{base}/chat/completions", {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "n": n, "temperature": temperature, "max_tokens": 256,
    }, {"Authorization": f"Bearer {key}"})
    return [_clean_sql(c["message"]["content"]) for c in out["choices"]]


def _gen_anthropic(prompt: str, n: int, temperature: float) -> list[str]:
    key = os.environ["ANTHROPIC_API_KEY"]
    model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")
    sqls = []
    for _ in range(n):  # Messages API has no n; loop (low-volume premium path)
        out = _post("https://api.anthropic.com/v1/messages", {
            "model": model, "max_tokens": 256, "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }, {"x-api-key": key, "anthropic-version": "2023-06-01"})
        sqls.append(_clean_sql(out["content"][0]["text"]))
    return sqls


def _gen_smoke(question: dict, n: int, temperature: float) -> list[str]:
    """OFFLINE fake candidates derived from gold + plausible mistakes. PLUMBING ONLY."""
    import random
    rng = random.Random(hash(question["id"]) & 0xFFFF)
    gold = question["gold"]
    variants = [gold, gold]  # correct shows up sometimes
    # plausible-but-wrong mutations
    variants.append(gold.replace("status='completed'", "1=1"))        # forgets filter
    variants.append(gold.replace("SUM(", "AVG(") if "SUM(" in gold else gold + " LIMIT 1")
    variants.append("SELECT * FROM customers")                          # nonsense
    variants.append(gold.replace("2025", "2024") if "2025" in gold else gold)
    return [rng.choice(variants) for _ in range(n)]


def generate(question: dict, n: int, backend: str = "vllm", temperature: float = 0.7) -> list[str]:
    prompt = PROMPT.format(schema=schema_text(), q=question["q"])
    if backend == "vllm":
        return _gen_vllm(prompt, n, temperature)
    if backend == "anthropic":
        return _gen_anthropic(prompt, n, temperature)
    if backend == "smoke":
        return _gen_smoke(question, n, temperature)
    raise ValueError(f"unknown backend: {backend}")
