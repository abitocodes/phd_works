# Dissertation results tables

LaTeX fragments consumed by `2-Dissertation-Draft/02-Content/Chapter-04.tex`.

## Proxy families (six)

| Family | File | Proxies |
|--------|------|---------|
| Transfer | `alignment-transfer.tex` | in-degree, in-value |
| Allowance | `alignment-allowance.tex` | in-approve degree, in-approve value |
| Default/Liquidation | `alignment-liquidation.tex` | liquidation-free rate, zero-liquidation flag, liquidation-free closes |
| Inverse risk | `alignment-inverse-risk.tex` | loss avoidance, non-loss close rate, worst-close PnL score |
| Sybil stability | `alignment-sybil-stability.tex` | inbound counterparty ratio, tenure, active months |
| GMX success | `alignment-gmx.tex` | close-success count, realized gain, success rate |
| Summary | `alignment-summary.tex` | mean τ per family, ER vs AWP |
| Benchmark | `benchmark-runtime.tex` | runtime, memory, iterations, edges |

## Regenerate (real BigQuery parquet)

```bash
cd A-Skill-Programs/margin_rank
# After Phase 1–2 extraction (see docs/bigquery_data_plan.md)
python scripts/run_dissertation_eval.py --real --export-latex
```

## Regenerate (offline synthetic)

```bash
python scripts/run_dissertation_eval.py --fixtures --n-wallets 571 --export-latex
```

Real-data tables include a header comment pointing to `--real --export-latex`.
