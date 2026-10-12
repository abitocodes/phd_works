# Context for revising the manuscript to the USD analysis (not part of the build)

Read this file, `_writing-brief.md` and `_claims.md` before editing any chapter.

## What changed

- On 10 October 2026, after the registered results (same window, W0, W1) were known, the amounts were revised (`experiments/docs/revision_price_weighting.md`; Chapter 3, Section~\ref{sec:amount-revision}, already rewritten). Commits a897475 (07:54 UTC), 09dfc32 (08:12 UTC) and 2705b28 (11:24 UTC), all before any revised score was computed (the first revised score was computed at 11:36 UTC).
- Every amount is in US dollars: raw value / 10^decimals × the token's DefiLlama daily close (transfers at the price of their UTC day, latest allowances at the price of the anchor's day).
- Only five tokens: WETH, USDC, USDT0, ARB, WBTC. Rule: Chainlink market-price feed on Arbitrum One rated low or medium market risk that prices the token itself, its 1:1 issuer wrapper or the Ethereum token of which it is the canonical-bridge copy (64 of 133 mapped tokens qualified), with a DefiLlama price (46), then the five with the most rows in the observation-window data (75.75% of all rows). Write "USDT0" in the text (not the ₮ glyph).
- Value transform V(z) = 2/(1+e^{-bz}) − 1 with b = ln 3 / m: m_T = 200 dollars (transfers), m_A = 62 dollars (allowances). V(m) = 1/2, V(2m) = 0.8, V(m/2) = 0.27. The plan had b = 1 on raw base units, which made V ≈ 1 for almost every amount.
- C-PR allowance layer: Σ_token min(a*, U), U = 20,000 dollars (99th percentile of single transfers up to t1). C-PR transfer layer: Σ x_e σ(Δt_e) in dollars. In-value proxy: USD sum; in-approve value: sum of capped allowances.
- Matched cohort: contracts approved on one of the five tokens by at least three distinct owners: n = 15,107 (the plan's cohort, now the registered analysis, was 27,844). Spender and trader cohorts, graphs, proxies and spender labels all use the five tokens.
- The top-20-token robustness check is replaced by a value-slope check (b × 10 and b / 10): Table `tab:robustness-slope` replaces `tab:robustness-tokens`; the file `results/tables/robustness-tokens.tex` is no longer generated, `results/tables/robustness-slope.tex` is.
- New tables: `tab:usd-tokens` (Appendix 8.4, the five tokens, rows kept and left out, prices), `tab:registered-vs-revised` (Appendix 8.6, Section `sec:map-registered`, the registered decision contrasts and verdicts beside the revised ones).
- New labels to cite: `sec:amount-revision` (Chapter 3), `sec:map-registered` (Appendix 8.6).

## Status words (strict)

- The revised analysis is the main analysis; Chapter 4 reports it. Never call a revised result "registered", "preregistered" or "fixed in advance".
- The plan and the registration still fixed the rules (rule A, rule B with δ = 0.01, F4–F6, the two sensitivity analyses, P, Q, R1–R3 and their wording) before the data of the registered analysis. On the revised scores the same rules are applied after the registered results were known: say "rule B, applied to the revised scores" or "on the revised scores", and that these verdicts are a re-analysis, not registered tests. Say this once per section where verdicts appear, not in every sentence.
- When a sentence describes what the registered analysis found (raw base units, every token), label it "in the registered analysis" and point to Appendix~\ref{sec:map-registered} / Table~\ref{tab:registered-vs-revised}. Registered numbers come from `experiments/data/3-published-results-for-thesis/results_digest.md`; use them only in such sentences.
- Every other number comes from the revised digest `experiments/data/3-published-results-for-thesis/revised-usd/results_digest.md` (or the JSON it cites). Numbers that do not depend on the revision (GMX closes per quarter, windows, dates, block numbers, the candidate counts 29,022 / 1,121 / 57, BigQuery scan costs of the plan) stay as they are.
- The registration of W1 and the window W1 itself remain "registered" (the window, its label definitions and the rules were registered); the results computed on W1 in the revised analysis are not.

## Writing rules (from `_writing-brief.md`, repeated because they are often broken)

- Every τ and every Δτ with its 95% interval in the form used in the chapter, e.g. `$0.585$ $[0.578,0.592]$`. No interpretation bands (weak/strong/moderate). No p-values.
- State a number where Chapter 4 establishes it and in the abstract; elsewhere refer to the table or section. Chapters 1, 5 and 6 may repeat a key number only where they already did so in the same place.
- Plain sentences; no "not only … but also", no em-dash chains, no promotional tone, no summary sign-offs. Never write that something was removed from the manuscript.
- APA author–date citations with `\textcite{}` / `\parencite{}`, one key per command. New keys available: `chainlinknddatafeeds`, `defillamanddocs`.
- Never mention, cite or allude to any earlier thesis, draft, pilot or proposal of the candidate.
- Contracts are scored; EOAs are owners/senders/recipients only.
- Do not edit `results/tables/*.tex` (generated) or any file other than the one you are assigned.

## Direction of results

Results may have changed direction under the revision. Do not keep an interpretive sentence because it was there: re-derive every comparison (which score leads, whether an interval excludes zero, whether a rule holds) from the revised digest, and rewrite the sentence if the conclusion changed. `_claims.md` states the revised claims C1–C6.
