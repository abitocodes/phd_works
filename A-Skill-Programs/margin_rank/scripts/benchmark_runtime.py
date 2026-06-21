"""Benchmark EndorseRank vs AWP runtime, memory, and PageRank iterations."""

from __future__ import annotations

import time
import tracemalloc
from statistics import mean
from typing import Any

import pandas as pd

from pagerank import (
    build_awp_edges,
    build_endorserank_edges,
    filter_subgraph_edges,
    weighted_pagerank,
)


def _run_timed(
    edges: pd.DataFrame,
    damping: float,
    tol: float,
    max_iter: int,
    repeats: int = 5,
) -> dict[str, Any]:
    runtimes: list[float] = []
    iterations: list[int] = []
    peak_mb = 0.0

    for _ in range(repeats):
        tracemalloc.start()
        t0 = time.perf_counter()
        _, iters = weighted_pagerank(
            edges,
            damping=damping,
            tol=tol,
            max_iter=max_iter,
            return_iterations=True,
        )
        elapsed = time.perf_counter() - t0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        runtimes.append(elapsed)
        iterations.append(iters)
        peak_mb = max(peak_mb, peak / (1024 * 1024))

    return {
        "runtime_sec_mean": round(mean(runtimes), 3),
        "runtime_sec_std": round(float(pd.Series(runtimes).std(ddof=0) or 0), 3),
        "iterations_mean": round(mean(iterations), 1),
        "peak_memory_mb": round(peak_mb, 2),
        "edge_count": len(edges),
        "node_count": len(set(edges["from_node"]) | set(edges["to_node"])) if not edges.empty else 0,
        "repeats": repeats,
    }


def benchmark_reputation(
    wallets: list[str],
    allowances: pd.DataFrame,
    transfers: pd.DataFrame,
    config: dict,
    repeats: int = 5,
) -> dict[str, Any]:
    rep = config["reputation"]
    seed = set(w.lower() for w in wallets)
    observation_end = pd.Timestamp(rep["observation_end"], tz="UTC")

    endorse_edges = filter_subgraph_edges(build_endorserank_edges(allowances), seed)
    awp_edges = filter_subgraph_edges(
        build_awp_edges(
            transfers,
            observation_end=observation_end,
            k=float(rep["awp_decay_k"]),
            t0_days=float(rep["awp_decay_t0_days"]),
        ),
        seed,
    )

    damping = float(rep["damping"])
    tol = float(rep["pagerank_tolerance"])
    max_iter = int(rep["max_iterations"])

    return {
        "endorserank": _run_timed(endorse_edges, damping, tol, max_iter, repeats),
        "awp": _run_timed(awp_edges, damping, tol, max_iter, repeats),
        "n_wallets": len(wallets),
    }
