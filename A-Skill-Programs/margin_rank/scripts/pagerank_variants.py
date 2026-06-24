"""PageRank variants: GF-PR, LP-PR, CW-AWP, LF-PR, RiskProp."""

from __future__ import annotations

from typing import Any

import pandas as pd

from pagerank import (
    build_awp_edges,
    build_endorserank_edges,
    build_weighted_edges,
    filter_subgraph_edges,
    weighted_pagerank,
)

GMX_POOL_NODE = "__gmx_profit_pool__"
GMX_SINK_NODE = "__gmx_loss_sink__"


def _wallet_liquidation_rates(decoded: pd.DataFrame, wallets: list[str]) -> dict[str, float]:
    work = decoded.copy()
    work["wallet"] = work["account"].astype(str).str.lower()
    wallet_set = {w.lower() for w in wallets}
    work = work[work["wallet"].isin(wallet_set)]
    if work.empty:
        return {w.lower(): 0.0 for w in wallets}

    agg = work.groupby("wallet", as_index=False).agg(
        total=("wallet", "count"),
        liq=("is_liquidation", "sum"),
    )
    agg["liq_rate"] = agg["liq"] / agg["total"].clip(lower=1)
    rates = dict(zip(agg["wallet"], agg["liq_rate"]))
    return {w.lower(): float(rates.get(w.lower(), 0.0)) for w in wallets}


def build_gf_pr_edges(decoded: pd.DataFrame, wallets: list[str]) -> pd.DataFrame:
    """ProfitFlow star graph: POOL -> wallet (gains), wallet -> SINK (losses/liquidations)."""
    work = decoded.copy()
    work["wallet"] = work["account"].astype(str).str.lower()
    work["base_pnl_usd"] = pd.to_numeric(work["base_pnl_usd"], errors="coerce").fillna(0)
    work["is_liquidation"] = work["is_liquidation"].fillna(False).astype(bool)
    wallet_set = {w.lower() for w in wallets}
    work = work[work["wallet"].isin(wallet_set)]

    pool_to: dict[str, float] = {}
    to_sink: dict[str, float] = {}

    for _, row in work.iterrows():
        w = row["wallet"]
        pnl = float(row["base_pnl_usd"])
        if row["is_liquidation"]:
            to_sink[w] = to_sink.get(w, 0.0) + abs(pnl) + 1.0
        elif pnl > 0:
            pool_to[w] = pool_to.get(w, 0.0) + pnl
        elif pnl < 0:
            to_sink[w] = to_sink.get(w, 0.0) + abs(pnl) + 0.1

    rows: list[dict[str, Any]] = []
    for w, wt in pool_to.items():
        if wt > 0:
            rows.append({"from_node": GMX_POOL_NODE, "to_node": w, "weight": wt})
    for w, wt in to_sink.items():
        if wt > 0:
            rows.append({"from_node": w, "to_node": GMX_SINK_NODE, "weight": wt})

    if not rows:
        return pd.DataFrame(columns=["from_node", "to_node", "weight"])
    return pd.DataFrame(rows)


def build_lp_pr_edges(
    transfers: pd.DataFrame,
    decoded: pd.DataFrame,
    wallets: list[str],
    observation_end: pd.Timestamp,
    k: float,
    t0_days: float,
) -> pd.DataFrame:
    """AWP transfer edges penalized by endpoint liquidation rates."""
    base = build_awp_edges(transfers, observation_end, k, t0_days)
    if base.empty:
        return base

    liq_rate = _wallet_liquidation_rates(decoded, wallets)
    work = base.copy()
    work["weight"] = work.apply(
        lambda r: float(r["weight"])
        * (1.0 - liq_rate.get(str(r["from_node"]).lower(), 0.0))
        * (1.0 - liq_rate.get(str(r["to_node"]).lower(), 0.0)),
        axis=1,
    )
    return work[work["weight"] > 0]


def build_cw_awp_edges(
    transfers: pd.DataFrame,
    token_allowlist: list[str],
    observation_end: pd.Timestamp,
    k: float,
    t0_days: float,
) -> pd.DataFrame:
    """AWP on collateral-token transfers only."""
    allow = {t.lower() for t in token_allowlist}
    work = transfers.copy()
    work["token_address"] = work["token_address"].astype(str).str.lower()
    filtered = work[work["token_address"].isin(allow)]
    return build_awp_edges(filtered, observation_end, k, t0_days)


