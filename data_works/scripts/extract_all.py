#!/usr/bin/env python3
"""BigQuery extraction with backward budget planning (1 TiB free tier)."""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter, ArrayQueryParameter

# Allow running as script from repo root or data_works/
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    PROCESSED_DIR,
    RAW_DIR,
    attach_block_ranges,
    format_bytes,
    iter_months_backward,
    load_config,
    load_json,
    normalize_address,
    read_sql,
    save_json,
)


def get_client(config: dict) -> bigquery.Client:
    project = config.get("bigquery", {}).get("project_id")
    return bigquery.Client(project=project)


def dry_run_bytes(
    client: bigquery.Client,
    sql: str,
    params: list,
) -> int:
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
    bytes_processed = int(job.total_bytes_processed or 0)
    return len(df), bytes_processed


def approval_params(mo: dict, config: dict) -> list:
    fw = config["feature_window"]
    ev = config["events"]
    return [
        ScalarQueryParameter("start_ts", "STRING", mo["start_ts"]),
        ScalarQueryParameter("end_ts", "STRING", mo["end_ts"]),
        ScalarQueryParameter("start_block", "INT64", mo["start_block"]),
        ScalarQueryParameter("end_block", "INT64", mo["end_block"]),
        ScalarQueryParameter("approval_topic0", "STRING", ev["approval_topic0"]),
    ]


def transfer_params(mo: dict, wallets: list[str]) -> list:
    # Deduplicate and normalize
    seen: set[str] = set()
    addrs: list[str] = []
    for w in wallets:
        n = normalize_address(w)
        if n and n not in seen:
            seen.add(n)
            addrs.append(n)
    if not addrs:
        addrs = ["0x0000000000000000000000000000000000000000"]
    return [
        ScalarQueryParameter("start_ts", "STRING", mo["start_ts"]),
        ScalarQueryParameter("end_ts", "STRING", mo["end_ts"]),
        ScalarQueryParameter("start_block", "INT64", mo["start_block"]),
        ScalarQueryParameter("end_block", "INT64", mo["end_block"]),
        ArrayQueryParameter("wallet_addresses", "STRING", addrs),
    ]


def liquidation_params(start_ts: str, end_ts: str, config: dict) -> list:
    ev = config["events"]
    pools = [p.lower() for p in config["aave_v3_pools"]]
    return [
        ScalarQueryParameter("start_ts", "STRING", start_ts),
        ScalarQueryParameter("end_ts", "STRING", end_ts),
        ScalarQueryParameter("liquidation_topic0", "STRING", ev["liquidation_topic0"]),
        ArrayQueryParameter("pool_addresses", "STRING", pools),
    ]


def fetch_wallet_seeds(client: bigquery.Client, config: dict) -> list[str]:
    """Small outcome-window liquidation query to seed transfer wallet filter."""
    ow = config["outcome_window"]
    sql = read_sql("aave_liquidations.sql")
    start_ts = f"{ow['start_date']} 00:00:00 UTC"
    # exclusive end: day after outcome end
    end_ts = "2027-01-01 00:00:00 UTC"
    params = liquidation_params(start_ts, end_ts, config)
    job_config = QueryJobConfig(use_query_cache=False, query_parameters=params)
    job = client.query(sql, job_config=job_config)
    df = job.to_dataframe()
    wallets: set[str] = set()
    for p in config["aave_v3_pools"]:
        w = normalize_address(p)
        if w:
            wallets.add(w)
    if not df.empty and "user_address" in df.columns:
        for u in df["user_address"].dropna().unique():
            w = normalize_address(u)
            if w:
                wallets.add(w)
    if not df.empty and "liquidator" in df.columns:
        for u in df["liquidator"].dropna().unique():
            w = normalize_address(u)
            if w:
                wallets.add(w)
    return sorted(wallets)


