"""Benchmark PageRank runtime, memory, and iterations for all seven methods."""

from __future__ import annotations

import hashlib
import time
import tracemalloc
from statistics import mean
from typing import Any

import pandas as pd

from pagerank_variants import SIX_AAVE_METHOD_IDS, collect_method_edges, collect_six_aave_edges


def subsample_wallets_deterministic(
    wallets: list[str],
    n: int,
    seed: str = "benchmark-scale-v1",
) -> list[str]:
    """Return n wallets via SHA256(seed:address) ordering for reproducible scaling runs."""
    unique = sorted({w.lower() for w in wallets})
    if n >= len(unique):
        return unique
    keyed = sorted(
        unique,
        key=lambda w: hashlib.sha256(f"{seed}:{w}".encode()).hexdigest(),
    )
    return keyed[:n]


def scaling_stages_for_cohort(wallets: list[str], config: dict) -> list[int]:
    """Configured in-cohort stages plus full cohort size, capped at len(wallets)."""
    bench = config.get("benchmark") or {}
    configured = [int(s) for s in bench.get("scaling_stages", [1000, 2000, 4000])]
    full = len(wallets)
    stages = sorted({s for s in configured if 0 < s <= full})
    if full not in stages:
        stages.append(full)
    return stages


def _run_timed(
    edges: pd.DataFrame,
    damping: float,
    tol: float,
    max_iter: int,
    repeats: int = 5,
) -> dict[str, Any]:
    from pagerank import weighted_pagerank

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


