# Ralph prompt — Lifeline

You are an autonomous coding agent improving Lifeline. Do exactly one story per loop.

1. Study `AGENT.md` to understand the project, the guardrails, and the invariants.
2. Read `prd.json`. Pick the single highest-priority story (lowest `priority` number) whose
   `"passes": false`. Work on that ONE story only — do not start others.
3. Before implementing: use sub-agents to search the codebase so you don't fill your own context
   ("don't assume; verify by searching"). Confirm the story isn't already done.
4. Implement the story. Keep the diff additive and localized. Obey every guardrail in `AGENT.md`:
   preserve all UI element ids and the `/ask` contract, keep accessibility + reduced-motion, do not
   edit the hardened core (`triage.py` / `real_run.py` verify/PROTO) unless the story says so.
5. Validate:
   - `./check.sh` must pass (never weaken existing tests).
   - `python3 -m py_compile lifeline/*.py`.
   - For UI stories, confirm the rendered result in the preview.
6. Set this story's `"passes": true` in `prd.json` and commit with a clear message.
7. If, after this, EVERY story in `prd.json` has `"passes": true`, reply with the exact sentinel:
   `<promise>complete</promise>`
   Otherwise, end so the loop runs the next iteration.
