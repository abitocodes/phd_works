#!/usr/bin/env python3
"""Compute EndorseRank and AWP scores/ranks and merge into wallet_rankings.parquet."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import load_config, load_json, save_json  # noqa: E402
from pagerank import (  # noqa: E402
    assign_dense_ranks,
    build_awp_edges,
    build_endorserank_edges,
    filter_subgraph_edges,
    weighted_pagerank,
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

    if not rankings_path.exists():
        print(f"Missing rankings: {rankings_path}")
        return 1
    if not allowances_path.exists():
        print(f"Missing allowances: {allowances_path}")
        return 1
    if not transfers_path.exists():
        print(f"Missing transfers: {transfers_path}")
        return 1

    rankings = pd.read_parquet(rankings_path)
    wallets = rankings["wallet"].astype(str).str.lower().tolist()
    seed = set(wallets)

    allowances = pd.read_parquet(allowances_path)
    transfers = pd.read_parquet(transfers_path)

    endorse_edges = build_endorserank_edges(allowances)
    endorse_edges = filter_subgraph_edges(endorse_edges, seed)
    endorse_scores = weighted_pagerank(
        endorse_edges,
        damping=float(rep["damping"]),
        tol=float(rep["pagerank_tolerance"]),
        max_iter=int(rep["max_iterations"]),
    )
    endorse_ranks = assign_dense_ranks(wallets, endorse_scores)

    observation_end = pd.Timestamp(rep["observation_end"], tz="UTC")
    awp_edge_df = build_awp_edges(
        transfers,
        observation_end=observation_end,
        k=float(rep["awp_decay_k"]),
        t0_days=float(rep["awp_decay_t0_days"]),
    )
    awp_edges = filter_subgraph_edges(awp_edge_df, seed)
    awp_scores = weighted_pagerank(
        awp_edges,
        damping=float(rep["damping"]),
        tol=float(rep["pagerank_tolerance"]),
        max_iter=int(rep["max_iterations"]),
    )
    awp_ranks = assign_dense_ranks(wallets, awp_scores)

    er_map = endorse_ranks.set_index("wallet")
    awp_map = awp_ranks.set_index("wallet")

    rankings = rankings.copy()
    rankings["wallet"] = rankings["wallet"].astype(str).str.lower()
    rankings["endorserank_score"] = rankings["wallet"].map(
        lambda w: er_map.loc[w, "score"] if w in er_map.index else 0.0
    )
    rankings["endorserank_rank"] = rankings["wallet"].map(
        lambda w: int(er_map.loc[w, "rank"]) if w in er_map.index else None
    )
    rankings["awp_score"] = rankings["wallet"].map(
        lambda w: awp_map.loc[w, "score"] if w in awp_map.index else 0.0
    )
    rankings["awp_rank"] = rankings["wallet"].map(
        lambda w: int(awp_map.loc[w, "rank"]) if w in awp_map.index else None
    )

    rankings.to_parquet(rankings_path, index=False)

    manifest_path = Path(config["paths"]["manifest"])
    manifest = load_json(manifest_path)
    manifest["reputation_ranks"] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "wallets": len(wallets),
        "endorse_edges": len(endorse_edges),
        "awp_edges": len(awp_edges),
        "output": str(rankings_path),
    }
    save_json(manifest_path, manifest)

    print(f"EndorseRank: {len(endorse_edges)} edges, ranked {len(wallets)} wallets")
    print(f"AWP:         {len(awp_edges)} edges, ranked {len(wallets)} wallets")
    print(f"Merged -> {rankings_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
