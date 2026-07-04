# Margin Rank — EndorseRank vs AWP evaluation pipeline

Arbitrum One ERC-20 allowance (EndorseRank) and transfer (AWP) reputation ranks, validated against **six proxy families**: transfer, allowance, GMX default/liquidation, inverse risk, Sybil-adjusted stability, and GMX trading success (see `config/margin_config.yaml` → `proxies`).

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

**Phase 3 — Evaluation, Tier 2 scaling, Tier 3 robustness (local)**

```bash
python scripts/sample_active_wallets.py --from-parquet --extract
python scripts/run_dissertation_eval.py --real --robustness --export-latex
```

Optional Tier~2 BQ reputation re-extract (`--tier2` writes to `data/raw/reputation_tier2/`). Use the project venv and `--resume` after interruptions; progress bars show overall step and download ETA:

```powershell
cd A-Skill-Programs/margin_rank
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python scripts/extract_reputation_data.py --tier2 --dry-run
python -u scripts/extract_reputation_data.py --tier2 --extract --yes --resume
python scripts/preprocess_tier2_reputation.py
```

If a step fails mid-download, re-run the same `--resume` command. Completed monthly parquets are skipped; batch chunks under `data/raw/reputation_tier2/*/_chunks/` and `job_id` in `extraction_manifest.json` let you continue without re-scanning when the BQ job is still valid. Press `Ctrl+C` during extraction to stop cleanly (no traceback); progress is checkpointed and `--resume` continues from the last batch.

Credit Delegation (deferred; records manifest only):

```bash
python scripts/extract_aave_lending.py --include-delegation --dry-run
```

Dry-run bytes and extraction metadata are written to `data/processed/extraction_manifest.json`. Per-query scan must stay under 150 GiB (`config/margin_config.yaml`).

## Scripts

| Script | Role |
|--------|------|
| `run_dissertation_eval.py` | Master offline/real eval → JSON (`--robustness` for Tier 3) |
| `run_robustness_eval.py` | Tier 3 damping / top-token / sample-size sweeps |
| `sample_active_wallets.py` | Tier 2 supplemental wallet pool (BQ or `--from-parquet`) |
| `preprocess_tier2_reputation.py` | Tier 2 processed allowances/transfers |
| `benchmark_runtime.py` | EndorseRank vs AWP runtime (`benchmark_tier2_scaling`) |
| `evaluate_alignment.py` | Spearman ρ / Kendall τ vs proxies |
| `export_latex_results.py` | JSON → dissertation LaTeX tables |
| `extract_margin_week.py` | GMX PositionDecrease BigQuery extraction |
| `extract_reputation_data.py` | Approval/Transfer BigQuery extraction |
| `generate_synthetic_*.py` | Offline fixture data |

See [docs/contract_wallet_exposure.md](docs/contract_wallet_exposure.md) for GMX wallet attribution rationale.

## Research log

실측 결과·가설 대비 판단·baseline 탐색: [`.cursor/journey.md`](../../.cursor/journey.md). `/git-commit` 시 자동 갱신. (구 경로 stub: [docs/research_log.md](docs/research_log.md))
