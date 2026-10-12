# Open items for the manuscript (not part of the build)

- Unisa: title, abstract and key terms in two further official languages are required at submission; translations must come from Unisa language services (placeholder note in 01-Intro/02-Abstract.tex, not machine translated).
- Ethics clearance number and date are [TBD] in Chapter 3 and Appendix 8.7.
- fritsch2024voting (replaces the practitioner volume carter2021defi in 2.16): volume, issue and article number checked against the ETH Library record; add the DOI after checking it on doi.org (not reachable from the cloud session).
- The cohort rule is defined in Section 3 (sec:data-sources); Ch1 and Ch4 now refer to it. The glossary entry and the limitation in Ch5 (cohort selection) still state the rule in one sentence each, on purpose.
- Supervisors have not yet reviewed this draft.
- Revision of 10 October 2026 (USD amounts, five tokens; `_revision-context.md`): the supervisors have not yet confirmed that the revised analysis replaces the registered one as the main analysis; the registered results are in Appendix 8.6 (sec:map-registered).
- Abstract: the revision sentences lengthened it; check it against the Unisa abstract length limit.
- Future work names a registered test of the revised analysis on a later window (October to December 2026 as the example); change the window if another is preferred.
- 지도교수님께 사후 보고(빌드와 무관): 2026년 10월 9일 분석 계획보다 앞서, 이전 지갑 평판 분석이 2026년 6~8월 GMX V2 포지션 마감 로그를 모두 내려받아 두었습니다(`archive/wallet-reputation-experiments/data/1-raw-blockchain-logs/registered-replication-2026-06-to-2026-08/gmx-position-close-logs`). 이 로그에는 W1 라벨 기간(7~9월)에 3건 이상 마감한 계약 계정 131개의 7~8월 마감 3,876건이 모두 들어 있고((block_number, log_index)로 대조), 9월 마감 2,887건은 들어 있지 않습니다. 131개 가운데 63개는 그 분석의 추출 주소 99,080개(`archive/wallet-reputation-experiments/data/2-processed-tables-and-evaluations/extraction_wallet_set.parquet`)에 들어 있었습니다. 그 분석은 이 계약들을 W1 라벨로 채점하지 않았습니다. 다만 그 분석의 트레이더 홀드아웃(2026-05-31 동결, 6~8월 라벨)은 63개 가운데 61개를 6~8월 청산 없는 마감 비율로 평가했고, 결과 파일(`registered-replication-2026-06-to-2026-08/fresh_holdout_summary.json`)에는 1,402개 전체의 집계 계수만 남아 있습니다. 논문과 투고 원고는 이제 시점에 관한 문장을 이 연구의 추출 기준으로 씁니다.
