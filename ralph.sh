#!/usr/bin/env bash
# Ralph — autonomous loop for Lifeline. Feeds prompt.md to the coding agent until every story in
# prd.json passes, detected via the <promise>complete</promise> sentinel. (Jeffrey Huntley's technique.)
#
#   bash ralph.sh            # loops until done
#
# Each iteration: the agent reads prompt.md -> AGENT.md + prd.json, implements ONE story, validates
# with ./check.sh, marks passes:true, commits. Stops when all stories pass.
set -uo pipefail
cd "$(dirname "$0")"
MAX="${MAX_LOOPS:-12}"
i=0
while (( i < MAX )); do
  i=$((i+1))
  echo "──────── Ralph loop $i ────────"
  out="$(cat prompt.md | claude -p --dangerously-skip-permissions 2>&1)"
  echo "$out"
  if grep -q "<promise>complete</promise>" <<<"$out"; then
    echo "✅ All stories pass — Ralph done after $i loop(s)."
    exit 0
  fi
done
echo "⏹ Stopped after $MAX loops (raise MAX_LOOPS to continue)."
