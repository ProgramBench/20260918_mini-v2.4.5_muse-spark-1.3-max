#!/usr/bin/env python3
"""Write `_stats/tokens.json` mapping each instance to its output-token count.

Copy into a submission's `_scripts/` and run from there. Output tokens are the
generated tokens the model produced, summed over every model response in the
trajectory — a price-independent, cache-invariant measure of generative effort
(input/prompt tokens excluded, so caching can't influence it; reasoning/thinking
tokens are already included in the output count).

Reads every task's `<iid>/<iid>.traj.json`. Only `output_tokens_from_traj` is
trajectory-format-specific; adapt it for other agents and the shape stays the same.
"""

import json
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent.parent


def _usage_of(msg: dict) -> dict | None:
    """Locate the per-call usage block on a message, across mini-swe-agent formats.

    Chat-Completions / litellm responses store it at `extra.response.usage`; the OpenAI
    Responses API stores it directly at `msg.usage` (on a message with `role: None`).
    """
    resp = (msg.get("extra") or {}).get("response")
    if isinstance(resp, dict) and isinstance(resp.get("usage"), dict):
        return resp["usage"]
    if isinstance(msg.get("usage"), dict):
        return msg["usage"]
    return None


def output_tokens_from_traj(traj: dict) -> int | None:
    """Sum output tokens over every model response in the trajectory.

    `completion_tokens` (Chat Completions) and `output_tokens` (Responses API / Anthropic)
    both count generated tokens including reasoning. Adapt for other agents.
    """
    total = 0
    found = False
    for msg in traj.get("messages", []):
        usage = _usage_of(msg)
        if not usage:
            continue
        out = usage.get("completion_tokens")
        if out is None:
            out = usage.get("output_tokens")
        if out is not None:
            total += out
            found = True
    return total if found else None


tokens = {}
for traj in sorted(RUN_DIR.glob("[!_]*/*.traj.json")):
    value = output_tokens_from_traj(json.loads(traj.read_text()))
    if value is not None:
        tokens[traj.parent.name] = value

(RUN_DIR / "_stats").mkdir(exist_ok=True)
(RUN_DIR / "_stats" / "tokens.json").write_text(json.dumps(tokens, indent=2, sort_keys=True))
print(f"Wrote _stats/tokens.json for {len(tokens)} instance(s)")

