"""
The "mayor": a Gastown-style orchestrator that fans work out to N agents and
collects their migration candidates ("trajectories").

Three modes:
  * synthetic  -> generate a candidate bank locally (zero dependency; for building/rehearsing)
  * replay     -> load real Devin trajectories captured earlier to JSON (for the live demo)
  * live       -> call Devin Teams to spawn N agents in parallel (skeleton; plug in your key)

The Agents track requires Devin Teams. The recommended flow:
  1. EARLY in the hackathon, run `live` on a handful of real tasks to bank trajectories
     (Devin is slow + costs credits -> do this offline, save to data/devin_runs/*.json).
  2. Build + rehearse the dashboard against `replay` (and `synthetic` before any Devin data).
  3. In the demo, drive the curve from the banked trajectories and do ONE live held-out run.
"""
from __future__ import annotations
import json
import os
import random

from agents.synthetic import generate_pool

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DevinOrchestrator:
    def __init__(self, mode: str = "synthetic", replay_path: str | None = None,
                 api_key: str | None = None, pool_size: int = 240, seed: int = 7):
        self.mode = mode
        self.replay_path = replay_path
        self.api_key = api_key or os.environ.get("DEVIN_API_KEY")
        self.pool_size = pool_size
        self.seed = seed
        self._bank: list[dict] | None = None

    # ---- public API used by the pipeline ----
    def bank(self, task: dict) -> list[dict]:
        """Return the full candidate bank (bootstrapped from in the curve)."""
        if self._bank is not None:
            return self._bank
        if self.mode == "synthetic":
            self._bank = generate_pool(task, size=self.pool_size, seed=self.seed)
        elif self.mode == "replay":
            self._bank = self._load_replay()
        elif self.mode == "live":
            self._bank = self._run_live(task, n=self.pool_size)
        else:
            raise ValueError(f"unknown mode: {self.mode}")
        return self._bank

    def fan_out(self, task: dict, n: int) -> list[dict]:
        """One demo round: take n trajectories from the bank (the 'swarm')."""
        bank = self.bank(task)
        rng = random.Random(self.seed)
        return rng.sample(bank, min(n, len(bank)))

    # ---- replay ----
    def _load_replay(self) -> list[dict]:
        path = self.replay_path or os.path.join(BASE, "data", "devin_runs", "bank.json")
        with open(path) as f:
            return json.load(f)

    # ---- live Devin Teams (skeleton) ----
    def _run_live(self, task: dict, n: int) -> list[dict]:
        """
        Spawn N Devin sessions on the same spec, each running a Ralph loop, and
        collect their migration outputs as candidates.

        Wire this up against the Devin API (app.devin.ai -> Settings -> API keys).
        Apply the hackathon coupon `inf3r3nc3` on the Team plan first.

        Pseudocode:
            import requests
            spec = build_spec(task)            # the migration prompt + RALPH.md loop file
            sessions = [create_session(spec) for _ in range(n)]   # POST /v1/sessions
            outputs  = [poll_until_done(s)  for s in sessions]    # GET  /v1/sessions/{id}
            return [parse_migration(o) for o in outputs]          # -> {customers, orders}

        Each session's RALPH.md should instruct: read the spec, make ONE improvement,
        run the local Diff Oracle (oracle/diff_oracle.py) as a self-check, commit, repeat
        until all hard invariants pass or the step budget is hit.
        """
        raise NotImplementedError(
            "Live Devin mode not wired yet. Bank trajectories with the Devin API, save to "
            "data/devin_runs/bank.json, then use mode='replay'. See the docstring + BUILD_PLAN.md."
        )


# Spec + Ralph-loop file generation (used by live mode; handy to scaffity early).
RALPH_LOOP_TEMPLATE = """\
# RALPH.md  -- the loop each Devin runs (fresh context every iteration)

GOAL: migrate data/orders_raw.csv into normalized tables {customers, orders}.

Each iteration:
1. Read this file and the current state of /out (customers.json, orders.json).
2. Make exactly ONE improvement toward a correct migration.
3. Self-check by running:  python -m oracle.diff_oracle_cli /out
   (all HARD invariants must pass: order_count, revenue, fk_integrity, pk_unique,
    customer_count, no_null)
4. Commit with a one-line message describing the improvement.
5. If every hard invariant passes, write DONE to /out/STATUS and stop. Else repeat.

Memory lives in git history + /out, NOT in your context window.
"""


def build_spec(task: dict) -> str:
    return (
        f"Task: {task['description']}\n"
        f"Source: data/orders_raw.csv ({task['n_source_rows']} messy rows).\n"
        f"Target: customers(customer_id,name,email) and "
        f"orders(order_id,customer_id,product,qty,unit_price,order_date).\n"
        f"Hard requirements (self-check with the Diff Oracle): exactly "
        f"{task['n_source_orders']} orders, {task['n_distinct_customers']} de-duplicated "
        f"customers, total revenue ${task['source_revenue']:.2f}, valid FKs, unique PKs, no nulls.\n"
        + RALPH_LOOP_TEMPLATE
    )
