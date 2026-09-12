# Dissertation results tables

LaTeX fragments consumed by `Chapter-04-Implementation-and-Empirical-Results/index.tex` and Appendix.
All numbers come from `A-Skill-Programs/margin_rank/data/processed/eval_summary.json`
(pipeline run of 2026-09-12: 5 timed PageRank solves after one warm-up, 400 paired
wallet-bootstrap resamples with seed 42).

## Main dissertation tables (Chapter 4)

| File | Description |
|------|-------------|
| `benchmark-runtime.tex` | Runtime (mean, SD), peak memory, iterations, \|V\|, \|E\| for EndorseRank and AWP on the matched cohort |
| `benchmark-scaling.tex` | Expanded wallet-pool node-count sensitivity (10,000 / 50,000 / 99,080) with per-stage \|V\|, \|E\| |
| `alignment-family-ci.tex` | Family-mean τ with 95% bootstrap CI for EndorseRank and AWP, plus inter-method τ |
| `tau-diff.tex` | Six pre-specified paired-bootstrap Δτ contrasts |
| `alignment-transfer.tex`, `alignment-allowance.tex`, `alignment-sybil-stability.tex` | Per-proxy detail with 95% CI (EndorseRank, AWP) |
| `robustness-damping.tex`, `robustness-tokens.tex`, `robustness-sample-size.tex` | Robustness / sensitivity checks |

## Appendix-only

| File | Description |
|------|-------------|
| `benchmark-scaling-incohort.tex` | Matched-cohort subsample scaling ($n \leq 5{,}521$) with \|V\|, \|E\| |
| `alignment-summary.tex` | Columnar family summary including the archived liquidation / inverse-risk / GMX families |
| `alignment-gmx.tex`, `alignment-inverse-risk.tex`, `alignment-liquidation.tex` | Outcome-family detail (not used as validation evidence in the main text) |

## Archived extended baselines

Three-method (with GF-PR), seven-method and six-Aave matrices:
[`../archive/extended-baselines/`](../archive/extended-baselines/README.md).
GF-PR was withdrawn from the main narrative because it is built from the same GMX
outcome data it would be validated against.

## Regenerate (real BigQuery parquet + robustness)

```bash
cd A-Skill-Programs/margin_rank
python scripts/run_dissertation_eval.py --real --robustness --benchmark-repeats 5
python scripts/export_latex_results.py
python scripts/export_method_matrix.py --preset three   # archive only
python scripts/generate_dissertation_figures.py
```

## Regenerate (offline synthetic)

```bash
python scripts/run_dissertation_eval.py --fixtures --n-wallets 571 --export-latex
```

## Figures

Generated PDFs live in `../Figures/generated/`. Regenerate with:

```bash
python scripts/generate_dissertation_figures.py
```
