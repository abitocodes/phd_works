#!/usr/bin/env python3
"""Extract GMX PositionDecrease logs from BigQuery for the analysis week."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    PROCESSED_DIR,
    RAW_DIR,
    format_bytes,
    load_config,
    read_sql,
    save_json,
)


def get_client(config: dict) -> bigquery.Client:
    project = config.get("bigquery", {}).get("project_id")
    return bigquery.Client(project=project)


def query_params(config: dict) -> list:
    period = config["period"]
    gmx = config["gmx_arbitrum"]
    ev = config["events"]
    return [
        ScalarQueryParameter("start_ts", "STRING", period["start_ts"]),
        ScalarQueryParameter("end_ts", "STRING", period["end_ts"]),
        ScalarQueryParameter("event_emitter", "STRING", gmx["event_emitter"]),
        ScalarQueryParameter("event_log1_topic0", "STRING", ev["event_log1_topic0"]),
        ScalarQueryParameter(
            "position_decrease_hash", "STRING", ev["position_decrease_hash"]
        ),
    ]


def dry_run_bytes(client: bigquery.Client, sql: str, params: list) -> int:
    job_config = QueryJobConfig(dry_run=True, use_query_cache=False, query_parameters=params)
    job = client.query(sql, job_config=job_config)
    return int(job.total_bytes_processed or 0)


def run_to_parquet(
    client: bigquery.Client,
    sql: str,
    params: list,
    out_path: Path,
) -> tuple[int, int]:
    job_config = QueryJobConfig(use_query_cache=False, query_parameters=params)
    job = client.query(sql, job_config=job_config)
    df = job.to_dataframe()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    return len(df), int(job.total_bytes_processed or 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Dry-run only")
    parser.add_argument("--extract", action="store_true", help="Run extraction")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation")
    args = parser.parse_args()

    if not args.dry_run and not args.extract:
        parser.error("Specify --dry-run or --extract")

    config = load_config()
    sql = read_sql("gmx_event_logs.sql").replace(
        "__LOGS_FQN__", config["bigquery"]["logs_fqn"]
    )
    params = query_params(config)
    out_path = Path(config["paths"]["raw_logs"])
    manifest_path = Path(config["paths"]["manifest"])
    budget_limit = config.get("budget", {}).get("max_bytes_per_query", 0)

    try:
        client = get_client(config)
    except Exception as exc:
        print(f"BigQuery client error: {exc}")
        print("Use: python scripts/generate_synthetic_rankings.py for offline mode.")
        return 1

    bytes_est = dry_run_bytes(client, sql, params)
    print(f"Dry-run bytes: {format_bytes(bytes_est)}")
    if budget_limit and bytes_est > budget_limit:
        print(f"ERROR: exceeds per-query budget ({format_bytes(budget_limit)})")
        return 1

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "synthetic": False,
        "period": config["period"],
        "protocol": config["protocol"],
        "dry_run_bytes": bytes_est,
    }
    save_json(manifest_path, manifest)

    if args.dry_run:
        print("Dry-run complete.")
        return 0

    if not args.yes:
        resp = input(f"Extract ~{format_bytes(bytes_est)} to {out_path}? [y/N] ")
        if resp.strip().lower() != "y":
            print("Aborted.")
            return 0

    rows, bytes_proc = run_to_parquet(client, sql, params, out_path)
    manifest.update(
        {
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "rows": rows,
            "bytes_processed": bytes_proc,
            "output": str(out_path),
        }
    )
    save_json(manifest_path, manifest)
    print(f"Extracted {rows} rows -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