def build_riskprop_edges(
    transfers: pd.DataFrame,
    decoded: pd.DataFrame,
    wallets: list[str],
    observation_end: pd.Timestamp,
    k: float,
    t0_days: float,
) -> pd.DataFrame:
    """AWP edges scaled by (1 - risk(from)) where risk = liquidation rate."""
    base = build_awp_edges(transfers, observation_end, k, t0_days)
    if base.empty:
        return base

    risk = _wallet_liquidation_rates(decoded, wallets)
    work = base.copy()
    work["weight"] = work.apply(
        lambda r: float(r["weight"]) * (1.0 - risk.get(str(r["from_node"]).lower(), 0.0)),
        axis=1,
    )
    return work[work["weight"] > 0]


def build_lf_pr_edges(
    aave_events: pd.DataFrame,
    observation_end: pd.Timestamp,
    k: float,
    t0_days: float,
) -> pd.DataFrame:
    """Time-decayed user <-> pool edges from Aave lending events."""
    if aave_events.empty:
        return pd.DataFrame(columns=["from_node", "to_node", "weight"])

    from pagerank import logistic_time_decay

    work = aave_events.copy()
    work["user"] = work["user"].astype(str).str.lower()
    work["pool"] = work["pool"].astype(str).str.lower()
    work["amount"] = work["amount"].astype(float)
    work["block_timestamp"] = pd.to_datetime(work["block_timestamp"], utc=True)
    work = work[work["amount"] > 0]

    delta = (observation_end - work["block_timestamp"]).dt.total_seconds() / 86400.0
    work["decay"] = logistic_time_decay(delta, k, t0_days)
    work["weighted"] = work["amount"] * work["decay"]

    rows: list[dict[str, Any]] = []
    for _, row in work.iterrows():
        user, pool = row["user"], row["pool"]
        w = float(row["weighted"])
        et = str(row.get("event_type", "")).lower()
        if et == "borrow":
            rows.append({"from_node": pool, "to_node": user, "weight": w})
        elif et in ("repay", "liquidation_call", "liquidation"):
            rows.append({"from_node": user, "to_node": pool, "weight": w})
        else:
            rows.append({"from_node": user, "to_node": pool, "weight": w * 0.5})
            rows.append({"from_node": pool, "to_node": user, "weight": w * 0.5})

    if not rows:
        return pd.DataFrame(columns=["from_node", "to_node", "weight"])
    df = pd.DataFrame(rows)
    return build_weighted_edges(df, "from_node", "to_node", "weight")


def collect_method_edges(
    wallets: list[str],
    config: dict[str, Any],
    allowances: pd.DataFrame,
    transfers: pd.DataFrame,
    decoded: pd.DataFrame,
    aave_events: pd.DataFrame | None,
) -> dict[str, pd.DataFrame]:
    """Filtered edge lists per method (for PageRank runtime benchmarking)."""
    rep = config["reputation"]
    seed = set(w.lower() for w in wallets)
    observation_end = pd.Timestamp(rep["observation_end"], tz="UTC")
    k = float(rep["awp_decay_k"])
    t0 = float(rep["awp_decay_t0_days"])
    methods_cfg = config.get("methods", {})
    collateral = config.get("collateral_tokens", [])

    edges: dict[str, pd.DataFrame] = {}

    edges["endorserank"] = filter_subgraph_edges(build_endorserank_edges(allowances), seed)

    awp_edge_df = build_awp_edges(transfers, observation_end, k, t0)
    edges["awp"] = filter_subgraph_edges(awp_edge_df, seed)

    if methods_cfg.get("gf_pr", {}).get("enabled", True):
        gf_edges = build_gf_pr_edges(decoded, wallets)
        edges["gf_pr"] = filter_subgraph_edges(
            gf_edges, seed | {GMX_POOL_NODE, GMX_SINK_NODE}
        )

    if methods_cfg.get("lp_pr", {}).get("enabled", True):
        lp_edges = build_lp_pr_edges(transfers, decoded, wallets, observation_end, k, t0)
        edges["lp_pr"] = filter_subgraph_edges(lp_edges, seed)

    if methods_cfg.get("cw_awp", {}).get("enabled", True) and collateral:
        cw_edges = build_cw_awp_edges(transfers, collateral, observation_end, k, t0)
        edges["cw_awp"] = filter_subgraph_edges(cw_edges, seed)

    if methods_cfg.get("riskprop_pr", {}).get("enabled", True):
        rp_edges = build_riskprop_edges(transfers, decoded, wallets, observation_end, k, t0)
        edges["riskprop_pr"] = filter_subgraph_edges(rp_edges, seed)

    if methods_cfg.get("lf_pr", {}).get("enabled", True):
        if aave_events is not None and not aave_events.empty:
            lf_edges = build_lf_pr_edges(aave_events, observation_end, k, t0)
            edges["lf_pr"] = filter_subgraph_edges(lf_edges, seed)
        else:
            edges["lf_pr"] = pd.DataFrame(columns=["from_node", "to_node", "weight"])

    return edges


