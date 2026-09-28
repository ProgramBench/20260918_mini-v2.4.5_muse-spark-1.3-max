<p align="center">
  <a href="https://programbench.com"><img src="https://programbench.com/static/images/fox_hero_200.png" width="110" alt="ProgramBench"></a>
</p>

> A submission to the **[ProgramBench](https://programbench.com)** leaderboard — *can language models rebuild programs from scratch?* · [Leaderboard](https://programbench.com) · [How to submit](https://programbench.com/blog/submission-guide)

# Muse Spark 1.3 (max)

## System overview

This is a single-attempt run of Muse Spark 1.3 (`muse-spark-1.3-internal`) with
`reasoning.effort: max` and a maximum output budget of 65,536 tokens. The model ran
through the mini-SWE-agent scaffold in ProgramBench mini version 2.4.5, with a 1,000-step
limit and six-hour wall-clock limit per task.

Every task ran in a `task_cleanroom_v6` image as the unprivileged `agent` user, with
Docker networking disabled (`--network none`) and `SYS_PTRACE` dropped. The run attempted
and evaluated all 200 benchmark instances. Its packaged mean score is 70.76%.

## Reproducing this run

```bash
revenge mini-batch infer --split task \
  -c reveng/configs/mini/infer/infer_no_int_no_dep.yaml \
  -c <muse-spark-1.3-max-model-config.yaml> -w 8

revenge eval-cloud submit <run-dir> --split task --has-test-branch --force --no-tui
revenge eval-cloud collect <batch-id> --no-tui

python .claude/skills/pb-ship-results/stage_run.py stage \
  <run-dir> <submission-dir> -w 8
python .claude/skills/pb-ship-results/stage_run.py scan <submission-dir> -w 12
programbench submit package <submission-dir>
programbench submit verify <submission-dir>
```

## Extra stats

Cost, model-call, and output-token statistics are generated from the published trajectories
by the scripts under `_scripts/`. Cost uses these per-million-token rates: $0.10 uncached
input, $0.002 cached input, and $0.20 output.

## Links

- [ProgramBench](https://github.com/facebookresearch/ProgramBench)

## Submission checklist

- [x] Ran evaluation and `programbench submit package` to produce this submission
- [x] Filled in every `submission.yaml` field, including `is_os_model` / `is_os_scaffold`
- [x] Trajectories (`traj.json`) included for every task
- [ ] Solutions present — inline `submission.tar.gz`, or a hosted `submission.tar.gz.url` + `.sha256`
- [x] Extra stats were produced by trajectory-reading scripts shipped under `_scripts/`
- [x] Filled in the System overview and Reproducing sections above
- [x] `programbench submit verify .` passes Tier-0
- [ ] Made this fork public
- [ ] Opened a registration PR to the submissions repo

## Integrity attestations

- [x] Solutions were produced **only** from behavioral observation of the binary and its
      bundled docs — no source code, repositories, mirrors, or package registries were consulted
- [x] The model was not given internet access during evaluation
- [x] The model did not have access to any unit tests during evaluation
- [x] I consent to re-evaluation, and to flagging or removal if it contradicts the reported results

## Auditing

```bash
git clone <your-submission-repo>
cd 20260918_mini-v2.4.5_muse-spark-1.3-max
uvx programbench submit verify .
uvx programbench submit verify . --tier1
```

Tier-0 is self-contained. Tier-1 additionally fetches the hosted solutions and hidden tests
and re-runs them.
