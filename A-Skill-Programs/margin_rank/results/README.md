# results/

Machine-readable summaries behind the tables in `2-Dissertation-Draft/overleaf-github/results/tables/`.

| File | Produced by | Read by |
|------|-------------|---------|
| `eval_summary.json` | `scripts/run_dissertation_eval.py --real --robustness --export-latex --benchmark-repeats 5` | `scripts/export_latex_results.py` (alignment, contrast, benchmark, robustness tables) |
| `holdout/eval_summary_spenders.json` | `scripts/run_holdout_eval.py --cohort spenders` | `scripts/export_latex_results.py` (holdout tables) |
| `config/margin_config.yaml` | copy of the configuration in force at the run, including the pre-registered `reputation.hybrid` block | reader |
| `MANIFEST.json` | `scripts/publish_results.py` | `scripts/publish_results.py --check` |

`data/processed/` is not tracked (raw extracts, parquet). These copies are, so the numbers in the thesis can be checked against a committed summary without re-running the pipeline. Refresh with `python scripts/publish_results.py` after each full run; verify with `--check`.