def _run_pagerank_on_edges(
    edges: pd.DataFrame,
    wallets: list[str],
    seed: set[str],
    rep: dict[str, Any],
) -> tuple[dict[str, float], int]:
    if edges.empty:
        return {w: 0.0 for w in wallets}, 0

    filtered = filter_subgraph_edges(edges, seed)
    scores = weighted_pagerank(
        filtered,
        damping=float(rep["damping"]),
        tol=float(rep["pagerank_tolerance"]),
        max_iter=int(rep["max_iterations"]),
    )
    return {w: scores.get(w, 0.0) for w in wallets}, len(filtered)


def compute_variant_scores(
    wallets: list[str],
    config: dict[str, Any],
    allowances: pd.DataFrame,
    transfers: pd.DataFrame,
    decoded: pd.DataFrame,
    aave_events: pd.DataFrame | None,
) -> tuple[dict[str, dict[str, float]], dict[str, int]]:
    """Compute all seven method scores and edge counts."""
    rep = config["reputation"]
    seed = set(w.lower() for w in wallets)
    observation_end = pd.Timestamp(rep["observation_end"], tz="UTC")
    k = float(rep["awp_decay_k"])
    t0 = float(rep["awp_decay_t0_days"])

    methods_cfg = config.get("methods", {})
    collateral = config.get("collateral_tokens", [])

    scores: dict[str, dict[str, float]] = {}
    edge_counts: dict[str, int] = {}

    # EndorseRank
    er_edges = filter_subgraph_edges(build_endorserank_edges(allowances), seed)
    scores["endorserank"], edge_counts["endorserank"] = _run_pagerank_on_edges(
        er_edges, wallets, seed, rep
    )

    # AWP
    awp_edges = build_awp_edges(transfers, observation_end, k, t0)
    scores["awp"], edge_counts["awp"] = _run_pagerank_on_edges(awp_edges, wallets, seed, rep)

    if methods_cfg.get("gf_pr", {}).get("enabled", True):
        gf_edges = build_gf_pr_edges(decoded, wallets)
        scores["gf_pr"], edge_counts["gf_pr"] = _run_pagerank_on_edges(
            gf_edges, wallets, seed | {GMX_POOL_NODE, GMX_SINK_NODE}, rep
        )

    if methods_cfg.get("lp_pr", {}).get("enabled", True):
        lp_edges = build_lp_pr_edges(transfers, decoded, wallets, observation_end, k, t0)
        scores["lp_pr"], edge_counts["lp_pr"] = _run_pagerank_on_edges(
            lp_edges, wallets, seed, rep
        )

    if methods_cfg.get("cw_awp", {}).get("enabled", True) and collateral:
        cw_edges = build_cw_awp_edges(transfers, collateral, observation_end, k, t0)
        scores["cw_awp"], edge_counts["cw_awp"] = _run_pagerank_on_edges(
            cw_edges, wallets, seed, rep
        )

    if methods_cfg.get("riskprop_pr", {}).get("enabled", True):
        rp_edges = build_riskprop_edges(transfers, decoded, wallets, observation_end, k, t0)
        scores["riskprop_pr"], edge_counts["riskprop_pr"] = _run_pagerank_on_edges(
            rp_edges, wallets, seed, rep
        )

    if methods_cfg.get("lf_pr", {}).get("enabled", True):
        if aave_events is not None and not aave_events.empty:
            lf_edges = build_lf_pr_edges(aave_events, observation_end, k, t0)
            scores["lf_pr"], edge_counts["lf_pr"] = _run_pagerank_on_edges(
                lf_edges, wallets, seed, rep
            )
        else:
            scores["lf_pr"] = {w: 0.0 for w in wallets}
            edge_counts["lf_pr"] = 0

    return scores, edge_counts
