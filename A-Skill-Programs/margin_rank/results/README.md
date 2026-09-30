# results/

Machine-readable summaries behind the tables in `2-Dissertation-Draft/overleaf-github/results/tables/`.

| File | Produced by | Read by |
|------|-------------|---------|
| `eval_summary.json` | `scripts/run_dissertation_eval.py --real --robustness --export-latex --benchmark-repeats 5`, then `scripts/refresh_alignment.py` (see `alignment_refresh` inside the file) | `scripts/export_latex_results.py` (alignment, contrast, benchmark, robustness tables) |
| `holdout/eval_summary_spenders.json` | `scripts/run_holdout_eval.py --cohort spenders` | `scripts/export_latex_results.py` (holdout tables) |
| `supplementary_checks.json` | `scripts/run_supplementary_checks.py` (post hoc: tie rule, edge weights, trader counts) | `scripts/export_latex_results.py` (tie-sensitivity and holdout-weighting tables) |
| `config/margin_config.yaml` | copy of the configuration in force at the run, including the pre-registered `reputation.hybrid` block | reader |
| `MANIFEST.json` | `scripts/publish_results.py` | `scripts/publish_results.py --check` |

`data/raw/` and `data/processed/` are tracked for collected/processed artifacts (see `../.gitignore` for exclusions: Tier-2 extracts, `_chunks/`, `active_wallet_cache/`, and blobs over GitHub’s 100 MiB limit). These `results/` copies remain the compact, published summaries for thesis tables. Refresh with `python scripts/publish_results.py` after each full run; verify with `--check`.

On 2026-09-30 two inverse-risk proxies (`loss_avoidance`, `worst_close_pnl_score`) were found to be negated, so they ranked the largest losses highest. `scripts/proxy_metrics.py` was fixed and `scripts/refresh_alignment.py` recomputed the alignment entries of `eval_summary.json` from the same parquet; runtimes were not measured again. The 29 August exploratory run in `data/processed/holdout/eval_summary.json` is kept as it was, so its inverse-risk labels still carry the old sign.
