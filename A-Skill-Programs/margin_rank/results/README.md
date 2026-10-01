# results/

Machine-readable summaries behind the tables in `2-Dissertation-Draft/overleaf-github/results/tables/`.

| File | Produced by | Read by |
|------|-------------|---------|
| `eval_summary.json` | `scripts/run_dissertation_eval.py --real --robustness --export-latex --benchmark-repeats 5`, then `scripts/refresh_alignment.py` (see `alignment_refresh` inside the file) | `scripts/export_latex_results.py` (alignment, contrast, benchmark, robustness tables) |
| `holdout/eval_summary_spenders.json` | `scripts/run_holdout_eval.py --cohort spenders` | `scripts/export_latex_results.py` (holdout tables) |
| `supplementary_checks.json` | `scripts/run_supplementary_checks.py` (post hoc: tie rule, edge weights, trader counts, AWP in its published form) | `scripts/export_latex_results.py` (tie-sensitivity, holdout-weighting and awp-paper-form tables) |
| `config/margin_config.yaml` | copy of the configuration in force at the run, including the pre-registered `reputation.hybrid` block | reader |
| `config/fresh_holdout_2026q3.yaml` | copy of the registration of the June–August replication (`status: registered`, commit 4085ab9, merged into master on 2026-10-01) | reader |
| `fresh_2026q3/extraction_manifest.json` | `scripts/extract_fresh_window.py --extract --yes` (rows, bytes billed and the registration hashes, taken on a Windows checkout, so the hashes are of the CRLF files) | reader |
| `fresh_2026q3/fresh_holdout_summary.json` | `scripts/run_fresh_holdout.py` (mode `registered`) | `scripts/export_latex_results.py` (fresh-holdout, fresh-traders and fresh-contrasts tables) |
| `MANIFEST.json` | `scripts/publish_results.py` | `scripts/publish_results.py --check` |

`data/raw/` and `data/processed/` are tracked for collected/processed artifacts (see `../.gitignore` for exclusions: Tier-2 extracts, `_chunks/`, `active_wallet_cache/`, and blobs over GitHub’s 100 MiB limit). These `results/` copies remain the compact, published summaries for thesis tables. Refresh with `python scripts/publish_results.py` after each full run; verify with `--check`.

On 2026-09-30 two inverse-risk proxies (`loss_avoidance`, `worst_close_pnl_score`) were found to be negated, so they ranked the largest losses highest. `scripts/proxy_metrics.py` was fixed and `scripts/refresh_alignment.py` recomputed the alignment entries of `eval_summary.json` from the same parquet; runtimes were not measured again. The 29 August exploratory run in `data/processed/holdout/eval_summary.json` is kept as it was, so its inverse-risk labels still carry the old sign.

The June–August replication was registered on 2026-10-01 (commit 4085ab9), its logs were extracted the same day after the registration, and `run_fresh_holdout.py` evaluated it in `registered` mode. By the rule fixed in advance the decision is not met: F1 and F3 hold, F2 does not.
