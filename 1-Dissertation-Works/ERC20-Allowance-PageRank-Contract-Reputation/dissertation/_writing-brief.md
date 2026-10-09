# Writing brief for the contract-reputation thesis (not part of the build)

## What the thesis is

- Title: *Integrating ERC-20 Allowance Edges into PageRank for On-Chain Smart Contract Reputation Scoring*. Candidate Taehong Kwon (student number 28576810), PhD in Computer Science, University of South Africa. Supervisor Prof. Ernest Mnkandla; co-supervisors Prof. Donatien Koulla Moulla and Dr. David Sena Attipoe.
- The thesis text starts from the earlier manuscript in this folder (copied from another draft) and keeps its structure, methods, section titles and style. Only the data change: every scored and evaluated address is a **smart contract**. Externally owned accounts (EOAs) appear in the graphs only as owners, senders and recipients and are never scored or evaluated.
- Chain: Arbitrum One. Data: public BigQuery logs, 1 October 2023 to 30 September 2026.

| Item | Definition |
|---|---|
| Observation window | 2023-10-01 00:00 UTC to 2026-06-30 23:59:59 UTC (33 months); time decay anchored at the end |
| Matched cohort (main sample) | 27,844 contracts that received a non-zero `Approval` from at least three distinct owners in the observation window; fixed from approval logs and `eth_getCode` before any transfer was aggregated |
| Account type | `eth_getCode` at block 513,216,506 (9 October 2026); bytecode = contract; no code or an EIP-7702 delegation designator = EOA. Of 29,022 candidates: 27,844 contracts, 1,121 EOAs, 57 EIP-7702 EOAs |
| Extraction | Approvals with a cohort contract as owner or spender; transfers with a cohort contract as sender or recipient (ego network of the cohort). 389,866,882 approval logs and 1,538,404,067 non-zero transfer logs |
| Holdout W0 | scores frozen 2026-03-31 23:59:59 UTC, labels April–June 2026; spender cohort = contract spenders with a positive latest allowance at the freeze |
| Registered window W1 | scores frozen 2026-06-30 23:59:59 UTC, labels July–September 2026; rule registered before the July–September logs were extracted |
| Trader cohort | GMX V2 accounts that are contracts, appear in the freeze-date graph and close at least three positions in the label window |
| Plan | `experiments/docs/analysis_plan.md`, committed 9 October 2026 (commit 43d8045) before any log was extracted; it fixes the cohorts, scores, labels, statistics and rule A (the rule for the coupled operator) |

Scores: EndorseRank, AWP (Do, Do and Nguyen, 2023), C-PR at λ ∈ {0, 0.25, 0.5, 0.75, 1}, S-PR, raw in-approve degree and raw transfer in-degree. Statistics: Kendall τ_b and Spearman ρ, 400 paired bootstrap resamples (seed 42), paired contrasts.

## Rules (from the supervisors' and examiner's comments; codes in brackets)

1. Never mention, cite or allude to any earlier thesis, draft, pilot study or research proposal of the candidate. The thesis reads as one study that began with the plan of 9 October 2026. Do not write "unlike before", "previously", "the proposal", "the earlier version".
2. Scored and evaluated addresses are contracts. Say "contract" or "spender contract", not "wallet", wherever the object of a score is meant; "owner" and "account" stay for the approving side.
3. Citations are APA 7 author–date through biblatex: `\textcite{key}` when the authors are part of the sentence, `\parencite{key}` otherwise. Keys are in `Config/references.bib`; `Config/refmap.csv` maps each old `\cend{n}` number to its key. One source per claim; never three or more keys in one citation (D20). Only scholarly sources, except a standard (EIP) or a tool's own documentation for describing that tool (P35). Recent peer-reviewed work from `Config/references-candidates.md` may be added where it supports a claim (D396); cite only what the sentence actually says.
4. No citations in the abstract (D3); no bold in the abstract (D6); every sentence says who did what (D7). The abstract keeps six elements: background, problem, approach, numerical results, comparison with existing techniques, social impact (D1). UNISA requires a list of key terms after the abstract.
5. A number is stated where it is established (Chapter 4) and in the abstract; elsewhere refer to the table or section (D82). Definitions live in one place and are referenced elsewhere (D378).
6. Every τ comes with its 95% interval; comparisons are paired contrasts with intervals; no "meaningfully larger" without an interval (D237). No interpretation bands or self-made thresholds for τ (D128, D129).
7. Agreement of a score with proxies built from its own edges is an intended-construct check, never "validation" (D74). PageRank is compared with the raw degree it smooths, and the text says plainly when the degree wins (D310).
8. Speed that comes from a sparser graph is reported as a consequence of |E|, not as a contribution or an advantage of the algorithm (D62). Runtimes always appear with |V| and |E|; five timed runs after one warm-up (D240); one measurement per graph and setting reused across tables, and the text says so (D283); scaling tables give per-stage |V| and |E| (D286, D288).
9. Do not call sample-definition changes "robustness"; the matched cohort is the primary sample (D299).
10. Research objectives O1–O5 mapped to RQ1–RQ5 (D72); Chapter 5 shows how each was met. Main research question is one sentence of about thirty words (X5).
11. Discuss deployed reputation tools such as Human Passport and how trust is usually formed in DeFi (X1–X4); keep the limitation that no off-chain information is used.
12. AWP is attributed only to Do, Do and Nguyen (2023, IEEE RIVF); PageRank and HodgeRank on Ethereum to Do and Do (2023, IJSI) (D2).
13. Reproducibility: repository URL `https://github.com/abitocodes/phd_works`, versioned configuration, machine-readable summaries, commit hash (D81). Ethics: Unisa clearance number and date as placeholders `[TBD]` with the certificate in the appendix (D264).
14. Style (P36): plain, concrete sentences. No inflated vocabulary, no formulaic triplets, no "not only … but also", no em-dash chains, no promotional tone, no summary sign-offs. Never write that something was deleted or removed from the manuscript.
15. Keep chapter and section titles and their order; if a title must change for the contract framing, change `01-Intro/03-TOC.tex` with it (P12). Introduce every figure and table in the text before it appears (P23); never open a section with a list (P24).
