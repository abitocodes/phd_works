# Handoff — dissertation work (2026-10-11)

This is where the thesis work stands. Read it before touching the manuscript, the experiments or the Korean edition.

## What changed on 2026-10-11

- The study (started 2026-10-09 in `1-Dissertation-Works/ERC20-Allowance-PageRank-Contract-Reputation/`) now lives under `1-Dissertation-Works/ERC20-Allowance-PageRank-Wallet-Reputation/`; the old Contract folder is gone.
- The thesis keeps the approved title *Integrating ERC-20 Allowance Edges into PageRank for Enhanced On-Chain Wallet Reputation Scoring* (title page, chapter cover, declaration, PDF metadata).
- Archived material is in `…/archive/` (read-only; see its README).

(`…` = `1-Dissertation-Works/ERC20-Allowance-PageRank-Wallet-Reputation`)

## Repos

- `phd_works` (this repo).
- `…/dissertation/overleaf-github` is a submodule (`phd-dissertation-draft-en`; its name in `.gitmodules` is still `2-Dissertation-Draft/overleaf-github`, on purpose). Overleaf reads its `main`. It holds the thesis sources, the built `main.pdf` and per-chapter PDFs, the journal manuscripts (`manuscripts/A-plos-one`, `manuscripts/B-ieee-access`) and their supporting analyses (`analysis/`). Run `git submodule update --init` if the folder is empty.
- Experiment code and data: `…/experiments` (moved from the Contract folder; `scripts/export_latex.py` now writes into the submodule). The tests import archived scripts read-only from `…/archive/wallet-reputation-experiments/scripts`.
- Korean edition: `…/dissertation/overleaf-github-ko` (easy Korean, rules in `TRANSLATION-GUIDE.md`, checks in `scripts/`).
- Writing rules for the thesis and the papers: `…/dissertation/notes/_writing-brief.md`.

## The study in one paragraph

Smart contracts on Arbitrum One that at least three distinct owners approved are ranked by EndorseRank (PageRank on the latest non-zero allowances), AWP (transfer PageRank), the coupled walk C-PR and S-PR, and compared with the raw degrees and with out-of-window labels in W0 (freeze 2026-03-31) and W1 (freeze 2026-06-30). The registered analysis (raw units, every token, cohort 27,844) was fixed before this study's extraction (plan `43d8045`, W1 registration `0d3a057`). The revised analysis (USD, five priced tokens, cohort 15,107; commits `a897475`, `09dfc32`, `2705b28`, after the registered results were known) is the thesis's main analysis and is never called registered. C-PR at λ = 0.5 met neither rule A nor rule B in either analysis.

## Rules that must not be broken

- Do not modify `…/proposal` or `…/archive`.
- Do not edit numbers by hand in `results/tables/` or `Figures/generated/`; regenerate with `CONTRACT_REP_VARIANT=usd python scripts/export_latex.py` in `…/experiments`.
- Do not change `experiments/docs/analysis_plan.md` §1–6, `experiments/config/contract_reputation.yaml` or the W1 registration files.
- Dissertation prose follows `_writing-brief.md` (no mention of earlier theses, drafts or the proposal; contracts, not wallets, as scored objects; plain style).
- Decisions of 2026-10-12 (user), for every text (thesis, Korean edition, manuscripts, cover letters, READMEs, supplements, slides, docs):
  - no date or time at which anything became public, was pushed to GitHub or appeared in GitHub's records; the plan and the registration are "committed to the public repository". Commit times and BigQuery job times stay;
  - a claim that data, logs, labels or outcomes had not yet been extracted, read, seen or known is scoped to this study ("before this study extracted any log"), without mentioning any earlier study;
  - no sentence that explains the title or sets it against the scored contracts.
- Git:
  - files are CRLF on the user's Windows checkout, so stage with `git -c core.autocrlf=true add`;
  - author is abito <33889084+abitocodes@users.noreply.github.com>;
  - commit messages have a Korean conventional title and one block per hunk, `path[start:end]`, followed by `-` bullets;
  - never commit `.cursor/journey.md`.
- After editing the English manuscript, rebuild (xelatex → biber → xelatex ×2; `build.ps1`) and check for 0 errors and 0 undefined references; then re-translate the changed paragraphs in the Korean edition and run its checks.
