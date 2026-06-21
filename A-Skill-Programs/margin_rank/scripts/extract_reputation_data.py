#!/usr/bin/env python3
"""Extract Arbitrum ERC-20 Approval and Transfer logs for reputation scoring."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from google.cloud.bigquery import ArrayQueryParameter, QueryJobConfig, ScalarQueryParameter

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import format_bytes, load_config, load_json, read_sql, save_json  # noqa: E402

OBSERVATION_MONTHS = [
    ("2025-12", "2025-12-01 00:00:00 UTC", "2026-01-01 00:00:00 UTC"),
    ("2026-01", "2026-01-01 00:00:00 UTC", "2026-02-01 00:00:00 UTC"),
    ("2026-02", "2026-02-01 00:00:00 UTC", "2026-03-01 00:00:00 UTC"),
    ("2026-03", "2026-03-01 00:00:00 UTC", "2026-04-01 00:00:00 UTC"),
    ("2026-04", "2026-04-01 00:00:00 UTC", "2026-05-01 00:00:00 UTC"),
    ("2026-05", "2026-05-01 00:00:00 UTC", "2026-06-01 00:00:00 UTC"),
]


def get_client(config: dict) -> bigquery.Client:
    project = config.get("bigquery", {}).get("project_id")
    return bigquery.Client(project=project)


def load_wallet_addresses(config: dict, wallets_path: Path | None) -> list[str]:
    path = wallets_path or Path(config["paths"]["wallet_rankings"])
    if not path.exists():
        raise FileNotFoundError(
            f"Wallet rankings not found: {path}\n"
            "Run compute_rankings.py or generate_synthetic_rankings.py first."
        )
    df = pd.read_parquet(path)
    if "wallet" not in df.columns:
        raise ValueError(f"Missing wallet column in {path}")
    wallets = df["wallet"].astype(str).str.lower().unique().tolist()
    return sorted(wallets)


def _topic_to_address(topic: str | None) -> str | None:
    if topic is None or (isinstance(topic, float) and pd.isna(topic)):
        return None
    s = str(topic).lower().strip()
    if len(s) >= 42:
        return "0x" + s[-40:]
    return None


def _parse_uint256_data(data: str | None) -> str:
    if data is None or (isinstance(data, float) and pd.isna(data)):
        return "0"
    s = str(data).strip()
    if not s or s in ("0x", "0X"):
        return "0"
    try:
        return str(int(s, 16))
    except ValueError:
        return "0"


def normalize_approvals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["owner"] = out["owner_topic"].map(_topic_to_address)
    out["spender"] = out["spender_topic"].map(_topic_to_address)
    out["token_address"] = out["token_address"].astype(str).str.lower()
    out["value"] = out["value_data"].map(_parse_uint256_data)
    return out.dropna(subset=["owner", "spender"])


def normalize_transfers(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["from_address"] = out["from_topic"].map(_topic_to_address)
    out["to_address"] = out["to_topic"].map(_topic_to_address)
    out["token_address"] = out["token_address"].astype(str).str.lower()
    out["value"] = out["value_data"].map(_parse_uint256_data)
    return out.dropna(subset=["from_address", "to_address"])


def query_params(
    config: dict,
    wallets: list[str],
    start_ts: str,
    end_ts: str,
) -> list:
    rep = config["reputation"]
    return [
        ScalarQueryParameter("start_ts", "STRING", start_ts),
        ScalarQueryParameter("end_ts", "STRING", end_ts),
        ScalarQueryParameter("approval_topic0", "STRING", rep["approval_topic0"]),
        ScalarQueryParameter("transfer_topic0", "STRING", rep["transfer_topic0"]),
        ArrayQueryParameter("wallet_addresses", "STRING", wallets),
    ]


def dry_run_bytes(client: bigquery.Client, sql: str, params: list) -> int:
    job_config = QueryJobConfig(dry_run=True, use_query_cache=False, query_parameters=params)
    job = client.query(sql, job_config=job_config)
    return int(job.total_bytes_processed or 0)


def run_query(client: bigquery.Client, sql: str, params: list) -> pd.DataFrame:
    job_config = QueryJobConfig(use_query_cache=False, query_parameters=params)
    job = client.query(sql, job_config=job_config)
    return job.to_dataframe()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wallets", type=Path, help="Parquet with wallet column")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    if not args.dry_run and not args.extract:
        parser.error("Specify --dry-run or --extract")

    config = load_config()
    wallets = load_wallet_addresses(config, args.wallets)
    print(f"Wallet set: {len(wallets)} addresses")

    logs_fqn = config["bigquery"]["logs_fqn"]
    sql_approvals = read_sql("arbitrum_approvals.sql").replace("__LOGS_FQN__", logs_fqn)
    sql_transfers = read_sql("arbitrum_transfers.sql").replace("__LOGS_FQN__", logs_fqn)

    rep_paths = config["reputation"]["paths"]
    approvals_dir = Path(rep_paths["raw_approvals_dir"])
    transfers_dir = Path(rep_paths["raw_transfers_dir"])
    manifest_path = Path(config["paths"]["manifest"])
    budget_limit = config.get("budget", {}).get("max_bytes_per_query", 0)

    try:
        client = get_client(config)
    except Exception as exc:
        print(f"BigQuery client error: {exc}")
        print("Use: python scripts/generate_synthetic_reputation.py for offline mode.")
        return 1

    month_plans: list[dict] = []
    total_bytes = 0
    for label, start_ts, end_ts in OBSERVATION_MONTHS:
        params = query_params(config, wallets, start_ts, end_ts)
        bytes_app = dry_run_bytes(client, sql_approvals, params)
        bytes_tx = dry_run_bytes(client, sql_transfers, params)
        month_total = bytes_app + bytes_tx
        total_bytes += month_total
        print(
            f"  {label}: approvals {format_bytes(bytes_app)}, "
            f"transfers {format_bytes(bytes_tx)}"
        )
        if budget_limit and max(bytes_app, bytes_tx) > budget_limit:
            print(
                f"ERROR: {label} exceeds per-query budget "
                f"({format_bytes(budget_limit)})"
            )
            return 1
        month_plans.append(
            {
                "label": label,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "bytes_approvals": bytes_app,
                "bytes_transfers": bytes_tx,
            }
        )

    print(f"Dry-run total ({len(month_plans)} months): {format_bytes(total_bytes)}")

    manifest = load_json(manifest_path)
    manifest["reputation_extract"] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "wallet_count": len(wallets),
        "dry_run_bytes_total": total_bytes,
        "months": month_plans,
        "observation": {
            "start": config["reputation"]["observation_start_ts"],
            "end": config["reputation"]["observation_end_ts"],
        },
    }
    save_json(manifest_path, manifest)

    if args.dry_run:
        print("Dry-run complete.")
        return 0

    if not args.yes:
        resp = input(f"Extract ~{format_bytes(total_bytes)}? [y/N] ")
        if resp.strip().lower() != "y":
            print("Aborted.")
            return 0

    approvals_dir.mkdir(parents=True, exist_ok=True)
    transfers_dir.mkdir(parents=True, exist_ok=True)
    approval_frames: list[pd.DataFrame] = []
    transfer_frames: list[pd.DataFrame] = []
    bytes_processed = 0

    for mo in month_plans:
        label = mo["label"]
        params = query_params(config, wallets, mo["start_ts"], mo["end_ts"])
        print(f"Extracting {label}...")

        df_app = run_query(client, sql_approvals, params)
        df_app = normalize_approvals(df_app)
        app_month_path = approvals_dir / f"approvals_{label}.parquet"
        df_app.to_parquet(app_month_path, index=False)
        approval_frames.append(df_app)

        df_tx = run_query(client, sql_transfers, params)
        df_tx = normalize_transfers(df_tx)
        tx_month_path = transfers_dir / f"transfers_{label}.parquet"
        df_tx.to_parquet(tx_month_path, index=False)
        transfer_frames.append(df_tx)

        bytes_processed += mo["bytes_approvals"] + mo["bytes_transfers"]
        print(f"  {label}: {len(df_app)} approvals, {len(df_tx)} transfers")

    df_app_all = pd.concat(approval_frames, ignore_index=True) if approval_frames else pd.DataFrame()
    df_tx_all = pd.concat(transfer_frames, ignore_index=True) if transfer_frames else pd.DataFrame()
    app_path = approvals_dir / "approvals_arbitrum.parquet"
    tx_path = transfers_dir / "transfers_arbitrum.parquet"
    if not df_app_all.empty:
        df_app_all.to_parquet(app_path, index=False)
    if not df_tx_all.empty:
        df_tx_all.to_parquet(tx_path, index=False)

    manifest["reputation_extract"].update(
        {
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "approval_rows": len(df_app_all),
            "transfer_rows": len(df_tx_all),
            "bytes_processed": bytes_processed,
            "approvals_path": str(app_path),
            "transfers_path": str(tx_path),
        }
    )
    save_json(manifest_path, manifest)
    print(f"Approvals: {len(df_app_all)} rows -> {app_path}")
    print(f"Transfers: {len(df_tx_all)} rows -> {tx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
