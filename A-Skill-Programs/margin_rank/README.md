# Margin Rank — EndorseRank vs AWP evaluation pipeline

Arbitrum One ERC-20 allowance (EndorseRank) and transfer (AWP) reputation ranks, validated against transfer proxies (in-degree, in-value) and GMX V2 margin-trading success proxies.

BigQuery source (when online): `bigquery-public-data.goog_blockchain_arbitrum_one_us.logs`

## Prerequisites

- Python 3.10+
- For **real** extraction: Google Cloud ADC (`gcloud auth application-default login`) and `GOOGLE_CLOUD_PROJECT`

## Setup

```bash
cd A-Skill-Programs/margin_rank
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Offline dissertation evaluation (no GCP)

```bash
python scripts/run_dissertation_eval.py --fixtures --n-wallets 571
python scripts/export_latex_results.py
```

Outputs:

- `data/processed/eval_summary.json`
- `2-Dissertation-Draft/results/tables/*.tex` (LaTeX table fragments)

## Real BigQuery pipeline (3 phases)

See [docs/bigquery_data_plan.md](docs/bigquery_data_plan.md) for streams, tiers, and cost guardrails.

**Phase 1 — GMX validation labels (6-month observation window)**

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id

python scripts/extract_margin_week.py --dry-run
python scripts/extract_margin_week.py --extract --yes
python scripts/decode_gmx_events.py
python scripts/compute_rankings.py
```

**Phase 2 — Reputation subgraph (wallet-filtered, monthly batches)**

```bash
python scripts/extract_reputation_data.py --dry-run
python scripts/extract_reputation_data.py --extract --yes
python scripts/preprocess_arbitrum_allowances.py
python scripts/preprocess_arbitrum_transfers.py
python scripts/compute_reputation_ranks.py
```

**Phase 3 — Evaluation and benchmark (local; no extra BQ cost)**

```bash
python scripts/run_dissertation_eval.py --real
python scripts/export_latex_results.py
python scripts/benchmark_runtime.py  # 10k / 50k / 100k subgraph from parquet
```

Dry-run bytes and extraction metadata are written to `data/processed/extraction_manifest.json`. Per-query scan must stay under 150 GiB (`config/margin_config.yaml`).

## Scripts

| Script | Role |
|--------|------|
| `run_dissertation_eval.py` | Master offline/real eval → JSON |
| `benchmark_runtime.py` | EndorseRank vs AWP runtime/memory |
| `evaluate_alignment.py` | Spearman ρ / Kendall τ vs proxies |
| `export_latex_results.py` | JSON → dissertation LaTeX tables |
| `extract_margin_week.py` | GMX PositionDecrease BigQuery extraction |
| `extract_reputation_data.py` | Approval/Transfer BigQuery extraction |
| `generate_synthetic_*.py` | Offline fixture data |

See [docs/contract_wallet_exposure.md](docs/contract_wallet_exposure.md) for GMX wallet attribution rationale.
