#!/usr/bin/env python3
"""Checks run after the spring results were known.

Each check asks how much a reported finding rests on a choice made in this
pipeline. None was fixed before the results were seen, so the dissertation
reports them as post hoc.

tie_sensitivity    Matched cohort, same window. The main analysis scores a
                   wallet that is missing from a graph zero. Here the missing
                   wallets are kept as isolated nodes, which gives each of them
                   the score of a node without in-edges.
holdout_weighting  Spender holdout. EndorseRank and AWP with each event counted
                   once (count) or each pair counted once (unit) instead of
                   raw token amounts, and the single-layer methods on the
                   spenders that received transfers before the freeze.
trader_counts      Spring counts behind the trader label of the registered
                   replication.

Output: data/processed/supplementary_checks.json (read by export_latex_results.py).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PROCESSED_DIR, load_config, save_json, tier2_reputation_paths  # noqa: E402
from evaluate_alignment import bootstrap_alignment  # noqa: E402
from holdout import (  # noqa: E402
    bootstrap_kendall,
    filter_transfers_as_of,
    future_approval_labels,
    future_transfer_labels,
    holdout_bounds,
    holdout_tau_diff,
    latest_positive_as_of,
    load_approval_events,
    load_transfer_events,
    pagerank_params,
    resolve_score_wallets,
    t1_baselines,
    t1_connected_wallets,
)
from pagerank import (  # noqa: E402
    build_awp_edges,
    build_endorserank_edges,
    build_weighted_edges,
    filter_subgraph_edges,
    logistic_time_decay,
    weighted_pagerank,
)
from proxy_metrics import compute_all_proxies  # noqa: E402

OUT_PATH = PROCESSED_DIR / "supplementary_checks.json"

TIE_METHODS = {"endorserank": "endorserank_score", "awp": "awp_score"}

HOLDOUT_LABELS = ("future_new_approvers", "future_new_transfer_senders")
WEIGHTING_METHODS = (
    "endorserank_raw",
    "endorserank_count",
    "endorserank_unit",
    "awp_raw",
    "awp_count",
    "awp_unit",
    "t1_in_approve_degree",
    "t1_in_degree",
)
# (label, method_a, method_b, holdout label, group); same layout as holdout.HOLDOUT_CONTRASTS.
WEIGHTING_CONTRASTS: tuple[tuple[str, str, str, str, str], ...] = (
    ("AWP count minus AWP", "awp_count", "awp_raw", "future_new_transfer_senders", "weights"),
    ("AWP count minus t1 in-degree", "awp_count", "t1_in_degree", "future_new_transfer_senders", "weights"),
    ("EndorseRank minus AWP count", "endorserank_raw", "awp_count", "future_new_transfer_senders", "weights"),
    ("EndorseRank count minus EndorseRank", "endorserank_count", "endorserank_raw", "future_new_approvers", "weights"),
    ("EndorseRank count minus AWP count", "endorserank_count", "awp_count", "future_new_approvers", "weights"),
    ("EndorseRank count minus AWP count", "endorserank_count", "awp_count", "future_new_transfer_senders", "weights"),
    ("EndorseRank unit minus AWP unit", "endorserank_unit", "awp_unit", "future_new_approvers", "weights"),
    ("EndorseRank unit minus AWP unit", "endorserank_unit", "awp_unit", "future_new_transfer_senders", "weights"),
)
RECEIVING_CONTRASTS: tuple[tuple[str, str, str, str, str], ...] = (
    ("EndorseRank minus AWP", "endorserank_raw", "awp_raw", "future_new_approvers", "receiving"),
    ("EndorseRank minus AWP", "endorserank_raw", "awp_raw", "future_new_transfer_senders", "receiving"),
    ("AWP minus t1 in-degree", "awp_raw", "t1_in_degree", "future_new_transfer_senders", "receiving"),
)


def _tied_pair_share(values: np.ndarray) -> float:
    _, counts = np.unique(values, return_counts=True)
    n = values.size
    return float((counts * (counts - 1) // 2).sum() / (n * (n - 1) // 2))


def tie_sensitivity(
    config: dict[str, Any],
    rankings: pd.DataFrame,
    allowances: pd.DataFrame,
    transfers: pd.DataFrame,
    proxies: pd.DataFrame,
    n_boot: int,
    seed: int,
) -> dict[str, Any]:
    """Same-window alignment with missing wallets scored zero or kept as isolated nodes."""
    rep = config["reputation"]
    damping, tol, max_iter = pagerank_params(config)
    observation_end = pd.Timestamp(rep["observation_end"], tz="UTC")
    cohort = set(rankings["wallet"])
    edges = {
        "endorserank": filter_subgraph_edges(build_endorserank_edges(allowances), cohort),
        "awp": filter_subgraph_edges(
            build_awp_edges(
                transfers, observation_end, float(rep["awp_decay_k"]), float(rep["awp_decay_t0_days"])
            ),
            cohort,
        ),
    }
    zero_rule = rankings[["wallet", *TIE_METHODS.values()]].merge(proxies, on="wallet", how="inner")
    isolated = zero_rule.copy()
    wallets = zero_rule["wallet"].tolist()
    methods: dict[str, Any] = {}
    for method, col in TIE_METHODS.items():
        e = edges[method]
        missing = sorted(cohort - (set(e["from_node"]) | set(e["to_node"])))
        committed = zero_rule[col].to_numpy(float)
        recomputed = weighted_pagerank(e, damping=damping, tol=tol, max_iter=max_iter)
        with_isolated = weighted_pagerank(
            e, damping=damping, tol=tol, max_iter=max_iter, extra_nodes=set(missing)
        )
        iso_scores = np.asarray([with_isolated[w] for w in wallets], dtype=float)
        isolated[col] = iso_scores
        node_score = float(with_isolated[missing[0]]) if missing else None
        methods[method] = {
            "n_missing": len(missing),
            "recomputed_matches_committed": bool(
                np.allclose([recomputed.get(w, 0.0) for w in wallets], committed, rtol=1e-9, atol=0.0)
            ),
            "isolated_node_score": node_score,
            "n_at_isolated_node_score": int((iso_scores == node_score).sum()) if missing else 0,
            "tied_pair_share": {
                "zero_rule": _tied_pair_share(committed),
                "isolated_nodes": _tied_pair_share(iso_scores),
            },
        }
    out: dict[str, Any] = {"n_wallets": len(zero_rule), "methods": methods}
    for rule, frame in (("zero_rule", zero_rule), ("isolated_nodes", isolated)):
        boot = bootstrap_alignment(frame, TIE_METHODS, n_boot=n_boot, seed=seed)
        er_ties = methods["endorserank"]["tied_pair_share"][rule]
        out[rule] = {
            "family_ci": boot["family_ci"],
            "proxy_ci": boot["proxy_ci"],
            "inter_method_ci": boot["inter_method_ci"],
            "tau_diff": [r for r in boot["tau_diff"] if r.get("group") == "primary"],
            # Largest tau_b EndorseRank can reach against a proxy without ties.
            "endorserank_ceiling_untied_proxy": float(np.sqrt(1.0 - er_ties)),
        }
    return out


def _score_on(edges: pd.DataFrame, wallets: list[str], params: tuple[float, float, int]) -> list[float]:
    damping, tol, max_iter = params
    scores = weighted_pagerank(
        filter_subgraph_edges(edges, set(wallets)), damping=damping, tol=tol, max_iter=max_iter
    )
    return [scores.get(w, 0.0) for w in wallets]


def holdout_weighting(
    config: dict[str, Any],
    approvals: pd.DataFrame,
    transfers: pd.DataFrame,
    latest_t1: pd.DataFrame,
    transfers_t1: pd.DataFrame,
    n_boot: int,
    seed: int,
) -> dict[str, Any]:
    """Spender holdout with the walks re-weighted, and on spenders that received transfers."""
    rep = config["reputation"]
    params = pagerank_params(config)
    score_end, outcome_start, outcome_end = holdout_bounds(config)
    k, t0 = float(rep["awp_decay_k"]), float(rep["awp_decay_t0_days"])
    spenders = sorted(set(latest_t1["spender"].astype(str).str.lower()))
    er_raw = build_endorserank_edges(latest_t1)
    awp_raw = build_awp_edges(transfers_t1, score_end, k, t0)
    wallets = resolve_score_wallets(spenders, t1_connected_wallets(er_raw, awp_raw))

    delta_days = (score_end - transfers_t1["block_timestamp"]).dt.total_seconds() / 86400.0
    counted = transfers_t1.assign(decay=logistic_time_decay(delta_days, k, t0), one=1.0)
    edge_sets = {
        "endorserank_raw": er_raw,
        "endorserank_count": build_endorserank_edges(latest_t1.assign(value=1.0)),
        "endorserank_unit": build_endorserank_edges(
            latest_t1[["owner", "spender"]].drop_duplicates().assign(value=1.0)
        ),
        "awp_raw": awp_raw,
        "awp_count": build_weighted_edges(counted, "from_address", "to_address", "decay"),
        "awp_unit": build_weighted_edges(
            counted.drop_duplicates(["from_address", "to_address"]), "from_address", "to_address", "one"
        ),
    }
    frame = pd.DataFrame({"wallet": wallets})
    for method, edges in edge_sets.items():
        frame[f"{method}_score"] = _score_on(edges, wallets, params)
    for method, mapping in t1_baselines(latest_t1, transfers_t1, wallets).items():
        frame[f"{method}_score"] = frame["wallet"].map(mapping)
    labels = future_approval_labels(approvals, latest_t1, outcome_start, outcome_end, wallets)
    flow = future_transfer_labels(transfers, transfers_t1, outcome_start, outcome_end, wallets)
    merged = frame.merge(labels[["wallet", "future_new_approvers"]], on="wallet").merge(flow, on="wallet")

    def _taus(df: pd.DataFrame, methods: tuple[str, ...]) -> dict[str, dict[str, Any]]:
        return {
            m: {
                lab: bootstrap_kendall(df[f"{m}_score"], df[lab], n_resamples=n_boot, seed=seed)
                for lab in HOLDOUT_LABELS
            }
            for m in methods
        }

    receiving = merged[merged["t1_in_degree_score"] > 0]
    awp_zero = merged["awp_raw_score"] == 0
    er = merged["endorserank_raw_score"]
    return {
        "n_spenders": len(merged),
        "composition": {
            "awp_zero": int(awp_zero.sum()),
            "t1_in_degree_zero": int((merged["t1_in_degree_score"] == 0).sum()),
            "endorserank_at_minimum": int((er == er[er > 0].min()).sum()),
            "new_approver_share": {
                "awp_zero": float((merged.loc[awp_zero, "future_new_approvers"] > 0).mean()),
                "awp_positive": float((merged.loc[~awp_zero, "future_new_approvers"] > 0).mean()),
            },
            "new_sender_share": {
                "awp_zero": float((merged.loc[awp_zero, "future_new_transfer_senders"] > 0).mean()),
                "awp_positive": float((merged.loc[~awp_zero, "future_new_transfer_senders"] > 0).mean()),
            },
        },
        "tau": _taus(merged, WEIGHTING_METHODS),
        "tau_diff": holdout_tau_diff(merged, WEIGHTING_CONTRASTS, n_resamples=n_boot, seed=seed),
        "receiving": {
            "definition": "spenders with at least one sender other than themselves before the freeze",
            "n": len(receiving),
            "tau": _taus(receiving, ("endorserank_raw", "awp_raw", "awp_count", "t1_in_degree")),
            "tau_diff": holdout_tau_diff(receiving, RECEIVING_CONTRASTS, n_resamples=n_boot, seed=seed),
        },
    }


def trader_counts(
    config: dict[str, Any],
    rankings: pd.DataFrame,
    decoded: pd.DataFrame,
    latest_t1: pd.DataFrame,
    transfers_t1: pd.DataFrame,
) -> dict[str, Any]:
    """Spring prevalence of liquidations among the matched wallets that close at least three times."""
    rep = config["reputation"]
    score_end, outcome_start, outcome_end = holdout_bounds(config)
    min_closes = int(rep["holdout"].get("min_closes", 3))
    nodes = t1_connected_wallets(
        build_endorserank_edges(latest_t1),
        build_awp_edges(transfers_t1, score_end, float(rep["awp_decay_k"]), float(rep["awp_decay_t0_days"])),
    )
    matched = rankings["wallet"].tolist()
    in_graph = set(resolve_score_wallets(matched, nodes))
    work = decoded.copy()
    work["block_timestamp"] = pd.to_datetime(work["block_timestamp"], utc=True)
    work["account"] = work["account"].astype(str).str.lower()
    window = work[(work["block_timestamp"] >= outcome_start) & (work["block_timestamp"] <= outcome_end)]
    per_wallet = window.groupby("account").agg(
        closes=("is_liquidation", "size"), liquidations=("is_liquidation", "sum")
    )
    active = per_wallet[per_wallet["closes"] >= min_closes]
    out: dict[str, Any] = {"window": [str(outcome_start), str(outcome_end)], "min_closes": min_closes}
    for name, population in (("matched", set(matched)), ("matched_in_freeze_graph", in_graph)):
        rows = active[active.index.isin(population)]
        out[name] = {
            "wallets": len(population),
            "with_min_closes": len(rows),
            "with_a_liquidation": int((rows["liquidations"] > 0).sum()),
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument("--bootstrap", type=int, default=None, help="override the resample count")
    args = parser.parse_args()

    config = load_config()
    align_cfg = config.get("alignment") or {}
    n_boot = int(args.bootstrap or align_cfg.get("bootstrap_resamples", 400))
    seed = int(align_cfg.get("bootstrap_seed", 42))
    rep_paths = tier2_reputation_paths(config)

    rankings = pd.read_parquet(config["paths"]["wallet_rankings"])
    rankings["wallet"] = rankings["wallet"].astype(str).str.lower()
    decoded = pd.read_parquet(config["paths"]["decoded_events"])
    allowances = pd.read_parquet(rep_paths["latest_allowances"])
    transfers = pd.read_parquet(rep_paths["transfer_events"])

    print("Tie sensitivity (matched cohort)...")
    proxies = compute_all_proxies(
        transfers, allowances, decoded, rankings["wallet"].tolist(), min_closes=int(config["ranking"]["min_closes"])
    )
    ties = tie_sensitivity(config, rankings, allowances, transfers, proxies, n_boot, seed)
    del transfers

    print("Loading raw approval and transfer events for the spring holdout...")
    raw_approvals = load_approval_events(config)
    raw_transfers = load_transfer_events(config)
    score_end, _, _ = holdout_bounds(config)
    latest_t1 = latest_positive_as_of(raw_approvals, score_end)
    transfers_t1 = filter_transfers_as_of(raw_transfers, score_end)
    print("Holdout weighting (spender cohort)...")
    weighting = holdout_weighting(config, raw_approvals, raw_transfers, latest_t1, transfers_t1, n_boot, seed)
    print("Trader counts...")
    traders = trader_counts(config, rankings, decoded, latest_t1, transfers_t1)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Post hoc checks; none was fixed before the spring results were seen.",
        "bootstrap": {"n_boot": n_boot, "seed": seed, "ci_level": 0.95},
        "tie_sensitivity": ties,
        "holdout_weighting": weighting,
        "trader_counts": traders,
    }
    save_json(args.out, summary)

    for rule in ("zero_rule", "isolated_nodes"):
        fam = ties[rule]["family_ci"]
        inter = ties[rule]["inter_method_ci"]
        print(
            f"  {rule:15s} ER transfer {fam['endorserank']['transfer']['mean_tau']:+.3f} "
            f"allowance {fam['endorserank']['allowance']['mean_tau']:+.3f} | "
            f"AWP transfer {fam['awp']['transfer']['mean_tau']:+.3f} | ER-AWP {inter['kendall_tau']:+.3f}"
        )
    for method in WEIGHTING_METHODS:
        row = weighting["tau"][method]
        print(
            f"  {method:22s} new approvers {row['future_new_approvers']['kendall_tau']:+.3f} "
            f"new senders {row['future_new_transfer_senders']['kendall_tau']:+.3f}"
        )
    print(f"  traders: {traders}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
