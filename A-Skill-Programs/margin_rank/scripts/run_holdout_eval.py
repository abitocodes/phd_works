#!/usr/bin/env python3
"""t1 EndorseRank/AWP scores versus pre-registered t2 labels.

Does not overwrite contemporaneous dissertation eval_summary.json.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import load_config, save_json  # noqa: E402
from holdout import (  # noqa: E402
    HOLDOUT_LABELS,
    build_holdout_fixture_frames,
    correlate_holdout,
    filter_transfers_as_of,
    future_approval_labels,
    future_gmx_labels,
    holdout_bounds,
    latest_positive_as_of,
    load_approval_events,
    load_transfer_events,
    resolve_score_wallets,
    score_awp,
    score_endorserank,
    scores_to_frame,
    t1_connected_wallets,
)
from pagerank import build_awp_edges, build_endorserank_edges  # noqa: E402


def _load_matched_wallets(config: dict) -> list[str] | None:
    path = Path(config["paths"]["wallet_rankings"])
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    return df["wallet"].astype(str).str.lower().tolist()


def _score_methods(
    latest_t1: pd.DataFrame,
    transfers_t1: pd.DataFrame,
    score_end: pd.Timestamp,
    wallets: list[str],
    config: dict,
) -> dict[str, dict[str, float]]:
    return {
        "endorserank": score_endorserank(latest_t1, wallets, config),
        "awp": score_awp(transfers_t1, score_end, wallets, config),
    }


def run_holdout(
    config: dict,
    approvals: pd.DataFrame,
    transfers: pd.DataFrame,
    decoded: pd.DataFrame,
    matched: list[str] | None,
    extra_scores: dict[str, dict[str, float]] | None = None,
) -> dict:
    score_end, outcome_start, outcome_end = holdout_bounds(config)
    ho = config["reputation"]["holdout"]
    min_closes = int(ho.get("min_closes", 3))
    n_boot = int(ho.get("bootstrap_resamples", 400))
    seed = int(ho.get("bootstrap_seed", 42))

    latest_t1 = latest_positive_as_of(approvals, score_end)
    transfers_t1 = filter_transfers_as_of(transfers, score_end)
    rep = config["reputation"]
    er_edges = build_endorserank_edges(latest_t1)
    awp_edges = build_awp_edges(
        transfers_t1,
        score_end,
        float(rep["awp_decay_k"]),
        float(rep["awp_decay_t0_days"]),
    )
    t1_nodes = t1_connected_wallets(er_edges, awp_edges)
    wallets = resolve_score_wallets(matched, t1_nodes)
    if not wallets:
        raise RuntimeError("No t1-connected wallets after holdout filters.")

    scores = _score_methods(latest_t1, transfers_t1, score_end, wallets, config)
    if extra_scores:
        scores.update(extra_scores)

    frame = scores_to_frame(wallets, scores)
    labels = future_approval_labels(
        approvals, latest_t1, outcome_start, outcome_end, wallets
    )
    gmx = future_gmx_labels(decoded, outcome_start, outcome_end, wallets, min_closes)
    merged = frame.merge(labels, on="wallet", how="left").merge(gmx, on="wallet", how="left")

    methods = list(scores.keys())
    alignment = correlate_holdout(
        merged, methods, labels=HOLDOUT_LABELS, n_resamples=n_boot, seed=seed
    )
    return {
        "protocol": "t1_score_vs_t2_label",
        "score_end": str(score_end),
        "outcome_start": str(outcome_start),
        "outcome_end": str(outcome_end),
        "n_wallets": len(wallets),
        "n_t1_allowance_rows": int(len(latest_t1)),
        "n_t1_transfers": int(len(transfers_t1)),
        "methods": methods,
        "alignment": alignment,
        "at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures",
        action="store_true",
        help="Use synthetic events that straddle the holdout cutoff.",
    )
    parser.add_argument("--n-wallets", type=int, default=48)
    args = parser.parse_args()

    config = load_config()
    out_path = Path(config["reputation"]["paths"]["holdout_summary"])

    if args.fixtures:
        frames = build_holdout_fixture_frames(n_wallets=args.n_wallets)
        matched = frames["wallets"]["wallet"].tolist()
        summary = run_holdout(
            config,
            frames["approvals"],
            frames["transfers"],
            frames["decoded"],
            matched,
        )
        summary["source"] = "fixtures"
    else:
        approvals = load_approval_events(config)
        transfers = load_transfer_events(config)
        decoded_path = Path(config["paths"]["decoded_events"])
        if not decoded_path.exists():
            print(f"Missing {decoded_path}; use --fixtures or run the GMX decode step.")
            return 1
        decoded = pd.read_parquet(decoded_path)
        summary = run_holdout(
            config, approvals, transfers, decoded, _load_matched_wallets(config)
        )
        summary["source"] = "local_parquet"

    save_json(out_path, summary)
    print(f"holdout n={summary['n_wallets']} methods={summary['methods']}")
    for method, labels in summary["alignment"]["methods"].items():
        new = labels.get("future_new_approvers", {})
        print(
            f"  {method:12s} future_new_approvers tau="
            f"{new.get('kendall_tau')} ci=({new.get('ci_low')}, {new.get('ci_high')}) n={new.get('n')}"
        )
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
