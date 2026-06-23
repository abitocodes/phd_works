# Dissertation results tables

LaTeX fragments consumed by `2-Dissertation-Draft/02-Content/Chapter-04.tex`.

## Regenerate (offline, synthetic)

```bash
cd A-Skill-Programs/margin_rank
source .venv/bin/activate
python scripts/run_dissertation_eval.py --fixtures --n-wallets 571 --export-latex
```

## Regenerate (real BigQuery)

After running the BigQuery extraction pipeline, use `--real` instead of `--fixtures`.

Each file begins with `% DUMMY DATA` comments until replaced by real pipeline output.
