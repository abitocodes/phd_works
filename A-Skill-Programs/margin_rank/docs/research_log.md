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

---

## 2026-06-23 — 6-method Aave W↔W PageRank × 6-proxy matrix

### 동기

7-method 비교에서 **LP-PR·RiskProp** 등은 Transfer 재가중이므로 “Transfer 외 새 엣지”가 아니다. **실질 wallet↔wallet(W↔W) 후보**를 조사한 결과:

| 후보 | W↔W 여부 | 비고 |
|------|----------|------|
| Aave LiquidationCall | **예** | liquidator → user |
| Aave Borrow (onBehalfOf) | **예** | initiator → onBehalfOf |
| Aave Repay | **예** | repayer → user |
| Aave Credit Delegation | **예** (설계) | delegator → delegatee; BQ 추출 deferred |
| GMX PositionDecrease | **아니오** | POOL/SINK star; 노드 속성만 |

→ **EndorseRank·AWP + Aave 4종 W↔W PR** = **6 methods × 6 proxy families** 행렬을 추가한다.

### 설계

- **Methods**: AWP, EndorseRank, LiqCall-PR, Borrow-PR, Repay-PR, Delegation-PR
- **Borrow/Repay pool-leg** (pool → user): PageRank 입력 **아님**; `aave_edge_diagnostics`에만 기록
- **Credit Delegation**: `margin_config.yaml`에 topic placeholder; real parquet 없으면 degenerate(---) 처리
- **Synthetic**: `generate_synthetic_aave.py` — lending 3종 + delegation fixtures hook

### 실데이터 결과 (n = 5,521)

표: `2-Dissertation-Draft/results/tables/alignment-six-aave-methods.tex`

| Method | Transfer | Allowance | Liq. | Inv.risk | Sybil | GMX | Runtime (s) |
|--------|----------|-----------|------|----------|-------|-----|-------------|
| AWP | **0.534** | -0.030 | **0.113** | **0.107** | **0.286** | **0.179** | 24.0 |
| EndorseRank | 0.333 | **0.355** | 0.093 | 0.035 | 0.233 | 0.096 | 3.5 |
| LiqCall-PR | 0.053 | -0.012 | -0.008 | 0.026 | 0.025 | 0.030 | 0.015 |
| Borrow-PR | 0.113 | -0.019 | 0.020 | 0.014 | 0.055 | 0.023 | 0.098 |
| Repay-PR | 0.143 | -0.024 | 0.016 | 0.022 | 0.068 | 0.026 | 0.156 |
| Delegation-PR | --- | --- | --- | --- | --- | --- | 0.000 |

**해석 요약**

- Aave W↔W 전용 PR(Liq/Borrow/Repay)은 **모든 proxy family에서 mean τ ≈ 0.05–0.14** — transfer·allowance·GMX 대비 **construct validation 기준(τ ≥ 0.35) 미달**.
- **AWP** transfer·GMX·liquidation/inverse-risk/sybil family **열 최대**; **EndorseRank** allowance **유일 우세**.
- Aave sparse coverage: liq **45** (0.9%), borrow **484** (9.1%), repay **787** (15.3%) — 희소 이벤트로 PR 신호 약함.

### Kendall τ 문헌 벤치마크 (정렬 해석용)

| 기준 | τ 범위 | 출처·맥락 |
|------|--------|-----------|
| Construct validation “의미 있음” | **≥ 0.35–0.5** | PageRank·블록체인 credit 논문 다수 |
| 실질적 무의미 | **\|τ\| < 0.10** | 약한/노이즈 수준 |
| “상당한 순위 변화” | **τ < 0.8** (비교 시) | Vigna et al., PageRank citation ranking |

→ Liq/Borrow/Repay PR의 0.05–0.14는 **무의미~매우 약한 정렬**로 읽는 것이 타당.

### 운영 이슈·복구

1. **`--fixtures`가 real `wallet_rankings`(5,521)를 synthetic(571)으로 덮어씀** — eval n 불일치 발생.
2. 복구: `extract_margin_week.py --extract --merge-only` + `decode_gmx_events.py` → **365,488 events / 5,521 wallets** 복원.
3. **`load_raw_parquet_dir`**: `*_arbitrum.parquet` 합본을 월별 shard보다 **우선** 로드 (synthetic 제외).
4. **`extract_margin_week --merge-only`**: `--extract` 없이 merge-only 단독 실행 허용 (argparse 수정).

Aave lending raw는 디스크에 이미 존재; BQ 재추출 없이 `preprocess_aave_lending.py` → **8,801 rows**.

### 재생성

```powershell
cd A-Skill-Programs/margin_rank
python scripts/preprocess_aave_lending.py
python scripts/compute_reputation_ranks.py
python scripts/run_dissertation_eval.py --real --export-latex
```

- CSV: `data/processed/six_aave_method_proxy_matrix.csv` (gitignore)
- JSON: `data/processed/eval_summary.json` — `six_aave_method_proxy_matrix`, `aave_edge_diagnostics`
- LaTeX preset: `export_method_matrix.py --preset six-aave`

### 후속

- Credit Delegation BQ 추출 완료 시 Delegation-PR τ 재평가
- 7-method 표(`alignment-seven-methods.tex`)는 별도 preset 유지; six-aave는 **W↔W Aave 전용** 비교축