def build_months(config: dict) -> list[dict]:
    fw = config["feature_window"]
    end = date.fromisoformat(fw["end_date"])
    earliest = date.fromisoformat(fw["earliest_candidate"])
    months = iter_months_backward(end, earliest)
    attach_block_ranges(
        months,
        earliest_date=earliest,
        end_date=end,
        earliest_block=int(fw["earliest_block"]),
        end_block=int(fw["end_block"]),
    )
    return months


def budget_plan(client: bigquery.Client, config: dict) -> dict:
    budget = config["budget"]
    max_total = int(budget["max_total_bytes"])
    max_per_query = int(budget["max_bytes_per_query"])

    approval_sql = read_sql("approvals_monthly.sql")
    transfer_sql = read_sql("token_transfers_wallet_filter.sql")
    liq_sql = read_sql("aave_liquidations.sql")

    ow = config["outcome_window"]
    fw = config["feature_window"]

    outcome_start = f"{ow['start_date']} 00:00:00 UTC"
    outcome_end = "2027-01-01 00:00:00 UTC"
    outcome_bytes = dry_run_bytes(
        client, liq_sql, liquidation_params(outcome_start, outcome_end, config)
    )

    reserved = outcome_bytes
    cumulative = 0
    included: list[dict] = []
    monthly_dry_runs: list[dict] = []

    wallet_seeds = fetch_wallet_seeds(client, config)
    print(f"Wallet seeds for transfer dry-run: {len(wallet_seeds)}")

    months = build_months(config)

    for mo in months:
        ap_bytes = dry_run_bytes(client, approval_sql, approval_params(mo, config))
        tr_bytes = dry_run_bytes(
            client, transfer_sql, transfer_params(mo, wallet_seeds)
        )
        month_total = ap_bytes + tr_bytes

        entry = {
            "month": mo["label"],
            "approval_bytes": ap_bytes,
            "transfer_bytes": tr_bytes,
            "month_total_bytes": month_total,
        }

        if ap_bytes > max_per_query or tr_bytes > max_per_query:
            entry["skipped"] = True
            entry["skip_reason"] = "single_query_exceeds_150_gib"
            monthly_dry_runs.append(entry)
            break

        if reserved + cumulative + month_total > max_total:
            entry["skipped"] = True
            entry["skip_reason"] = "budget_exceeded"
            monthly_dry_runs.append(entry)
            break

        cumulative += month_total
        entry["cumulative_bytes"] = cumulative
        entry["reserved_plus_cumulative"] = reserved + cumulative
        included.append(mo)
        monthly_dry_runs.append(entry)

    if not included:
        raise RuntimeError("Budget plan included zero months; check GCP auth and config.")

    # Feature liquidation dry-run over full included span
    start_mo = included[-1]
    end_mo = included[0]
    feature_start = start_mo["start_ts"]
    feature_end = end_mo["end_ts"]
    feature_liq_bytes = dry_run_bytes(
        client,
        liq_sql,
        liquidation_params(feature_start, feature_end, config),
    )
    reserved += feature_liq_bytes

    total_planned = reserved + cumulative

    plan = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "budget_bytes_limit": max_total,
        "budget_bytes_planned": total_planned,
        "outcome_liquidation_bytes": outcome_bytes,
        "feature_liquidation_bytes": feature_liq_bytes,
        "reserved_bytes": reserved,
        "monthly_cumulative_bytes": cumulative,
        "feature_window": {
            "start_date": start_mo["start_date"].isoformat(),
            "end_date": fw["end_date"],
            "months_included": len(included),
            "month_labels": [m["label"] for m in reversed(included)],
        },
        "monthly_dry_runs": monthly_dry_runs,
        "months_included_detail": [
            {
                "label": m["label"],
                "start_ts": m["start_ts"],
                "end_ts": m["end_ts"],
                "start_block": m["start_block"],
                "end_block": m["end_block"],
            }
            for m in reversed(included)
        ],
    }

    out_path = PROCESSED_DIR / "budget_plan.json"
    save_json(out_path, plan)
    print(f"\nBudget plan saved: {out_path}")
    print(f"  Start date: {plan['feature_window']['start_date']}")
    print(f"  End date:   {plan['feature_window']['end_date']}")
    print(f"  Months:     {plan['feature_window']['months_included']}")
    print(f"  Planned:    {format_bytes(total_planned)} / {format_bytes(max_total)}")
    return plan