def benchmark_er_awp_pair(
    wallets: list[str],
    allowances: pd.DataFrame,
    transfers: pd.DataFrame,
    config: dict,
    repeats: int = 5,
    decoded: pd.DataFrame | None = None,
    aave_events: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Time EndorseRank and AWP PageRank on pre-built edge lists (same path as full benchmark)."""
    rep = config["reputation"]
    damping = float(rep["damping"])
    tol = float(rep["pagerank_tolerance"])
    max_iter = int(rep["max_iterations"])

    if decoded is not None:
        edge_map = collect_method_edges(
            wallets, config, allowances, transfers, decoded, aave_events
        )
        er_edges = edge_map["endorserank"]
        awp_edges = edge_map["awp"]
    else:
        from pagerank import build_awp_edges, build_endorserank_edges, filter_subgraph_edges

        seed = set(w.lower() for w in wallets)
        observation_end = pd.Timestamp(rep["observation_end"], tz="UTC")
        er_edges = filter_subgraph_edges(build_endorserank_edges(allowances), seed)
        awp_edges = filter_subgraph_edges(
            build_awp_edges(
                transfers,
                observation_end=observation_end,
                k=float(rep["awp_decay_k"]),
                t0_days=float(rep["awp_decay_t0_days"]),
            ),
            seed,
        )

    return {
        "endorserank": _run_timed(er_edges, damping, tol, max_iter, repeats),
        "awp": _run_timed(awp_edges, damping, tol, max_iter, repeats),
        "n_wallets": len(wallets),
    }


def benchmark_all_methods(
    wallets: list[str],
    allowances: pd.DataFrame,
    transfers: pd.DataFrame,
    decoded: pd.DataFrame,
    aave_events: pd.DataFrame | None,
    config: dict,
    repeats: int = 5,
) -> dict[str, Any]:
    """Time weighted PageRank on each method's filtered edge list."""
    rep = config["reputation"]
    damping = float(rep["damping"])
    tol = float(rep["pagerank_tolerance"])
    max_iter = int(rep["max_iterations"])

    edge_map = collect_method_edges(
        wallets, config, allowances, transfers, decoded, aave_events
    )

    results: dict[str, Any] = {"n_wallets": len(wallets)}
    for method_id, edges in edge_map.items():
        results[method_id] = _run_timed(edges, damping, tol, max_iter, repeats)

    return results


def benchmark_six_aave_methods(
    wallets: list[str],
    allowances: pd.DataFrame,
    transfers: pd.DataFrame,
    aave_events: pd.DataFrame | None,
    delegation_events: pd.DataFrame | None,
    config: dict,
    repeats: int = 5,
) -> dict[str, Any]:
    """Time PageRank for six-Aave preset methods."""
    rep = config["reputation"]
    damping = float(rep["damping"])
    tol = float(rep["pagerank_tolerance"])
    max_iter = int(rep["max_iterations"])

    edge_map = collect_six_aave_edges(
        wallets, config, allowances, transfers, aave_events, delegation_events
    )

    results: dict[str, Any] = {"n_wallets": len(wallets)}
    for method_id in SIX_AAVE_METHOD_IDS:
        edges = edge_map.get(method_id, pd.DataFrame())
        results[method_id] = _run_timed(edges, damping, tol, max_iter, repeats)
    return results


def benchmark_reputation(
    wallets: list[str],
    allowances: pd.DataFrame,
    transfers: pd.DataFrame,
    config: dict,
    repeats: int = 5,
    decoded: pd.DataFrame | None = None,
    aave_events: pd.DataFrame | None = None,
    delegation_events: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Backward-compatible wrapper; benchmarks all methods when decoded is provided."""
    if decoded is not None:
        results = benchmark_all_methods(
            wallets, allowances, transfers, decoded, aave_events, config, repeats
        )
        six_bench = benchmark_six_aave_methods(
            wallets, allowances, transfers, aave_events, delegation_events, config, repeats
        )
        results["six_aave"] = six_bench
        for method_id in SIX_AAVE_METHOD_IDS:
            if method_id in six_bench:
                results[method_id] = six_bench[method_id]
        return results

    return benchmark_er_awp_pair(
        wallets, allowances, transfers, config, repeats=repeats, decoded=None
    )


def benchmark_scaling(
    wallets: list[str],
    allowances: pd.DataFrame,
    transfers: pd.DataFrame,
    config: dict,
    repeats: int = 5,
    decoded: pd.DataFrame | None = None,
    aave_events: pd.DataFrame | None = None,
    authoritative_full_cohort: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Benchmark EndorseRank vs AWP at deterministic in-cohort subsample sizes."""
    bench = config.get("benchmark") or {}
    scaling_seed = str(bench.get("scaling_seed", "benchmark-scale-v1"))
    stages = scaling_stages_for_cohort(wallets, config)
    full_n = len(wallets)

    rows: list[dict[str, Any]] = []
    for n in stages:
        subset = subsample_wallets_deterministic(wallets, n, seed=scaling_seed)
        if (
            authoritative_full_cohort is not None
            and len(subset) == full_n
            and n == full_n
        ):
            er = authoritative_full_cohort["endorserank"]
            awp = authoritative_full_cohort["awp"]
        else:
            pair = benchmark_er_awp_pair(
                subset,
                allowances,
                transfers,
                config,
                repeats=repeats,
                decoded=decoded,
                aave_events=aave_events,
            )
            er = pair["endorserank"]
            awp = pair["awp"]

        er_speedup_ratio = (
            round(awp["runtime_sec_mean"] / er["runtime_sec_mean"], 2)
            if er["runtime_sec_mean"] > 0
            else None
        )
        rows.append(
            {
                "n_wallets": len(subset),
                "scaling_seed": scaling_seed,
                "endorserank": er,
                "awp": awp,
                "er_speedup_ratio": er_speedup_ratio,
                "speedup_awp_over_er": er_speedup_ratio,
            }
        )

    return {
        "scaling_seed": scaling_seed,
        "stages": stages,
        "rows": rows,
        "repeats": repeats,
    }


def tier2_stages_for_pool(pool_size: int, config: dict) -> list[int]:
    """Configured Tier-2 benchmark stages capped at wallet pool size."""
    bench = config.get("benchmark") or {}
    configured = [int(s) for s in bench.get("stages", [10000, 50000, 100000])]
    stages = sorted({s for s in configured if 0 < s <= pool_size})
    if pool_size not in stages and pool_size > 0:
        stages.append(pool_size)
    return stages


def benchmark_tier2_scaling(
    wallet_pool: list[str],
    allowances: pd.DataFrame,
    transfers: pd.DataFrame,
    config: dict,
    repeats: int = 5,
) -> dict[str, Any]:
    """Benchmark EndorseRank vs AWP at Tier-2 stages (10k/50k/100k) from wallet pool."""
    bench = config.get("benchmark") or {}
    scaling_seed = str(bench.get("tier2_scaling_seed", "benchmark-tier2-v1"))
    stages = tier2_stages_for_pool(len(wallet_pool), config)

    rows: list[dict[str, Any]] = []
    for n in stages:
        subset = subsample_wallets_deterministic(wallet_pool, n, seed=scaling_seed)
        pair = benchmark_er_awp_pair(
            subset,
            allowances,
            transfers,
            config,
            repeats=repeats,
        )
        er = pair["endorserank"]
        awp = pair["awp"]
        er_speedup_ratio = (
            round(awp["runtime_sec_mean"] / er["runtime_sec_mean"], 2)
            if er["runtime_sec_mean"] > 0
            else None
        )
        rows.append(
            {
                "n_wallets": len(subset),
                "scaling_seed": scaling_seed,
                "endorserank": er,
                "awp": awp,
                "er_speedup_ratio": er_speedup_ratio,
                "speedup_awp_over_er": er_speedup_ratio,
            }
        )

    return {
        "scaling_seed": scaling_seed,
        "wallet_pool_size": len(wallet_pool),
        "stages": stages,
        "rows": rows,
        "repeats": repeats,
        "tier": 2,
    }
