# Muse Spark 1.3 (max) — ProgramBench submission

- **Model:** Muse Spark 1.3, reasoning effort **max**
- **Scaffold:** mini-SWE-agent v2.4.5 (single-agent), open source
- **Protocol:** `diff_lang` — no-internet + `task_cleanroom` images. The agent sees only the
  compiled binary (source removed, `.git` reset), reimplements from scratch by interacting with
  it, and never has network access (enforced at the container level).
- **Score:** ~0.708 (mean per-instance test pass-rate over the fixed 200, missing/errored = 0;
  the leaderboard recomputes authoritatively from `_stats/score.json`).
- **Inference date:** 20260918

## Reproduce

```bash
# inference (RevEngBench harness)
revenge mini-batch infer --split task \
  -c reveng/configs/mini/infer/infer_no_int_no_dep.yaml \
  -c reveng/configs/mini/models/muse_spark_1_3_pub_max.yaml -w 8
# evaluation
revenge eval-cloud submit output/<run> --split task --has-test-branch --force
```

Each test is run up to 3× (pytest-rerunfailures); only the final attempt is scored (flakiness defense).
