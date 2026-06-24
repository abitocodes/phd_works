# EndorseRank 실증 연구 로그

제안서(EndorseRank) 대비 BigQuery 실데이터 평가·대안 PageRank baseline 탐색 기록.

---

## 2026-06-23 — EndorseRank vs AWP 실데이터 평가

### 배경

논문 제안서는 **allowance 기반 EndorseRank**가 transfer 기반 **AWP**보다 **정렬(alignment)·효율(runtime)** 에서 우수함을 실증하려는 설계였다. 이를 위해 Arbitrum One에서 GMX V2 마진 cohort와 reputation subgraph를 BigQuery로 수집·평가 파이프라인을 구축했다.

### 데이터

- 소스: `bigquery-public-data.goog_blockchain_arbitrum_one_us.logs`
- GMX cohort: **n = 5,521** (최소 3회 close)
- 관찰 기간: **2025-12 ~ 2026-05** (6개월)
- Reputation: ERC-20 Approval + Transfer (월별 배치 추출)
- 상세: [`docs/bigquery_data_plan.md`](bigquery_data_plan.md), `data/processed/extraction_manifest.json` (로컬, gitignore)

### EndorseRank vs AWP 결과 (실측)

**원하는 “EndorseRank의 전반적 우수성”은 나오지 않았다.**

| 항목 | EndorseRank | AWP | 비고 |
|------|-------------|-----|------|
| PageRank runtime (s) | **2.8** | 23.8 | H3(효율) 방향 **일치** |
| Transfer mean τ | 0.333 | **0.534** | AWP 우세 |
| Allowance mean τ | **0.355** | -0.030 | ER **유일 우세 family** |
| Liquidation mean τ | 0.093 | **0.113** | AWP 우세 |
| Inverse risk mean τ | 0.035 | **0.107** | AWP 우세 |
| Sybil stability mean τ | 0.233 | **0.286** | AWP 우세 |
| GMX success mean τ | 0.096 | **0.179** | AWP 우세 |
| Inter-method τ (score) | — | — | 0.316 |

- EndorseRank transfer τ(0.333)는 allowance-only 방법치고 높은 편이나, AWP(0.534)보다는 낮다.
- Sybil family mean τ(0.233)는 **counterparty ratio(0.073)** 보다 **transfer tenure·active months(~0.30)** 가 끌어올린 값이다.

### 후속 방향

제안서 가설을 그대로 방어하기 어렵다고 판단, **다른 PageRank baseline**을 같은 6-proxy family로 비교하는 7×6 행렬을 추가한다 (GF-PR, LP-PR, CW-AWP, LF-PR, RiskProp). 표: `2-Dissertation-Draft/results/tables/alignment-seven-methods.tex`.

### 메모

- **GF-PR**은 GMX PositionDecrease PnL의 POOL/SINK star graph로, wallet↔wallet social edge가 없다. GMX proxy family τ가 매우 높을 경우 **construct overlap(순환)** 주의.
- LF-PR용 Aave V3 lending 로그 별도 BQ 추출 (~677 GiB dry-run, 6개월).

---

## 2026-06-23 — 7-method PageRank × 6-proxy matrix

### 산출

- `scripts/pagerank_variants.py`, `export_method_matrix.py`, Aave `extract_aave_lending.py` / `preprocess_aave_lending.py`
- 표: `2-Dissertation-Draft/results/tables/alignment-seven-methods.tex` (우측 열: PageRank **Runtime (s)**, 5 repeats)

### mean τ 열 최대 (요약)

| Method | Transfer | Allowance | GMX | Runtime (s) |
|--------|----------|-----------|-----|-------------|
| AWP | **0.534** | | 0.179 | 23.826 |
| EndorseRank | 0.333 | **0.355** | 0.096 | **2.809** |
| GF-PR | | | **0.583** | 1.804 |
| LP-PR | 0.529 | | 0.196 | 23.538 |
| LF-PR | 0.197 | | 0.032 | 0.101 |

- **RiskProp** ≈ AWP (transfer 0.534, runtime 21.0s) — liquidation-rate 가중이 미미.
- **GF-PR** GMX τ 0.583: GMX-native star graph; social reputation baseline과 구분.
- **EndorseRank** allowance·runtime에서 강점; transfer/GMX 계열은 AWP·LP-PR·CW-AWP가 경쟁.
