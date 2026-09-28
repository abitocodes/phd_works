# results/

Machine-readable summaries behind the tables in `2-Dissertation-Draft/overleaf-github/results/tables/`.

| File | Produced by | Read by |
|------|-------------|---------|
| `eval_summary.json` | `scripts/run_dissertation_eval.py --real --robustness --export-latex --benchmark-repeats 5` | `scripts/export_latex_results.py` (alignment, contrast, benchmark, robustness tables) |
| `holdout/eval_summary_spenders.json` | `scripts/run_holdout_eval.py --cohort spenders` | `scripts/export_latex_results.py` (holdout tables) |
| `config/margin_config.yaml` | copy of the configuration in force at the run, including the pre-registered `reputation.hybrid` block | reader |
| `MANIFEST.json` | `scripts/publish_results.py` | `scripts/publish_results.py --check` |

`data/raw/` and `data/processed/` are tracked for collected/processed artifacts (see `../.gitignore` for exclusions: Tier-2 extracts, `_chunks/`, `active_wallet_cache/`, and blobs over GitHub’s 100 MiB limit). These `results/` copies remain the compact, published summaries for thesis tables. Refresh with `python scripts/publish_results.py` after each full run; verify with `--check`.
