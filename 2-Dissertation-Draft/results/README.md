# Dissertation results tables

LaTeX fragments consumed by `2-Dissertation-Draft/02-Content/Chapter-04.tex`.

## Regenerate (offline, synthetic)

```bash
cd A-Skill-Programs/margin_rank
source .venv/bin/activate
python scripts/run_dissertation_eval.py --fixtures --n-wallets 571 --export-latex
```

## Regenerate (real BigQuery)

After Tier 1 extraction (GMX 6-month window + wallet-filtered Approval/Transfer), use `--real` instead of `--fixtures`:

```bash
# Phase 1–2: see docs/bigquery_data_plan.md and 03-End/appendix.tex
python scripts/run_dissertation_eval.py --real --export-latex
python scripts/benchmark_runtime.py  # 10k / 50k / 100k from cached parquet
```

Each file begins with `% DUMMY DATA` comments until replaced by real pipeline output.
