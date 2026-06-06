# Margin Rank — 온체인 마진거래 지갑 성공률 순위

GMX V2 (Arbitrum) perpetual margin trading positions for **2026-05-25 ~ 2026-05-31**, ranked by close success rate. Static Django dashboard (no live refresh).

BigQuery source: `bigquery-public-data.goog_blockchain_arbitrum_one_us.logs` (legacy `crypto_arbitrum` is not accessible).

## Prerequisites

- Python 3.10+
- Google Cloud ADC (`gcloud auth application-default login`) for real BigQuery extraction
- See [docs/contract_wallet_exposure.md](docs/contract_wallet_exposure.md) for protocol rationale

## Setup

```bash
cd margin_rank
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GOOGLE_CLOUD_PROJECT=your-project-id
```

## Pipeline

```bash
# 1) Extract raw EventEmitter logs (dry-run first)
python scripts/extract_margin_week.py --dry-run
python scripts/extract_margin_week.py --extract --yes

# 2) Decode PositionDecrease events
python scripts/decode_gmx_events.py

# 3) Compute wallet rankings
python scripts/compute_rankings.py

# 4) Reputation ranks (EndorseRank + AWP on Arbitrum Approval/Transfer)
python scripts/extract_reputation_data.py --dry-run
python scripts/extract_reputation_data.py --extract --yes
python scripts/preprocess_arbitrum_allowances.py
python scripts/preprocess_arbitrum_transfers.py
python scripts/compute_reputation_ranks.py

# Offline (no GCP):
python scripts/generate_synthetic_rankings.py
python scripts/generate_synthetic_reputation.py
```

## Django

```bash
cd web
python manage.py migrate
python manage.py import_rankings --source ../data/processed/wallet_rankings.parquet
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Success rate

```
success_rate = wins / total_closes
```

- **Close:** `PositionDecrease` event
- **Win:** `basePnlUsd > 0`
- **Loss:** `basePnlUsd <= 0` or liquidation (`orderType == 7`)
- **Filter:** `total_closes >= 3`

## Data products

| File | Description |
|------|-------------|
| `data/raw/gmx_event_logs_*.parquet` | Raw BigQuery logs |
| `data/processed/gmx_decoded_events.parquet` | Decoded decreases with account & PnL |
| `data/processed/wallet_rankings.parquet` | Final rankings (+ EndorseRank/AWP ranks) for Django import |
| `data/processed/reputation/latest_allowances.parquet` | Latest ERC-20 allowances (EndorseRank input) |
| `data/processed/reputation/transfer_events.parquet` | Transfer events with timestamps (AWP input) |

## Reputation ranks

- **EndorseRank:** Weighted PageRank on `owner → spender` approval graph (latest allowance weights, d=0.85)
- **AWP:** Adaptive Weighted PageRank on transfer graph with logistic time-decay (Do et al. 2023 style)
- Observation window: 2025-12-01 ~ 2026-05-31 (Arbitrum One)