def load_budget_plan() -> dict:
    path = PROCESSED_DIR / "budget_plan.json"
    plan = load_json(path)
    if not plan:
        raise FileNotFoundError(
            f"Missing {path}. Run with --budget-plan first."
        )
    return plan


def collect_wallets_from_parquet(paths: list[Path], columns: list[str]) -> set[str]:
    wallets: set[str] = set()
    for p in paths:
        if not p.exists():
            continue
        df = pd.read_parquet(p)
        for col in columns:
            if col in df.columns:
                for v in df[col].dropna().unique():
                    w = normalize_address(str(v))
                    if w:
                        wallets.add(w)
    return wallets


def extract(client: bigquery.Client, config: dict, plan: dict, skip_existing: bool) -> dict:
    approval_sql = read_sql("approvals_monthly.sql")
    transfer_sql = read_sql("token_transfers_wallet_filter.sql")
    liq_sql = read_sql("aave_liquidations.sql")

    manifest: dict = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "budget_plan": plan,
        "extractions": [],
        "total_bytes_processed": 0,
        "total_rows": 0,
    }

    total_bytes = 0
    total_rows = 0

    # Outcome liquidations (required)
    ow = config["outcome_window"]
    outcome_path = RAW_DIR / "aave_liquidations" / "liquidations_outcome_2026-H2.parquet"
    if skip_existing and outcome_path.exists():
        print(f"Skip existing: {outcome_path}")
    else:
        n, b = run_to_parquet(
            client,
            liq_sql,
            liquidation_params(f"{ow['start_date']} 00:00:00 UTC", "2027-01-01 00:00:00 UTC", config),
            outcome_path,
        )
        total_bytes += b
        total_rows += n
        manifest["extractions"].append(
            {"dataset": "liquidations_outcome", "path": str(outcome_path), "rows": n, "bytes": b}
        )
        print(f"Outcome liquidations: {n} rows, {format_bytes(b)}")

    month_details = plan.get("months_included_detail") or []
    if not month_details:
        labels = plan["feature_window"]["month_labels"]
        months_all = build_months(config)
        by_label = {m["label"]: m for m in months_all}
        month_details = [by_label[l] for l in labels if l in by_label]

    approval_paths: list[Path] = []

    # Pass 1: approvals month by month
    for mo in month_details:
        label = mo["label"]
        out = RAW_DIR / "approvals" / f"approvals_{label}.parquet"
        if skip_existing and out.exists():
            print(f"Skip existing: {out}")
            approval_paths.append(out)
            continue
        mo_full = mo
        if "start_date" not in mo:
            months_all = build_months(config)
            mo_full = next(m for m in months_all if m["label"] == label)
        n, b = run_to_parquet(
            client, approval_sql, approval_params(mo_full, config), out
        )
        total_bytes += b
        total_rows += n
        approval_paths.append(out)
        manifest["extractions"].append(
            {"dataset": "approvals", "month": label, "path": str(out), "rows": n, "bytes": b}
        )
        print(f"Approvals {label}: {n} rows, {format_bytes(b)}")

    # Wallet set for transfers
    wallet_seeds = fetch_wallet_seeds(client, config)
    approval_wallets = collect_wallets_from_parquet(
        approval_paths, ["owner", "spender"]
    )
    wallets = sorted(wallet_seeds | approval_wallets)
    print(f"Transfer wallet filter size: {len(wallets)}")

    # Pass 2: transfers
    for mo in month_details:
        label = mo["label"]
        out = RAW_DIR / "token_transfers" / f"transfers_{label}.parquet"
        if skip_existing and out.exists():
            print(f"Skip existing: {out}")
            continue
        mo_full = mo
        if "start_date" not in mo:
            months_all = build_months(config)
            mo_full = next(m for m in months_all if m["label"] == label)
        n, b = run_to_parquet(
            client, transfer_sql, transfer_params(mo_full, wallets), out
        )
        total_bytes += b
        total_rows += n
        manifest["extractions"].append(
            {"dataset": "token_transfers", "month": label, "path": str(out), "rows": n, "bytes": b}
        )
        print(f"Transfers {label}: {n} rows, {format_bytes(b)}")

    # Feature liquidations
    start_mo = month_details[0]
    end_mo = month_details[-1]
    feature_path = RAW_DIR / "aave_liquidations" / "liquidations_feature.parquet"
    if skip_existing and feature_path.exists():
        print(f"Skip existing: {feature_path}")
    else:
        months_all = build_months(config)
        if "start_ts" not in start_mo:
            start_mo = next(m for m in months_all if m["label"] == start_mo["label"])
            end_mo = next(m for m in months_all if m["label"] == end_mo["label"])
        n, b = run_to_parquet(
            client,
            liq_sql,
            liquidation_params(start_mo["start_ts"], end_mo["end_ts"], config),
            feature_path,
        )
        total_bytes += b
        total_rows += n
        manifest["extractions"].append(
            {"dataset": "liquidations_feature", "path": str(feature_path), "rows": n, "bytes": b}
        )
        print(f"Feature liquidations: {n} rows, {format_bytes(b)}")

    manifest["total_bytes_processed"] = total_bytes
    manifest["total_rows"] = total_rows
    manifest["feature_window"] = plan["feature_window"]
    manifest["outcome_window"] = config["outcome_window"]

    save_json(PROCESSED_DIR / "extraction_manifest.json", manifest)
    print(f"\nManifest: {PROCESSED_DIR / 'extraction_manifest.json'}")
    print(f"Total: {total_rows} rows, {format_bytes(total_bytes)}")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="BigQuery proposal data extraction")
    parser.add_argument("--budget-plan", action="store_true", help="Dry-run backward budget plan")
    parser.add_argument("--extract", action="store_true", help="Run extraction from budget plan")
    parser.add_argument("--dry-run-only", action="store_true", help="Alias for --budget-plan")
    parser.add_argument("--skip-existing", action="store_true", help="Skip existing parquet files")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation before extract")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Offline mode: write synthetic data (no BigQuery credentials)",
    )
    args = parser.parse_args()

    if not args.budget_plan and not args.extract and not args.dry_run_only:
        parser.error("Specify --budget-plan or --extract")

    config = load_config()

    if args.synthetic:
        from generate_synthetic import build_budget_plan, write_synthetic_data

        if args.budget_plan or args.dry_run_only:
            plan = build_budget_plan(config)
            save_json(PROCESSED_DIR / "budget_plan.json", plan)
            print("Synthetic budget plan written.")
            return
        if args.extract:
            try:
                plan = load_budget_plan()
            except FileNotFoundError:
                plan = build_budget_plan(config)
            write_synthetic_data(plan, config)
            print("Synthetic extraction complete.")
            return
        parser.error("With --synthetic, use --budget-plan or --extract")

    client = get_client(config)

    if args.budget_plan or args.dry_run_only:
        budget_plan(client, config)
        return

    plan = load_budget_plan()
    planned = int(plan.get("budget_bytes_planned", 0))
    limit = int(config["budget"]["max_total_bytes"])
    print(f"Planned scan: {format_bytes(planned)} / {format_bytes(limit)}")
    if planned > limit:
        raise RuntimeError("Budget plan exceeds limit; re-run --budget-plan.")

    if not args.yes:
        ans = input("Proceed with extraction? [y/N]: ").strip().lower()
        if ans not in ("y", "yes"):
            print("Aborted.")
            return

    extract(client, config, plan, skip_existing=args.skip_existing)


if __name__ == "__main__":
    main()
