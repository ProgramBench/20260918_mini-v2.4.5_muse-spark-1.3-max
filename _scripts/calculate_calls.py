#!/usr/bin/env python3
"""Write `_stats/calls.json` mapping each instance to its model/API call count.

Copy into a submission's `_scripts/` and run from there. Reads every task's
`<iid>/<iid>.traj.json`. Only `calls_from_traj` is trajectory-format-specific;
adapt it for other agents and the output shape stays the same.
"""

import json
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent.parent


def calls_from_traj(traj: dict) -> int | None:
    """mini-swe-agent format: info.model_stats.api_calls. Adapt for other agents."""
    return traj.get("info", {}).get("model_stats", {}).get("api_calls")


calls = {}
for traj in sorted(RUN_DIR.glob("[!_]*/*.traj.json")):
    value = calls_from_traj(json.loads(traj.read_text()))
    if value is not None:
        calls[traj.parent.name] = value

(RUN_DIR / "_stats").mkdir(exist_ok=True)
(RUN_DIR / "_stats" / "calls.json").write_text(json.dumps(calls, indent=2, sort_keys=True))
print(f"Wrote _stats/calls.json for {len(calls)} instance(s)")

