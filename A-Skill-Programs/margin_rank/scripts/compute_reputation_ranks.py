#!/usr/bin/env python3
"""Compute seven reputation method scores/ranks and merge into wallet_rankings.parquet."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import load_config, load_json, save_json  # noqa: E402
from pagerank import assign_dense_ranks  # noqa: E402
from pagerank_variants import compute_variant_scores  # noqa: E402

METHOD_IDS = (
    "endorserank",
    "awp",
    "gf_pr",
    "lp_pr",
    "cw_awp",
    "lf_pr",
    "riskprop_pr",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rankings", type=Path, help="Input/output wallet_rankings.parquet")
    args = parser.parse_args()

    config = load_config()
    rep = config["reputation"]
    rankings_path = args.rankings or Path(config["paths"]["wallet_rankings"])
    allowances_path = Path(rep["paths"]["latest_allowances"])
    transfers_path = Path(rep["paths"]["transfer_events"])
    decoded_path = Path(config["paths"]["decoded_events"])
    aave_path = Path(config["paths"]["aave_events"])

    if not rankings_path.exists():
        print(f"Missing rankings: {rankings_path}")
        return 1
    if not allowances_path.exists():
        print(f"Missing allowances: {allowances_path}")
        return 1
    if not transfers_path.exists():
        print(f"Missing transfers: {transfers_path}")
        return 1
    if not decoded_path.exists():
        print(f"Missing decoded events: {decoded_path}")
        return 1

    rankings = pd.read_parquet(rankings_path)
    wallets = rankings["wallet"].astype(str).str.lower().tolist()

    allowances = pd.read_parquet(allowances_path)
    transfers = pd.read_parquet(transfers_path)
    decoded = pd.read_parquet(decoded_path)

    aave_events = None
    if aave_path.exists():
        aave_events = pd.read_parquet(aave_path)
    else:
        print(f"Note: {aave_path} missing; lf_pr scores will be zero.")

    scores, edge_counts = compute_variant_scores(
        wallets,
        config,
        allowances,
        transfers,
        decoded,
        aave_events,
    )

    rankings = rankings.copy()
    rankings["wallet"] = rankings["wallet"].astype(str).str.lower()

    for method in METHOD_IDS:
        if method not in scores:
            continue
        rank_df = assign_dense_ranks(wallets, scores[method])
        rank_map = rank_df.set_index("wallet")
        rankings[f"{method}_score"] = rankings["wallet"].map(
            lambda w, m=method: rank_map.loc[w, "score"] if w in rank_map.index else 0.0
        )
        rankings[f"{method}_rank"] = rankings["wallet"].map(
            lambda w, m=method: int(rank_map.loc[w, "rank"]) if w in rank_map.index else None
        )

    rankings.to_parquet(rankings_path, index=False)

    manifest_path = Path(config["paths"]["manifest"])
    manifest = load_json(manifest_path)
    manifest["reputation_ranks"] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "wallets": len(wallets),
        "methods": edge_counts,
        "output": str(rankings_path),
    }
    save_json(manifest_path, manifest)

    for method in METHOD_IDS:
        ec = edge_counts.get(method, 0)
        print(f"{method:14s}: {ec:>8} edges")
    print(f"Merged 7 methods -> {rankings_path} ({len(wallets)} wallets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
