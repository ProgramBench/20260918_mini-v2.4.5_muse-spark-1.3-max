#!/usr/bin/env python3
"""Write `_stats/cost.json` using the published Muse Spark 1.3 token rates.

Only provider-reported cache hits are charged at the cached-input rate. When a response
does not report cache-hit tokens, all of its prompt tokens are conservatively charged at
the uncached-input rate; no cache behavior is inferred from prompt growth.
"""

import json
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent.parent
TOKENS_PER_MILLION = 1_000_000
INPUT_USD_PER_MILLION = 0.10
CACHED_INPUT_USD_PER_MILLION = 0.002
OUTPUT_USD_PER_MILLION = 0.20


def _usage_of(msg: dict) -> dict | None:
    response = (msg.get("extra") or {}).get("response")
    if isinstance(response, dict) and isinstance(response.get("usage"), dict):
        return response["usage"]
    if isinstance(msg.get("usage"), dict):
        return msg["usage"]
    return None


def cost_from_traj(traj: dict) -> tuple[float, int, int, int] | None:
    uncached_input = 0
    cached_input = 0
    output = 0
    found = False

    for msg in traj.get("messages", []):
        usage = _usage_of(msg)
        if not usage:
            continue
        prompt = usage.get("prompt_tokens", usage.get("input_tokens"))
        completion = usage.get("completion_tokens", usage.get("output_tokens"))
        if prompt is None or completion is None:
            continue

        details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details") or {}
        recorded_cached = details.get("cached_tokens")
        if isinstance(recorded_cached, int):
            cached = min(prompt, recorded_cached)
        else:
            cached = 0

        uncached_input += prompt - cached
        cached_input += cached
        output += completion
        found = True

    if not found:
        return None
    cost = (
        uncached_input * INPUT_USD_PER_MILLION
        + cached_input * CACHED_INPUT_USD_PER_MILLION
        + output * OUTPUT_USD_PER_MILLION
    ) / TOKENS_PER_MILLION
    return cost, uncached_input, cached_input, output


cost = {}
totals = {"uncached_input": 0, "cached_input": 0, "output": 0}
for traj in sorted(RUN_DIR.glob("[!_]*/*.traj.json")):
    value = cost_from_traj(json.loads(traj.read_text()))
    if value is not None:
        amount, uncached_input, cached_input, output = value
        cost[traj.parent.name] = amount
        totals["uncached_input"] += uncached_input
        totals["cached_input"] += cached_input
        totals["output"] += output

(RUN_DIR / "_stats").mkdir(exist_ok=True)
(RUN_DIR / "_stats" / "cost.json").write_text(json.dumps(cost, indent=2, sort_keys=True))
print(f"Wrote _stats/cost.json for {len(cost)} instance(s)")
print(
    f"Estimated usage: uncached_input={totals['uncached_input']:,}, "
    f"cached_input={totals['cached_input']:,}, output={totals['output']:,}; "
    f"total_cost=${sum(cost.values()):,.6f}"
)
