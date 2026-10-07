#!/usr/bin/env python3
"""Synthetic illustration of how Sybil attacks move a target contract's rank.

Section 5 of the manuscript makes three claims:

1. On a wallet-contract graph with a uniform restart, PageRank gives every
   wallet the same mass, so each added wallet lifts the contract it authorizes
   by the same amount whatever value it puts at risk (Proposition 1).
2. When the restart is weighted by fees paid, splitting a fee budget across
   many wallets gains nothing (Proposition 2).
3. Contracts with no restart mass and no edges from honest contracts collect
   no score (Proposition 3). Runtime trait bindings would hand an attacker
   such edges for the price of a call, so they are not edges.

This script builds a small made-up graph with honest contracts and wallets,
adds an attacker's target token, and measures how much the attacker must pay
(in units of the minimum call fee) to lift the target into the top three
under each scoring rule. The graph is synthetic. The output illustrates the
propositions; it says nothing about Stacks mainnet.

Attacks (numbered as in Section 7 of the manuscript, where A3 is a wash flow
that only AWP reacts to and is therefore left out here):
    A1  deploy k contracts that each reference the target (link farm)
    A2  create k wallets that each authorize the target once (wallet farm)
    A4  call the honest router k times with the target as the trait argument

Scoring rules:
    callers      number of distinct wallets that authorized the contract
    dep-pr       PageRank on contract references, uniform restart
    er-uniform   EndorseRank moved to Stacks: wallets and contracts as nodes,
                 latest authorized value on wallet edges, uniform restart
    pc-er        PC-EndorseRank: contracts only, restart weighted by fees
    pc-er+bind   pc-er plus run-time trait bindings as router edges (ablation);
                 the router's binding edges together get the same weight as its
                 static references, split by how often each token was bound

Ranks count only contracts with a strictly higher score, so ties go in the
target's favor and the reported costs can only be too low. The fee cap f_max
of the manuscript is left out.

Usage:
    python scripts/toy_sybil_example.py           # print tables
    python scripts/toy_sybil_example.py --latex   # also write the LaTeX tables
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

D = 0.85  # damping, as in AWP and EndorseRank
TOL = 1e-8  # l1 tolerance and iteration cap of Section 5.6
MAX_ITER = 300
SEED = 20261007
N_HONEST_WALLETS = 300
CALL_FEE = 1.0  # one call at the minimum fee is the unit of cost
DEPLOY_FEE = 10.0  # one small contract deployment
BETA_DEP = 1.0
BETA_DEL = 2.0
TOP = 3
K_CAP = 200_000  # largest attack size tried
GRID = (0, 10, 100, 1000)

TRAIT = "sip010-trait"
TOKENS = ["tok-a", "tok-b", "tok-c", "tok-d", "tok-e", "tok-f"]
POOLS = {"pool-ab": ("tok-a", "tok-b"), "pool-cd": ("tok-c", "tok-d"), "pool-ef": ("tok-e", "tok-f")}
TARGET = "x-token"
ENTRY_POINTS = ["router", "vault", "dao"] + TOKENS
ENTRY_PROBS = np.array([0.35, 0.20, 0.05] + [0.40 / len(TOKENS)] * len(TOKENS))

HERE = Path(__file__).resolve().parent
TABLE_DIR = HERE.parent / "manuscript" / "tables"


@dataclass
class World:
    contracts: list[str]
    dep: list[tuple[str, str]]
    dele: list[tuple[str, str]]
    # wallet -> {contract: latest authorized value}
    auth: dict[str, dict[str, float]]
    fees: dict[str, float]
    # runtime trait bindings observed on router calls: token -> count
    bindings: dict[str, float] = field(default_factory=dict)


def honest_world(rng: np.random.Generator) -> World:
    contracts = [TRAIT, *TOKENS, "math-lib", *POOLS, "router", "vault", "dao", TARGET]
    dep: list[tuple[str, str]] = [(t, TRAIT) for t in TOKENS]  # impl-trait
    dele: list[tuple[str, str]] = []
    for pool, (t1, t2) in POOLS.items():
        dep += [(pool, TRAIT), (pool, "math-lib")]  # use-trait, library call
        dele += [(pool, t1), (pool, t2)]  # pays out inside as-contract?
    dep += [("router", pool) for pool in POOLS] + [("router", TRAIT)]
    dele += [("vault", "tok-a"), ("vault", "tok-b")]
    dep += [("vault", "math-lib")]
    dele += [("dao", "vault"), ("dao", "router")]  # enabled extensions
    dep += [(TARGET, TRAIT)]  # the attacker's token implements SIP-010

    auth: dict[str, dict[str, float]] = {}
    fees: dict[str, float] = {}
    bindings = {t: 0.0 for t in TOKENS}
    pool_pairs = list(POOLS.values())
    for i in range(N_HONEST_WALLETS):
        w = f"w{i}"
        n = int(rng.integers(1, 4))
        chosen = rng.choice(len(ENTRY_POINTS), size=n, replace=False, p=ENTRY_PROBS)
        auth[w] = {ENTRY_POINTS[j]: float(rng.lognormal(math.log(200.0), 1.0)) for j in chosen}
        n_tx = 1 + int(rng.poisson(8))
        fees[w] = float(np.sum(CALL_FEE * rng.lognormal(math.log(3.0), 0.5, size=n_tx)))
        if "router" in auth[w]:
            for _ in range(int(rng.integers(1, 6))):
                t1, t2 = pool_pairs[int(rng.integers(len(pool_pairs)))]
                bindings[t1] += 1.0
                bindings[t2] += 1.0
    return World(contracts, dep, dele, auth, fees, bindings)


def attacked(base: World, attack: str, k: int) -> tuple[World, float]:
    """Return a copy of the world with the attack applied and its cost."""
    w = World(list(base.contracts), list(base.dep), list(base.dele),
              {u: dict(a) for u, a in base.auth.items()}, dict(base.fees), dict(base.bindings))
    cost = 0.0
    if k == 0:
        return w, cost
    if attack == "A1":
        for i in range(k):
            name = f"farm-{i}"
            w.contracts.append(name)
            w.dep.append((name, TARGET))
        cost = k * DEPLOY_FEE
    elif attack == "A2":
        for i in range(k):
            u = f"sybil-{i}"
            w.auth[u] = {TARGET: 1.0}
            w.fees[u] = CALL_FEE
        cost = k * CALL_FEE
    elif attack == "A4":
        u = "attacker"
        w.auth[u] = {"router": 1.0}
        w.fees[u] = k * CALL_FEE
        w.bindings[TARGET] = w.bindings.get(TARGET, 0.0) + k
        cost = k * CALL_FEE
    else:
        raise ValueError(attack)
    return w, cost


def pagerank(n: int, src: np.ndarray, dst: np.ndarray, wt: np.ndarray, restart: np.ndarray) -> np.ndarray:
    """Weighted PageRank; dangling mass returns to the restart distribution."""
    out = np.bincount(src, weights=wt, minlength=n)
    p = wt / out[src]
    dangling = out == 0
    r = restart.copy()
    for _ in range(MAX_ITER):
        new = (1 - D) * restart + D * np.bincount(dst, weights=r[src] * p, minlength=n)
        new += D * r[dangling].sum() * restart
        if np.abs(new - r).sum() < TOL:
            return new
        r = new
    return r


def contract_edges(w: World, beta_dep: float, beta_del: float, with_bindings: bool) -> dict[tuple[str, str], float]:
    edges: dict[tuple[str, str], float] = {}
    for a, b in w.dep:
        edges[(a, b)] = max(edges.get((a, b), 0.0), beta_dep)
    for a, b in w.dele:
        edges[(a, b)] = max(edges.get((a, b), 0.0), beta_del)
    if with_bindings:
        # Ablation: runtime bindings get the same total weight as the router's
        # static references, split by how often each token was bound.
        static = sum(v for (a, _), v in edges.items() if a == "router")
        total = sum(w.bindings.values())
        for tok, cnt in w.bindings.items():
            if cnt > 0:
                edges[("router", tok)] = edges.get(("router", tok), 0.0) + static * cnt / total
    return edges


def shares(auth: dict[str, float]) -> dict[str, float]:
    tot = sum(auth.values())
    if tot <= 0:
        return {c: 1.0 / len(auth) for c in auth}
    return {c: v / tot for c, v in auth.items()}


def score(w: World, method: str) -> dict[str, float]:
    if method == "callers":
        cnt = {c: 0.0 for c in w.contracts}
        for a in w.auth.values():
            for c in a:
                cnt[c] += 1.0
        return cnt

    if method == "dep-pr":
        idx = {c: i for i, c in enumerate(w.contracts)}
        e = contract_edges(w, 1.0, 1.0, with_bindings=False)
        src = np.array([idx[a] for a, _ in e], dtype=int)
        dst = np.array([idx[b] for _, b in e], dtype=int)
        wt = np.array(list(e.values()))
        n = len(idx)
        r = pagerank(n, src, dst, wt, np.full(n, 1.0 / n))
        return {c: r[i] for c, i in idx.items()}

    if method == "er-uniform":
        nodes = list(w.contracts) + list(w.auth)
        idx = {v: i for i, v in enumerate(nodes)}
        e = contract_edges(w, BETA_DEP, BETA_DEL, with_bindings=False)
        triples = [(idx[a], idx[b], v) for (a, b), v in e.items()]
        triples += [(idx[u], idx[c], v) for u, a in w.auth.items() for c, v in a.items()]
        src, dst, wt = (np.array(x) for x in zip(*triples))
        n = len(nodes)
        r = pagerank(n, src.astype(int), dst.astype(int), wt.astype(float), np.full(n, 1.0 / n))
        return {c: r[idx[c]] for c in w.contracts}

    if method in ("pc-er", "pc-er+bind"):
        idx = {c: i for i, c in enumerate(w.contracts)}
        n = len(idx)
        restart = np.zeros(n)
        for u, a in w.auth.items():
            for c, s in shares(a).items():
                restart[idx[c]] += w.fees[u] * s
        restart /= restart.sum()
        e = contract_edges(w, BETA_DEP, BETA_DEL, with_bindings=(method == "pc-er+bind"))
        src = np.array([idx[a] for a, _ in e], dtype=int)
        dst = np.array([idx[b] for _, b in e], dtype=int)
        wt = np.array(list(e.values()))
        r = pagerank(n, src, dst, wt, restart)
        return {c: r[i] for c, i in idx.items()}

    raise ValueError(method)


def rank_of_target(s: dict[str, float]) -> int:
    x = s[TARGET]
    return 1 + sum(1 for c, v in s.items() if c != TARGET and v > x + 1e-15)


def min_cost_to_top(base: World, attack: str, method: str) -> float | None:
    """Smallest attack cost that puts the target in the top TOP, or None."""
    def ok(k: int) -> bool:
        return rank_of_target(score(attacked(base, attack, k)[0], method)) <= TOP

    if ok(0):
        return 0.0
    # Double the attack size up to K_CAP, then narrow down by bisection. This
    # assumes that a larger attack never lowers the target's rank.
    lo, hi = 0, 1
    while not ok(hi):
        if hi >= K_CAP:
            return None
        lo, hi = hi, min(hi * 2, K_CAP)
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if ok(mid):
            hi = mid
        else:
            lo = mid
    return attacked(base, attack, hi)[1]


METHODS = ["callers", "dep-pr", "er-uniform", "pc-er", "pc-er+bind"]
METHOD_LABELS = {
    "callers": "Distinct callers",
    "dep-pr": "Dependency PageRank, uniform restart",
    "er-uniform": "EndorseRank on Stacks, uniform restart",
    "pc-er": "PC-EndorseRank (fee-weighted restart)",
    "pc-er+bind": "PC-EndorseRank with run-time trait bindings",
}
ATTACKS = ["A1", "A2", "A4"]
# LaTeX macro names cannot contain digits or hyphens.
MACRO_NAMES = {"callers": "Callers", "dep-pr": "DepPR", "er-uniform": "ERUniform", "pc-er": "PCER",
               "pc-er+bind": "PCERBind", "A1": "AOne", "A2": "ATwo", "A4": "AFour"}


def fmt_cost(c: float | None) -> str:
    if c is None:
        return "not reached"
    return f"{c:,.0f}"


def write_latex(costs: dict, ranks: dict, stats: dict) -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    head = "% Generated by scripts/toy_sybil_example.py. Do not edit by hand.\n"
    lines = [head,
             "\\begin{tabular}{@{}lrrr@{}}\n\\toprule\n",
             "Scoring rule & A1 & A2 & A4 \\\\\n\\midrule\n"]
    for m in METHODS:
        cells = " & ".join(fmt_cost(costs[(m, a)]) for a in ATTACKS)
        lines.append(f"{METHOD_LABELS[m]} & {cells} \\\\\n")
    lines.append("\\bottomrule\n\\end{tabular}\n")
    (TABLE_DIR / "toy-sybil-cost.tex").write_text("".join(lines), encoding="utf-8")

    lines = [head,
             "\\begin{tabular}{@{}llrrrrr@{}}\n\\toprule\n",
             "Attack & $k$ & Callers & Dep-PR & ER-uniform & PC-ER & PC-ER+bind \\\\\n\\midrule\n"]
    for a in ATTACKS:
        for k in GRID:
            cells = " & ".join(str(ranks[(a, k, m)]) for m in METHODS)
            lines.append(f"{a} & {k:,} & {cells} \\\\\n")
        if a != ATTACKS[-1]:
            lines.append("\\addlinespace\n")
    lines.append("\\bottomrule\n\\end{tabular}\n")
    (TABLE_DIR / "toy-sybil-ranks.tex").write_text("".join(lines), encoding="utf-8")

    macros = [head]
    for key, val in stats.items():
        macros.append(f"\\newcommand{{\\Toy{key}}}{{{val}}}\n")
    for (m, a), c in costs.items():
        macros.append(f"\\newcommand{{\\ToyCost{MACRO_NAMES[m]}{MACRO_NAMES[a]}}}{{{fmt_cost(c)}}}\n")
    # How many times more a wallet farm (A2) costs under fee weights than under a uniform restart.
    ratio = costs[("pc-er", "A2")] / costs[("er-uniform", "A2")]
    macros.append(f"\\newcommand{{\\ToyRatioATwo}}{{{ratio:.0f}}}\n")
    (TABLE_DIR / "toy-sybil-stats.tex").write_text("".join(macros), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--latex", action="store_true", help="write LaTeX tables to manuscript/tables/")
    args = ap.parse_args()

    base = honest_world(np.random.default_rng(SEED))
    honest_fees = np.array(list(base.fees.values()))
    callers = score(base, "callers")
    n_honest = len(base.contracts) - 1
    stats = {
        "Wallets": f"{N_HONEST_WALLETS:,}",
        "Contracts": str(n_honest),
        "MeanFee": f"{honest_fees.mean():.1f}",
        "MaxCallers": f"{int(max(v for c, v in callers.items() if c != TARGET))}",
        "Top": str(TOP),
        "DeployFee": f"{DEPLOY_FEE:.0f}",
    }
    print(f"honest wallets: {N_HONEST_WALLETS}, honest contracts: {n_honest}")
    print(f"mean fees paid per honest wallet: {honest_fees.mean():.1f} call-fee units")
    print(f"most callers of an honest contract: {stats['MaxCallers']}")

    print("\nRank of the target among contracts (1 = top):")
    ranks = {}
    print(f"{'attack':6} {'k':>6} " + " ".join(f"{m:>11}" for m in METHODS))
    for a in ATTACKS:
        for k in GRID:
            w, _ = attacked(base, a, k)
            row = [rank_of_target(score(w, m)) for m in METHODS]
            for m, rk in zip(METHODS, row):
                ranks[(a, k, m)] = rk
            print(f"{a:6} {k:>6} " + " ".join(f"{rk:>11}" for rk in row))

    print(f"\nMinimum attack cost to reach the top {TOP} (call-fee units):")
    costs = {}
    print(f"{'method':12} " + " ".join(f"{a:>12}" for a in ATTACKS))
    for m in METHODS:
        row = [min_cost_to_top(base, a, m) for a in ATTACKS]
        for a, c in zip(ATTACKS, row):
            costs[(m, a)] = c
        print(f"{m:12} " + " ".join(f"{fmt_cost(c):>12}" for c in row))

    if args.latex:
        write_latex(costs, ranks, stats)
        print(f"\nwrote {TABLE_DIR / 'toy-sybil-cost.tex'}, toy-sybil-ranks.tex, toy-sybil-stats.tex")


if __name__ == "__main__":
    main()
