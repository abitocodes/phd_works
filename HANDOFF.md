# Handoff — dissertation work (2026-09-28)

This is where the thesis work stood at the end of the previous session. Read it before touching the manuscript or `margin_rank`.

## Repos

- `phd_works` (this repo). Latest commit is 0097fdb: the C-PR hybrid evaluation and the pipeline for the June–August registered replication.
- `2-Dissertation-Draft/overleaf-github` is a submodule (`phd-dissertation-draft-en`). Latest commit is 9459b33: the central claim reframed as an improvement over AWP. Run `git submodule update --init` if the folder is empty.
- Experiment code lives in `A-Skill-Programs/margin_rank`. `data/processed/` is not tracked; the committed summaries are under `results/`.

## Central claim, as it now stands

- Adding ERC-20 allowance edges to PageRank improves on AWP, the transfer-only walk.
- **Settled:** in the spring holdout (freeze on 28 Feb, labels Mar–May), EndorseRank beat AWP on both future labels. The contrasts were fixed in advance: +0.435 on new approvals, +0.102 on new senders.
- **C-PR (λ=0.5):**
  - It failed the 14 September rule, which required beating both single-layer methods. The thesis reports that failure as it is.
  - Against AWP alone it gained +0.251 [0.203, 0.306] on new approvals, with no difference on new senders. This was found only after the labels were in, so it is exploratory.
- **Where the verdict comes from:** the June–August replication, with hypotheses F1–F6. The design is in `margin_rank/docs/fresh_holdout_2026q3_plan.md` and `config/fresh_holdout_2026q3.yaml`.

## Remaining steps, in order

1. The user reviews the plan and the YAML. The YAML currently says `status: draft`, which means the replication is **not yet registered**.
2. Registration: change it to `status: registered` and commit the YAML, the plan, the scripts and the tests together, then push. This step runs on the user's PC.
3. `python scripts/extract_fresh_window.py --dry-run`, then `--extract --yes`. This needs BigQuery credentials and runs on the user's PC.
4. `python scripts/run_fresh_holdout.py` writes `data/processed/fresh_2026q3/fresh_holdout_summary.json`.
5. Fill the 10 `\freshpending{…}` placeholders in the manuscript with those results. When done, a search for `\freshpending` should return nothing. Locations:
   - Abstract l.12
   - Ch1 l.143
   - Ch4 l.192, l.205
   - Ch5 l.37, l.60, l.100
   - Ch6 l.19, l.27
   - Appendix E l.43
6. If the registration date changes from 28 September 2026, correct it in the abstract, Ch1, Ch3, Table 5.1 in Ch5, and Appendix E.

Report F1–F3 exactly as they come out, failures included (plan §5–6). Do not change λ, the labels, the cohorts, the 0.02 margin or the window.

## Rules that must not be broken

- Do not change the cover or the table-of-contents titles. New content goes into unnumbered-in-TOC subsections (3.7.1/3.7.2, 4.8.1/4.8.2).
- Do not modify `1-Proposal`.
- Dissertation prose must not read as AI-written:
  - no inflated vocabulary, formulaic triplets or "not only…but also";
  - no em-dash chains, promotional tone or summary sign-offs;
  - keep sentences plain and concrete.
- Git:
  - files are CRLF, so stage with `git -c core.autocrlf=true add`;
  - author is abito <33889084+abitocodes@users.noreply.github.com>;
  - commit messages have a Korean conventional title and one block per hunk, `path[start:end]`, followed by `-` bullets;
  - never commit `.cursor/journey.md`.
- Build: 175 pages, 0 errors, 0 undefined references at 9459b33. Check the build again after every edit.

## Other numbers you will need

- Raw degree baselines: in-approve degree gives τ=0.711 on new approvals, and transfer in-degree gives 0.472. The gain comes from the edge type, not from the walk.
- Exploratory trader holdout (29 Aug, n=1,860): AWP was ahead of EndorseRank on success count (0.131 vs 0.073) and realized gain (0.153 vs 0.048). The success rate was about 0 for both.
- Liquidation-free rate in the same window: EndorseRank 0.075, AWP 0.083. It was never computed for C-PR, and never out of window.
