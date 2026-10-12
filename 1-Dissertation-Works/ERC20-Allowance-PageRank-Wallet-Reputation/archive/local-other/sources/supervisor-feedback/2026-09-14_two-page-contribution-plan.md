# Plan for growing the contribution to doctoral scale

Reply to Dr Attipoe's comment on the Contributions section (review of 28 August 2026): "Bring me a two-page plan for how the contribution grows to doctoral scale."

Taehong Kwon, 14 September 2026. The design, labels and success rules below were fixed before any of the new numbers were computed.

## 1. Where the contribution stands

The review describes the current thesis accurately. EndorseRank swaps the transfer edge for the ERC-20 allowance edge and runs an unmodified PageRank. Its strongest same-window result, agreement with allowance in-degree, is close to correlating a quantity with a smoothed copy of itself. The temporal holdout added after the review (scores frozen on 28 February 2026, labels from March to May) is out-of-window evidence, but the label is the same construct in the future tense: new approvals. AWP was never given the equivalent future-tense test on its own construct, so the holdout comparison is not yet like with like.

Three things are missing: a method that goes beyond the edge swap, a test in which neither construct is favoured by design, and a rule fixed in advance for what would count as an improvement.

## 2. What I am adding

### 2.1 A coupled PageRank over both edge types (C-PR)

The allowance graph and the transfer graph are two layers over one address set. C-PR runs a single random walk whose step from wallet u mixes the two layers:

    P[u, .] = lambda * P_approve[u, .] + (1 - lambda) * P_transfer[u, .]

P_approve and P_transfer are the row-normalised transition matrices of the two layers. If u has out-edges in only one layer, the walk uses that layer alone. If it has none, the step is a uniform jump, as in standard PageRank. Teleportation and damping (d = 0.85) are unchanged.

The operator nests both existing methods. On a shared node set, lambda = 1 is EndorseRank and lambda = 0 is AWP; on the empirical graphs the two layers differ by their one-hop neighbours, so the end points reproduce the single-layer rankings on the common wallets rather than the full score vectors. It is not a third edge swap; it is a one-parameter family whose end points are the two compared methods, and the question becomes whether an interior point beats either end. lambda = 0.5 is the primary setting and is fixed now. lambda = 0.25 and 0.75 are reported as sensitivity.

### 2.2 An ablation: endorsement-seeded PageRank (S-PR)

S-PR keeps the transfer walk but replaces the uniform teleport vector with the normalised EndorseRank score. Allowances decide where the walk restarts; transfers decide how it spreads. This is the TrustRank construction with allowance-derived seeds in place of hand-labelled ones. It isolates whether the value of the allowance edge lies in propagation or in seeding.

### 2.3 A future-tense label for the transfer construct

The holdout gains a second label: the number of distinct addresses that first send a transfer to the wallet between 1 March and 31 May 2026, having never done so up to the freeze date. It mirrors the existing label (new owner-spender approval pairs) on the transfer side. With both labels, each single-layer method is tested on its own construct in the future tense, and the hybrids are tested on both.

### 2.4 A same-window baseline for the holdout

RQ4 promised a comparison with the same-window allowance degree, and the table did not contain one. The holdout table gains a row for in-approve degree at the freeze date, so the increment of EndorseRank over the raw degree can be read directly, with a paired interval.

## 3. What counts as better (fixed before the run)

All intervals are 95 percent percentile intervals from a paired wallet bootstrap with 400 resamples and one shared index matrix, so every difference is a paired difference.

Primary criterion (temporal holdout, spender cohort, n = 1,335). C-PR at lambda = 0.5 must (a) be no worse than EndorseRank on future new approvals: the interval of tau(C-PR) - tau(EndorseRank) includes zero or lies above it; and (b) be better than AWP on future new transfer senders: the interval of tau(C-PR) - tau(AWP) lies entirely above zero.

Secondary criterion (same window, matched cohort, n = 5,521). C-PR must fall within the interval of the better single method on the transfer family and on the allowance family, and must exceed both single methods on the Sybil-adjusted stability family with intervals that exclude zero.

S-PR is judged by the same two criteria and is reported as an ablation whatever the outcome.

## 4. What the thesis will say in each case

If both criteria are met, the contribution is a method: a coupled operator that generalises the two compared methods and beats both on out-of-window labels for both constructs. The claims about EndorseRank alone stay as they are.

If only the primary criterion is met, the contribution is predictive: the coupled score anticipates future endorsement and future flow better than either single-layer score, while same-window agreement reflects the mixing. That is a result about the future, not about the input.

If the primary criterion fails, the thesis reports the null with intervals. The contribution then rests on the operator, the like-with-like holdout protocol, and the finding that the two edge types do not combine profitably at the settings tested. I would rather write that chapter than adjust lambda after seeing the labels, and the configuration file will show that lambda was fixed before the run.

## 5. Cost, and what does not carry over

C-PR walks on the union of both edge sets, about 14.7 thousand allowance edges plus 137 thousand transfer edges on the matched cohort. Its solve time will be close to AWP's, not EndorseRank's. The speed result (C1) belongs to EndorseRank only and will be stated that way. The coupled method is the accuracy option; EndorseRank is the cheap one. Both runtimes go into the benchmark table.

## 6. Timeline and deliverables

- 14 September: this plan; lambda grid, labels and criteria written into the versioned configuration.
- 14 to 16 September: C-PR and S-PR in the shared solver; the transfer holdout label, the degree baseline and the paired holdout contrasts; unit tests including the lambda = 0 and lambda = 1 identities; full evaluation run on the matched cohort, the spender cohort and the runtime benchmark; every table regenerated from the machine-readable summary, including the holdout table that was previously typed by hand.
- By 24 September: chapter revisions (RQ5, objective O5, claim C5, a methodology section for the coupled operator, results, discussion, conclusion); the machine-readable summaries committed to the public repository next to the code, with the revision hash cited in Appendix 8.1.

## 7. Outside this plan

The ethics clearance certificate is still pending. The declaration was submitted to Prof. Mnkandla, and I am waiting for the reference number and date. The placeholder in Section 3 and Appendix F will be filled when they arrive. The separate review memo (Supervisory_Review_Taehong_Thesis, Section 8 items 1 to 6) has not reached me; I will work through it as soon as it does.
