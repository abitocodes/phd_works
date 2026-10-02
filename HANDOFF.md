# Handoff — dissertation work (2026-10-01)

This is where the thesis work stood at the end of the previous session. Read it before touching the manuscript or the experiments folder.

## Repos

- `phd_works` (this repo). The June–August replication was registered in commit 4085ab9 (merged into master in f701400 on 2026-10-01), extracted in d6d26c4 and evaluated in 1462d76.
- `2-Dissertation-Draft-Works/overleaf-github` is a submodule (`phd-dissertation-draft-en`; its name in `.gitmodules` is still `2-Dissertation-Draft/overleaf-github`, on purpose). Its work branch `claude/sweet-darwin-odfmmv` (latest 8a60745) carries all manuscript changes and is not yet merged into `main`; the submodule pointer here still points at 9459b33. Run `git submodule update --init` if the folder is empty.
- Experiment code and data live in `2-Dissertation-Draft-Works/wallet-reputation-experiments` (until 1 October 2026: `A-Skill-Programs/margin_rank`). All data sit under its `data/`: `1-raw-blockchain-logs/` and `2-processed-tables-and-evaluations/` are tracked (see its `.gitignore` for exclusions), and the summaries behind the thesis tables are copied to `3-published-results-for-thesis/` by `scripts/publish_results.py`. Its `README.md` and `data/README.md` describe every folder and file; `scripts/project_paths.py` holds the folder names and the old-to-new map.
- After pulling the folder move, run `scripts/finish_folder_move.py` (dry run, then `--apply`) on each checkout to move what git does not track (the `.venv`, files over 100 MiB, the submodule checkout) out of the old folders.

## Central claim, as it now stands

- The thesis asked whether adding ERC-20 allowance edges to PageRank improves on AWP, the transfer-only walk.
- **Spring holdout** (freeze 28 Feb, labels Mar–May): EndorseRank beat AWP on new approvals (+0.435) and on new senders (+0.102), both fixed in advance. The new-sender lead disappears when both walks weight each event once and against AWP in its published form (post hoc).
- **AWP fidelity:** the AWP of the thesis adapts Do, Do and Nguyen (2023): raw amounts instead of the bounded value transform, uniform restarts instead of activity-weighted ones. The published form is reported as a post hoc check (Table awp-paper-form) and as a registered sensitivity analysis.
- **C-PR (λ=0.5):** failed the 14 September rule (beat both single layers). Against AWP alone it gained +0.251 on new approvals in the spring, which was exploratory.
- **Registered replication** (freeze 31 May, labels Jun–Aug; decision needs F1–F3): F1 holds (+0.179 [0.132, 0.225]), F2 fails (−0.011 [−0.025, 0.003], lower bound below −0.02), F3 holds (+0.018 [0.011, 0.024]). **Decision not met**, so the thesis makes no improvement claim. F4 holds, F5 fails, F6 fails. Both sensitivity analyses give the same decision. EndorseRank's lead on new approvals replicated (+0.280); its lead on new senders did not.
- The cover title says "ENHANCED on-chain wallet reputation scoring". The rule below forbids changing it without the user; whether it still fits the result is the user's and the supervisors' decision.

## Remaining steps

1. The user and the supervisors read the results (Ch4 §4.8.2, Tables fresh-holdout, fresh-contrasts, fresh-traders) and decide on the title.
2. Merge the manuscript work branch into `main` of `phd-dissertation-draft-en` (Overleaf reads `main`), then update the submodule pointer here if wanted.
3. Report every coefficient as it came out; do not change λ, the labels, the cohorts, the 0.02 margin or the window (plan §6).

## Rules that must not be broken

- Do not change the cover or the table-of-contents titles. New content goes into unnumbered-in-TOC subsections (3.7.1/3.7.2, 4.8.1/4.8.2).
- Do not modify `1-Proposal`.
- Dissertation prose must not read as AI-written:
  - no inflated vocabulary, formulaic triplets or "not only…but also";
  - no em-dash chains, promotional tone or summary sign-offs;
  - keep sentences plain and concrete.
- Git:
  - files are CRLF on the user's Windows checkout, so stage with `git -c core.autocrlf=true add`;
  - author is abito <33889084+abitocodes@users.noreply.github.com>;
  - commit messages have a Korean conventional title and one block per hunk, `path[start:end]`, followed by `-` bullets;
  - never commit `.cursor/journey.md`.
- The registration files (`config/fresh_holdout_2026q3.yaml`, `docs/fresh_holdout_2026q3_plan.md`) are frozen; their hashes are in `data/3-published-results-for-thesis/registered-replication-2026-06-to-2026-08/extraction_manifest.json` (computed on the CRLF checkout). The registration still names the old data folders; `fresh_holdout.load_registration` translates them.
- Build: 193 pages, 0 errors, 0 undefined references at 8a60745. Check the build again after every edit.

## Other numbers you will need

- Raw degree baselines beat both walks in both windows: in-approve degree 0.711 (spring) and 0.613 (Jun–Aug) on new approvals; transfer in-degree 0.472 and 0.435 on new senders.
- Spender cohorts: 1,335 at 28 Feb (1,174 contracts, 161 EOAs by eth_getCode), 1,964 at 31 May.
- Trader cohorts: 4,227 matched wallets in the 28 Feb graph (1,860 with labels); 5,151 in the 31 May graph (1,402 with labels, 789 with a liquidation).
- June–August extraction: nine queries, about 1.04 TB billed; 163,553 approval logs, 1,013,023 transfer logs, 144,152 GMX closes.
