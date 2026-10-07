#!/usr/bin/env python3
"""시빌 공격이 대상 컨트랙트의 순위를 얼마나 움직이는지 보여 주는 합성 예제.

원고 5절은 세 가지를 주장한다.

1. 지갑-컨트랙트 그래프에 균등 재시작을 쓰면 PageRank는 모든 지갑에 같은 질량을
   준다. 따라서 지갑을 하나 더할 때마다, 그 지갑이 얼마를 걸든 상관없이, 그 지갑이
   승인한 컨트랙트가 같은 만큼 올라간다(명제 1).
2. 재시작을 낸 수수료로 가중하면 수수료 예산을 여러 지갑에 나눠도 얻는 것이 없다
   (명제 2).
3. 재시작 질량이 없고 정직한 컨트랙트에서 들어오는 간선도 없는 컨트랙트는 점수를
   얻지 못한다(명제 3). 실행 시점 trait 바인딩을 간선으로 치면 공격자가 호출 비용만
   내고 그런 간선을 얻으므로, 바인딩은 간선이 아니다.

이 스크립트는 정직한 컨트랙트와 지갑으로 된 작은 가짜 그래프를 만들고, 공격자의
대상 토큰을 더한 뒤, 순위 규칙마다 대상을 상위 3위 안에 올리는 데 공격자가 얼마를
내야 하는지(최소 호출 수수료 단위)를 잰다. 그래프는 꾸며 낸 것이다. 출력은 명제를
예시할 뿐 Stacks 메인넷에 대해서는 아무것도 말하지 않는다.

공격(원고 7절의 번호를 따른다. A3 왕복 송금은 AWP에만 통하므로 여기서는 뺐다):
    A1  대상을 참조하는 컨트랙트 k개 배포(링크 팜)
    A2  대상을 한 번씩 승인하는 지갑 k개 생성(지갑 농장)
    A4  대상을 trait 인자로 넣어 정직한 라우터를 k번 호출

순위 규칙:
    callers      그 컨트랙트를 승인한 서로 다른 지갑의 수
    dep-pr       컨트랙트 참조 위의 PageRank, 균등 재시작
    er-uniform   Stacks로 옮긴 EndorseRank: 지갑과 컨트랙트가 노드, 지갑 간선에
                 최신 승인 값, 균등 재시작
    pc-er        PC-EndorseRank: 컨트랙트만 노드, 수수료로 가중한 재시작
    pc-er+bind   pc-er에 실행 시점 trait 바인딩을 라우터 간선으로 더한 절제 분석.
                 라우터의 바인딩 간선 전체에 라우터의 정적 참조와 같은 가중치를 주고,
                 토큰이 바인딩된 횟수에 비례해 나눈다.

순위는 점수가 엄격히 더 높은 컨트랙트만 세므로 동점은 대상에게 유리하고, 보고하는
비용은 실제보다 낮게 나올 수는 있어도 높게 나오지는 않는다. 원고의 수수료 상한
f_max는 뺐다.

사용법:
    python scripts/toy_sybil_example.py           # 표를 출력
    python scripts/toy_sybil_example.py --latex   # LaTeX 표도 씀
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

D = 0.85  # 감쇠 계수(AWP, EndorseRank와 같음)
TOL = 1e-8  # 원고 5.6절의 l1 허용 오차와 반복 상한
MAX_ITER = 300
SEED = 20261007
N_HONEST_WALLETS = 300
CALL_FEE = 1.0  # 최소 수수료로 보낸 호출 한 번이 비용의 단위
DEPLOY_FEE = 10.0  # 작은 컨트랙트 배포 한 번
BETA_DEP = 1.0
BETA_DEL = 2.0
TOP = 3
K_CAP = 200_000  # 시험하는 가장 큰 공격 크기
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
    # 지갑 -> {컨트랙트: 최신 승인 값}
    auth: dict[str, dict[str, float]]
    fees: dict[str, float]
    # 라우터 호출에서 본 실행 시점 trait 바인딩: 토큰 -> 횟수
    bindings: dict[str, float] = field(default_factory=dict)


def honest_world(rng: np.random.Generator) -> World:
    contracts = [TRAIT, *TOKENS, "math-lib", *POOLS, "router", "vault", "dao", TARGET]
    dep: list[tuple[str, str]] = [(t, TRAIT) for t in TOKENS]  # impl-trait
    dele: list[tuple[str, str]] = []
    for pool, (t1, t2) in POOLS.items():
        dep += [(pool, TRAIT), (pool, "math-lib")]  # use-trait, 라이브러리 호출
        dele += [(pool, t1), (pool, t2)]  # as-contract? 안에서 토큰을 내줌
    dep += [("router", pool) for pool in POOLS] + [("router", TRAIT)]
    dele += [("vault", "tok-a"), ("vault", "tok-b")]
    dep += [("vault", "math-lib")]
    dele += [("dao", "vault"), ("dao", "router")]  # 켜진 확장
    dep += [(TARGET, TRAIT)]  # 공격자의 토큰도 SIP-010을 구현함

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
    """공격을 적용한 사본과 그 공격의 비용을 돌려준다."""
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
    """가중 PageRank. 댕글링 노드의 질량은 재시작 분포로 돌아간다."""
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
        # 절제 분석: 실행 시점 바인딩 전체에 라우터의 정적 참조와 같은 가중치를 주고,
        # 토큰이 바인딩된 횟수에 비례해 나눈다.
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
    """대상을 상위 TOP 안에 넣는 가장 작은 공격 비용. 도달하지 못하면 None."""
    def ok(k: int) -> bool:
        return rank_of_target(score(attacked(base, attack, k)[0], method)) <= TOP

    if ok(0):
        return 0.0
    # 공격 크기를 K_CAP까지 두 배씩 늘린 뒤 이분 탐색으로 좁힌다. 공격이 커져도
    # 대상의 순위가 내려가지 않는다고 가정한다.
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
    "callers": "호출자 수",
    "dep-pr": "의존성 PageRank, 균등 재시작",
    "er-uniform": "Stacks로 옮긴 EndorseRank, 균등 재시작",
    "pc-er": "PC-EndorseRank(수수료 가중 재시작)",
    "pc-er+bind": "PC-EndorseRank + 실행 시점 trait 바인딩",
}
ATTACKS = ["A1", "A2", "A4"]
# LaTeX 매크로 이름에는 숫자와 하이픈을 쓸 수 없다.
MACRO_NAMES = {"callers": "Callers", "dep-pr": "DepPR", "er-uniform": "ERUniform", "pc-er": "PCER",
               "pc-er+bind": "PCERBind", "A1": "AOne", "A2": "ATwo", "A4": "AFour"}


def fmt_cost(c: float | None) -> str:
    if c is None:
        return "도달 못 함"
    return f"{c:,.0f}"


def write_latex(costs: dict, ranks: dict, stats: dict) -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    head = "% scripts/toy_sybil_example.py가 만든 파일이다. 손으로 고치지 않는다.\n"
    lines = [head,
             "\\begin{tabular}{@{}lrrr@{}}\n\\toprule\n",
             "순위 규칙 & A1 & A2 & A4 \\\\\n\\midrule\n"]
    for m in METHODS:
        cells = " & ".join(fmt_cost(costs[(m, a)]) for a in ATTACKS)
        lines.append(f"{METHOD_LABELS[m]} & {cells} \\\\\n")
    lines.append("\\bottomrule\n\\end{tabular}\n")
    (TABLE_DIR / "toy-sybil-cost.tex").write_text("".join(lines), encoding="utf-8")

    lines = [head,
             "\\begin{tabular}{@{}llrrrrr@{}}\n\\toprule\n",
             "공격 & $k$ & 호출자 수 & 의존성 PR & ER(균등) & PC-ER & PC-ER+바인딩 \\\\\n\\midrule\n"]
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
    # 지갑 농장(A2)의 비용이 균등 재시작보다 수수료 가중에서 몇 배인지.
    ratio = costs[("pc-er", "A2")] / costs[("er-uniform", "A2")]
    macros.append(f"\\newcommand{{\\ToyRatioATwo}}{{{ratio:.0f}}}\n")
    (TABLE_DIR / "toy-sybil-stats.tex").write_text("".join(macros), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--latex", action="store_true", help="manuscript/tables/에 LaTeX 표를 쓴다")
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
    print(f"정직한 지갑: {N_HONEST_WALLETS}개, 정직한 컨트랙트: {n_honest}개")
    print(f"정직한 지갑 하나가 낸 평균 수수료: 최소 호출 수수료의 {honest_fees.mean():.1f}배")
    print(f"정직한 컨트랙트의 최대 호출자 수: {stats['MaxCallers']}")

    print("\n컨트랙트 가운데 대상의 순위(1 = 맨 위):")
    ranks = {}
    print(f"{'공격':6} {'k':>6} " + " ".join(f"{m:>11}" for m in METHODS))
    for a in ATTACKS:
        for k in GRID:
            w, _ = attacked(base, a, k)
            row = [rank_of_target(score(w, m)) for m in METHODS]
            for m, rk in zip(METHODS, row):
                ranks[(a, k, m)] = rk
            print(f"{a:6} {k:>6} " + " ".join(f"{rk:>11}" for rk in row))

    print(f"\n상위 {TOP}위 안에 드는 최소 공격 비용(최소 호출 수수료 단위):")
    costs = {}
    print(f"{'순위 규칙':12} " + " ".join(f"{a:>12}" for a in ATTACKS))
    for m in METHODS:
        row = [min_cost_to_top(base, a, m) for a in ATTACKS]
        for a, c in zip(ATTACKS, row):
            costs[(m, a)] = c
        print(f"{m:12} " + " ".join(f"{fmt_cost(c):>12}" for c in row))

    if args.latex:
        write_latex(costs, ranks, stats)
        print(f"\n썼음: {TABLE_DIR / 'toy-sybil-cost.tex'}, toy-sybil-ranks.tex, toy-sybil-stats.tex")


if __name__ == "__main__":
    main()
