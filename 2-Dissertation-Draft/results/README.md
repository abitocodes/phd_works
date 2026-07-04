# Dissertation results tables

LaTeX fragments consumed by `2-Dissertation-Draft/02-Content/Chapter-04.tex` and Appendix.

## Main dissertation tables (Chapter 4)

| File | Description |
|------|-------------|
| `alignment-three-methods.tex` | Mean τ matrix (five proxy families): EndorseRank, AWP, GF-PR |
| `alignment-transfer.tex`, `alignment-allowance.tex`, `alignment-inverse-risk.tex`, `alignment-sybil-stability.tex`, `alignment-gmx.tex` | Per-family proxy detail (3 methods each) |
| `benchmark-runtime.tex` | Runtime, memory, edges (ER, AWP, GF-PR) on matched cohort |
| `benchmark-scaling.tex` | Expanded wallet-pool runtime scaling (10k, full pool) |
| `robustness-damping.tex`, `robustness-tokens.tex`, `robustness-sample-size.tex` | Robustness checks (Chapter 4) |

## Appendix-only

| File | Description |
|------|-------------|
| `benchmark-scaling-incohort.tex` | Matched-cohort subsample scaling ($n \leq 5{,}521$) |
| `alignment-summary.tex` | Columnar family summary (duplicate of three-method matrix) |

## Archived extended baselines

Seven-method and six-Aave tables: [`../archive/extended-baselines/`](../archive/extended-baselines/README.md).

## Regenerate (real BigQuery parquet + robustness)

```bash
cd A-Skill-Programs/margin_rank
python scripts/sample_active_wallets.py --from-parquet --extract
python scripts/run_dissertation_eval.py --real --robustness --export-latex
```

Exports dissertation tables plus archive presets when `--export-latex` is set.

## Regenerate (offline synthetic)

```bash
python scripts/run_dissertation_eval.py --fixtures --n-wallets 571 --export-latex
```

## Figures

Generated PDFs live in `../Figures/generated/`. Regenerate with:

```bash
python scripts/generate_dissertation_figures.py
```
