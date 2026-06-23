"""Weighted PageRank on sparse directed graphs."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse


def build_weighted_edges(
    df: pd.DataFrame,
    from_col: str,
    to_col: str,
    weight_col: str,
) -> pd.DataFrame:
    """Aggregate duplicate edges by summing weights."""
    work = df[[from_col, to_col, weight_col]].copy()
    work = work[work[weight_col] > 0]
    return (
        work.groupby([from_col, to_col], as_index=False)[weight_col]
        .sum()
        .rename(columns={from_col: "from_node", to_col: "to_node", weight_col: "weight"})
    )


def filter_subgraph_edges(
    edges: pd.DataFrame,
    seed_wallets: set[str],
) -> pd.DataFrame:
    """Keep edges touching at least one seed wallet (includes 1-hop neighbors)."""
    mask = edges["from_node"].isin(seed_wallets) | edges["to_node"].isin(seed_wallets)
    return edges[mask].copy()


def weighted_pagerank(
    edges: pd.DataFrame,
    damping: float = 0.85,
    tol: float = 1e-8,
    max_iter: int = 100,
    return_iterations: bool = False,
) -> dict[str, float] | tuple[dict[str, float], int]:
    """
    Run weighted PageRank on edge list with columns: from_node, to_node, weight.

    Returns mapping node -> score (sums to 1 over reachable nodes).
    """
    if edges.empty:
        if return_iterations:
            return {}, 0
        return {}

    nodes = sorted(set(edges["from_node"]) | set(edges["to_node"]))
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)

    row: list[int] = []
    col: list[int] = []
    data: list[float] = []
    out_strength = np.zeros(n, dtype=np.float64)

    for _, r in edges.iterrows():
        u = idx[r["from_node"]]
        v = idx[r["to_node"]]
        w = float(r["weight"])
        if w <= 0:
            continue
        row.append(u)
        col.append(v)
        data.append(w)
        out_strength[u] += w

    adj = sparse.csr_matrix((data, (row, col)), shape=(n, n))

    # Transition matrix: P[u,v] = w[u,v] / sum_out(u); dangling -> uniform
    inv_out = np.zeros(n, dtype=np.float64)
    nonzero_out = out_strength > 0
    inv_out[nonzero_out] = 1.0 / out_strength[nonzero_out]

    diag = sparse.diags(inv_out, format="csr")
    transition = diag @ adj

    dangling = ~nonzero_out
    rank = np.full(n, 1.0 / n, dtype=np.float64)
    teleport = np.full(n, 1.0 / n, dtype=np.float64)

    iterations = 0
    for i in range(max_iter):
        iterations = i + 1
        dangling_contrib = rank[dangling].sum() * teleport
        new_rank = (1.0 - damping) * teleport + damping * (transition.T @ rank)
        new_rank = new_rank + damping * dangling_contrib
        if np.abs(new_rank - rank).sum() < tol:
            rank = new_rank
            break
        rank = new_rank

    total = rank.sum()
    if total > 0:
        rank = rank / total

    scores = {nodes[i]: float(rank[i]) for i in range(n)}
    if return_iterations:
        return scores, iterations
    return scores


def assign_dense_ranks(
    wallets: list[str],
    scores: dict[str, float],
) -> pd.DataFrame:
    """Rank wallets by score descending (1 = highest)."""
    rows = [{"wallet": w, "score": scores.get(w, 0.0)} for w in wallets]
    df = pd.DataFrame(rows)
    df = df.sort_values(["score", "wallet"], ascending=[False, True]).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    return df


def logistic_time_decay(
    delta_days: pd.Series,
    k: float,
    t0: float,
) -> pd.Series:
    """sigma(dt) = 1 / (1 + exp(k * (dt - t0)))."""
    return 1.0 / (1.0 + np.exp(k * (delta_days - t0)))


def build_awp_edges(
    transfers: pd.DataFrame,
    observation_end: pd.Timestamp,
    k: float,
    t0_days: float,
) -> pd.DataFrame:
    """Aggregate time-decayed transfer weights into directed edges."""
    work = transfers.copy()
    work["block_timestamp"] = pd.to_datetime(work["block_timestamp"], utc=True)
    delta = (observation_end - work["block_timestamp"]).dt.total_seconds() / 86400.0
    work["decay"] = logistic_time_decay(delta, k, t0_days)
    work["weighted_value"] = work["value"].astype(float) * work["decay"]
    return build_weighted_edges(work, "from_address", "to_address", "weighted_value")


def build_endorserank_edges(allowances: pd.DataFrame) -> pd.DataFrame:
    """Sum latest allowance amounts per owner -> spender across tokens."""
    agg = (
        allowances.groupby(["owner", "spender"], as_index=False)["value"]
        .sum()
        .rename(columns={"owner": "from_node", "spender": "to_node", "value": "weight"})
    )
    return agg
