# BigQuery Proposal Data Extraction

EndorseRank dissertation proposal — on-chain data pipeline using **Google BigQuery Sandbox** (free 1 TiB/month query processing, no billing required).

## Proposal vs actual window

[Chapter-05](../proposal/02-Content/Chapter-05.tex) mentions a six-month observation window. This pipeline uses a **budget-driven window**:

- **End (fixed):** 2026-05-31
- **Start (dynamic):** determined by backward monthly dry-runs within **900 GiB** of the 1 TiB free tier
- Actual dates are stored in `processed/extraction_manifest.json`

## Prerequisites

1. Google account with a GCP project (**do not enable billing** for Sandbox)
2. [BigQuery Sandbox](https://cloud.google.com/bigquery/docs/sandbox) or free tier only
3. Python 3.10+

## Setup

```bash
cd data_works
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Authenticate (pick one)
gcloud auth application-default login
# or set GOOGLE_APPLICATION_CREDENTIALS to a service account key

export GOOGLE_CLOUD_PROJECT=your-project-id
```

## Usage

```bash
# 1) Plan budget (dry-run only, writes processed/budget_plan.json)
python scripts/extract_all.py --budget-plan

# 2) Extract included months + liquidations
python scripts/extract_all.py --extract --yes

# 3) Preprocess
python scripts/preprocess_latest_allowances.py
python scripts/preprocess_transfer_graph.py
python scripts/preprocess_default_labels.py
python scripts/create_samples.py
```

### Offline / no GCP credentials

If Application Default Credentials are not configured, use `--synthetic` to validate the pipeline locally (small fake data; manifest marks `"synthetic": true`):

```bash
python scripts/extract_all.py --synthetic --budget-plan
python scripts/extract_all.py --synthetic --extract
# then preprocess + create_samples as above
```

Replace with real BigQuery runs after `gcloud auth application-default login`.

Options:

- `--skip-existing` — skip parquet files that already exist
- `--yes` — skip confirmation prompt before extract
- `--dry-run-only` — alias for `--budget-plan`

## Cost safeguards

1. **No billing** — Sandbox only
2. Every query is **dry-run** during `--budget-plan`
3. **900 GiB** total budget cap (10% headroom under 1 TiB)
4. **150 GiB** max per single query (month skipped if exceeded)
5. Transfers always use **wallet filter** (`aave_wallets_only`)
6. `extraction_manifest.json` logs planned vs actual bytes scanned

## Data products

| Output | Description |
|--------|-------------|
| `raw/approvals/approvals_YYYY-MM.parquet` | ERC-20 Approval events |
| `raw/token_transfers/transfers_YYYY-MM.parquet` | ERC-20 transfers (filtered wallets) |
| `raw/aave_liquidations/` | Feature + outcome liquidation events |
| `processed/latest_allowances.parquet` | Latest allowance per (token, owner, spender) |
| `processed/transfer_edges.parquet` | Aggregated transfer graph edges |
| `processed/default_labels.parquet` | Binary default labels from post-cutoff liquidations |

## Event signatures

- **Approval:** `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925`
- **LiquidationCall:** `0xe413a321e86847086171d8f3574d34f9b1b5e4a3a5d0c3e6600679c56`

## License

Research use — public BigQuery datasets only.
