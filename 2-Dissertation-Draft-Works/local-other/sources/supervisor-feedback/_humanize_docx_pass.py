# -*- coding: utf-8 -*-
"""Apply humanized LaTeX prose to the review DOCX without adding comments.

Body replacements only (existing comment range markers kept). Taehong Kwon
comment *text* is rewritten in place; ids, threads and supervisor comments
are untouched. Does not run the Word reply pass.
"""
from __future__ import annotations

import io
import zipfile
from collections import Counter
from pathlib import Path

from lxml import etree

HERE = Path(__file__).resolve().parent
DOCX = HERE / "Taehong_Thesis_Reviewed_Moulla_Attipoe.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = {"w": W_NS}


def qn(tag: str) -> str:
    return "{%s}%s" % (W_NS, tag.split(":")[1])


def localname(el) -> str:
    return etree.QName(el).localname


def para_text(p) -> str:
    return "".join(t.text or "" for t in p.iter(qn("w:t")))


def comment_text(c) -> str:
    return "".join(t.text or "" for t in c.iter(qn("w:t")))


def replace_in_para(p, old: str, new: str) -> int:
    if not old or old == new:
        return 0
    count = 0
    once = old in new
    while count < 8:
        ts = [t for t in p.iter(qn("w:t")) if t.text]
        full = "".join(t.text for t in ts)
        k = full.find(old)
        if k < 0:
            return count
        if once and count:
            return count
        end = k + len(old)
        off = 0
        first = True
        for t in ts:
            a, b = off, off + len(t.text)
            off = b
            if b <= k or a >= end:
                continue
            lo, hi = max(k, a) - a, min(end, b) - a
            if first:
                t.text = t.text[:lo] + new + t.text[hi:]
                first = False
            else:
                t.text = t.text[:lo] + t.text[hi:]
        count += 1
        if once:
            return count
    return count


def span(p, start: str, end: str) -> str | None:
    t = para_text(p)
    i = t.find(start)
    if i < 0:
        return None
    j = t.find(end, i)
    if j < 0:
        return None
    return t[i : j + len(end)]


def replace_span(p, start: str, end: str, new: str) -> int:
    old = span(p, start, end)
    if old is None:
        return 0
    return replace_in_para(p, old, new)


def find_paras(body, needle: str) -> list:
    return [p for p in body.iter(qn("w:p")) if needle in para_text(p)]


def set_comment_text(c, new: str) -> None:
    ts = [t for t in c.iter(qn("w:t"))]
    if not ts:
        return
    ts[0].text = new
    ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for extra in ts[1:]:
        extra.text = ""


def has_markers(el) -> bool:
    tags = {
        "commentRangeStart",
        "commentRangeEnd",
        "commentReference",
        "bookmarkStart",
        "bookmarkEnd",
        "footnoteReference",
        "endnoteReference",
    }
    return any(localname(e) in tags for e in el.iter())


def clear_or_drop_para(p) -> str:
    if has_markers(p):
        for t in p.iter(qn("w:t")):
            t.text = ""
        return "cleared"
    parent = p.getparent()
    parent.remove(p)
    return "removed"


def apply_body(doc) -> list[str]:
    log: list[str] = []

    def one(needle: str, start: str, end: str, new: str) -> None:
        hits = find_paras(doc, needle)
        if len(hits) != 1:
            log.append(f"SKIP {needle!r}: {len(hits)} hits")
            return
        n = replace_span(hits[0], start, end, new)
        log.append(f"{'OK' if n else 'FAIL'} {needle!r} n={n}")
        print(log[-1], flush=True)

    def exact(needle: str, old: str, new: str) -> None:
        hits = find_paras(doc, needle)
        if len(hits) != 1:
            log.append(f"SKIP exact {needle!r}: {len(hits)} hits")
            return
        n = replace_in_para(hits[0], old, new)
        log.append(f"{'OK' if n else 'FAIL'} exact {needle!r} n={n}")
        print(log[-1], flush=True)

    # Abstract
    exact(
        "significance of the work is methodological",
        "The significance of the work is methodological and practical. Methodologically, it provides the first same-cohort comparison of an allowance-based and a transfer-based PageRank with confidence intervals, difference tests, a temporal holdout and a reproducible pipeline whose artefacts are versioned. Practically, it shows that a reputation score can be refreshed at roughly one eighth of the cost of the transfer-graph baseline while capturing a trust act that the baseline misses. For DeFi users, cheaper and more frequently refreshed authorization-aware scores lower the barrier to risk screening that today favours well-resourced actors; for protocol operators and regulators, an auditable score built on public approvals offers a transparent complement to opaque proprietary risk engines. The thesis also states clearly what EndorseRank does not do: it does not outperform AWP on transfer-hub detection, and its Sybil resistance depends on the economic cost of manufacturing approvals, which is modelled but not measured here.",
        "The comparison is the first same-cohort evaluation of an allowance-based and a transfer-based PageRank that reports confidence intervals, difference tests, a temporal holdout and a versioned pipeline. A reputation score can be refreshed at roughly one eighth of the cost of the transfer-graph baseline and still capture a trust act that the baseline misses. Cheaper, more frequently refreshed authorization-aware scores lower the barrier to risk screening that today favours well-resourced actors. For protocol operators and regulators, an auditable score built on public approvals is a transparent complement to opaque proprietary risk engines. EndorseRank does not outperform AWP on transfer-hub detection. Its Sybil resistance depends on the economic cost of manufacturing approvals, which is modelled but not measured here.",
    )
    one(
        "cheaper endorsement signal that already exists on every EVM chain",
        "every EVM chain",
        "can support a reputation score",
        "every EVM chain, the ERC-20 allowance an owner grants to a spender, can support a reputation score",
    )
    exact(
        "intended-construct check rather than as an external test",
        "so the allowance result is read as an intended-construct check rather than as an external test.",
        "so the allowance result is read as an intended-construct check, not as an external test.",
    )

    # Ch1
    exact(
        "has transformed how capital",
        "has transformed how capital is allocated on public blockchains, enabling lending, borrowing, and leveraged trading without traditional financial intermediaries",
        "changed how capital is allocated on public blockchains: lending, borrowing, and leveraged trading can run without traditional financial intermediaries",
    )
    exact(
        "it does not, however, model",
        "baseline; it does not, however, model explicit spending authorization, which is a distinct on-chain act recorded by ERC-20 allowances",
        "baseline. It does not model explicit spending authorization, a distinct on-chain act recorded by ERC-20 allowances",
    )
    exact(
        "merely different, or differently aligned",
        "Whether that semantic difference produces rankings that are merely different, or differently aligned with authorization and transfer checks, is an empirical question. This research answers that question on Arbitrum One",
        "Whether that semantic difference produces rankings that differ, and whether those rankings align differently with authorization and transfer checks, is an empirical question. This research answers it on Arbitrum One",
    )
    exact(
        "integrating ERC-20 allowance edges",
        "without temporal decay weighting---integrating ERC-20 allowance edges into PageRank for enhanced on-chain wallet reputation scoring.",
        "without temporal decay weighting.",
    )
    one(
        "integrating ERC-20 allowance edges",
        "without temporal decay weighting",
        "on-chain wallet reputation scoring.",
        "without temporal decay weighting.",
    )
    one(
        "originality does not lie",
        "Its originality does not lie",
        "out-of-window test.",
        "EndorseRank applies classical PageRank [15] unchanged. The contribution is the combination of a new edge construct, a same-cohort comparison with inference, and an out-of-window test.",
    )
    exact(
        "makes explicit that each method",
        "The design makes explicit that each method's own-construct agreement is partly mechanical, and it reports edge counts alongside runtimes so that the efficiency result (Claim C1) is read as an expected consequence of sparsity rather than as a contribution.",
        "The design states that each method's own-construct agreement is partly mechanical, and it reports edge counts alongside runtimes so that the efficiency result (Claim C1) is read as an expected consequence of sparsity.",
    )
    one(
        "makes explicit that each method",
        "The design makes explicit that each method",
        "rather than as a contribution.",
        "The design states that each method's own-construct agreement is partly mechanical, and it reports edge counts alongside runtimes so that the efficiency result (Claim C1) is read as an expected consequence of sparsity.",
    )
    exact(
        "rather than as external validation",
        "RQ2 is read as a construct-validity observation rather than as external validation.",
        "RQ2 is read as a construct-validity observation, not as external validation.",
    )
    exact(
        "rather than universal dominance",
        "Those results support an efficiency–alignment trade-off rather than universal dominance of either social method.",
        "Those results describe an efficiency–alignment trade-off: neither social method dominates both constructs.",
    )
    one(
        "rather than universal dominance",
        "Those results support",
        "either social method.",
        "Those results describe an efficiency–alignment trade-off: neither social method dominates both constructs.",
    )
    exact(
        "The next chapter begins",
        "The next chapter begins with the blockchain and DeFi primitives on which the allowance construct rests and ends with the research gap that this study is designed to close.",
        "Chapter 2 starts from the blockchain and DeFi primitives that the allowance construct uses and closes with the research gap this study is designed to close.",
    )

    # Ch2
    exact(
        "Critically, an allowance",
        "Critically, an allowance is an explicit authorization, not a completed transfer.",
        "An allowance is an explicit authorization, not a completed transfer.",
    )
    exact(
        "rather than black-box predictive scoring",
        "EndorseRank stays within interpretable graph propagation rather than black-box predictive scoring.",
        "EndorseRank stays within interpretable graph propagation. It is not a black-box predictive score.",
    )
    exact(
        "does not claim that PageRank scores are credit scores",
        "This research does not claim that PageRank scores are credit scores in the regulatory sense; it claims that allowance-based and transfer-based rankings can be compared rigorously on shared proxies.",
        "PageRank scores are not treated as credit scores in the regulatory sense. The claim is that allowance-based and transfer-based rankings can be compared rigorously on shared proxies.",
    )
    exact(
        "supporting a directed endorsement graph rather than transfer volume alone",
        "supporting a directed endorsement graph rather than transfer volume alone.",
        "which supports a directed endorsement graph in addition to transfer volume.",
    )
    exact(
        "expected consequence of edge sparsity rather than an algorithmic contribution",
        "any runtime difference is an expected consequence of edge sparsity rather than an algorithmic contribution.",
        "any runtime difference is an expected consequence of edge sparsity, not an algorithmic contribution.",
    )
    one(
        "underscore that allowances",
        "underscore that allowances are not neutral metadata",
        "they are capabilities.",
        "treat allowances as capabilities, not as neutral metadata.",
    )
    one(
        "not whether AWP",
        "The empirical question is not whether AWP",
        "cheaper signal.",
        "The empirical question is whether allowance edges yield a different, useful, and cheaper signal.",
    )
    exact(
        "The table highlights that",
        "The table highlights that EndorseRank’s novelty is not the use of PageRank per se, but the choice of latest-allowance endorsement edges as the primary social construct for DeFi wallets.",
        "Table 2.1 shows that EndorseRank’s novelty is the choice of latest-allowance endorsement edges as the primary social construct for DeFi wallets, not a new ranking algorithm.",
    )
    one(
        "The table highlights that",
        "The table highlights that",
        "DeFi wallets.",
        "Table 2.1 shows that EndorseRank’s novelty is the choice of latest-allowance endorsement edges as the primary social construct for DeFi wallets, not a new ranking algorithm.",
    )

    # Ch3
    exact(
        "not only in size but in composition",
        "The pool subsamples differ from the cohort not only in size but in composition:",
        "The pool subsamples differ from the cohort in size and in composition:",
    )

    # Ch4
    one(
        "What the evidence does license",
        "These two null results discipline the interpretation of the allowance family.",
        "and the reverse holds for transfer volume.",
        "These two null results bound the interpretation of the allowance family. EndorseRank is a global smoothing of spender in-approve degree, so its agreement with allowance proxies is an intended-construct check, not an external test. The between-method statement that follows is licensed: transfer centrality (AWP) carries no information about who receives spending authorisation, whereas endorsement centrality (EndorseRank) does, and the reverse holds for transfer volume. The within-method statement that EndorseRank “prefers” allowance over transfer signal is not licensed.",
    )
    exact(
        "Taken together, the damping",
        "Taken together, the damping and top-token checks support reading Claims C1–C3 as stable under parameter and token-mix perturbation, while the sample-definition check shows that the comparative structure, not the decimal values, is what travels across populations.",
        "The damping and top-token checks support reading Claims C1–C3 as stable under parameter and token-mix perturbation. The sample-definition check shows that the comparative structure, not the decimal values, is what travels across populations.",
    )
    one(
        "Taken together, the damping",
        "Taken together, the damping and top-token checks",
        "what travels across populations.",
        "The damping and top-token checks support reading Claims C1–C3 as stable under parameter and token-mix perturbation. The sample-definition check shows that the comparative structure, not the decimal values, is what travels across populations.",
    )
    one(
        "trade-off rather than a dominance: EndorseRank is the cheaper",
        "The efficiency and construct results combine into a trade-off rather than a dominance:",
        "longitudinal stability.",
        "The efficiency and construct results combine into a trade-off. EndorseRank is the cheaper method and the only one that aligns with authorisation checks, and on the spender holdout it predicts future new approvals where AWP does not (Table 4.13). AWP remains the stronger method for transfer-hub detection and longitudinal stability.",
    )
    exact(
        "None of the claims states that AWP is obsolete",
        "None of the claims states that AWP is obsolete. The contribution is a construct-aware comparison with quantified uncertainty:",
        "The claims do not retire AWP. They report a construct-aware comparison with quantified uncertainty:",
    )

    # Ch5
    exact(
        "rather than a universal ranking",
        "Tables 4.7 and 4.14 show construct-specific winners rather than a universal ranking:",
        "Tables 4.7 and 4.14 show construct-specific winners.",
    )
    exact(
        "rather than external validation",
        "rather than external validation.",
        ", not external validation.",
    )
    # The previous may have produced a double comma if the source already had a comma.
    # Fix after if needed.
    exact(
        "qualifies rather than extends the claim",
        "qualifies rather than extends the claim.",
        "qualifies the claim; it does not extend it.",
    )
    exact(
        "rather than folded into them",
        "Both are reported as limits on the claims rather than folded into them.",
        "Both are reported as limits on the claims. They are not folded into the objectives.",
    )
    exact(
        "not a single algorithm applied",
        "Graph-based reputation is therefore not a single algorithm applied to “the” transaction graph; it is a family of methods whose validity depends on which relationships are encoded as edges",
        "Graph-based reputation is therefore a family of methods whose validity depends on which relationships are encoded as edges",
    )
    one(
        "not a single algorithm applied",
        "Graph-based reputation is therefore not a single algorithm applied",
        "whose validity depends on which relationships are encoded as edges",
        "Graph-based reputation is therefore a family of methods whose validity depends on which relationships are encoded as edges",
    )
    exact(
        "scenario-dependent adoption rather than a single recommended score",
        "The empirical trade-off supports scenario-dependent adoption rather than a single recommended score.",
        "The empirical trade-off supports scenario-dependent adoption. It does not identify a single recommended score.",
    )
    exact(
        "None of these scenarios treats reputation",
        "None of these scenarios treats reputation as a substitute for collateral. The claim is narrower and more durable: a standardised, auditable, low-latency ordinal signal lowers the cost of counterparty differentiation.",
        "These scenarios do not treat reputation as a substitute for collateral. They treat a standardised, auditable, low-latency ordinal signal as a way to lower the cost of counterparty differentiation.",
    )
    exact(
        "lies less in its forecasting power",
        "lies less in its forecasting power than in its being public, comparable and cheap to recompute, so that many parties can reason from the same number while knowing how it can be gamed.",
        "is that it is public, comparable and cheap to recompute, so that many parties can reason from the same number while knowing how it can be gamed. Forecasting power is secondary.",
    )
    one(
        "significance of this research beyond",
        "The significance of this research beyond its immediate findings",
        "changes that distribution.",
        "Counterparty screening in DeFi is expensive and unevenly available. Well-resourced actors run proprietary risk engines over full transfer histories; retail users rely on informal signals or none. A score that can be refreshed at a fraction of the transfer-graph cost (Table 4.2) and that reads directly off the approvals users already grant lowers the resource barrier to systematic screening. Because approvals are also the mechanism through which most token-draining exploits operate (Section 2.8), a spender-centred endorsement score speaks to a risk that users face directly and that transfer volume does not capture.",
    )
    # Drop the now-duplicated "For users, ..." paragraph.
    hits = find_paras(doc, "For users, counterparty screening in DeFi is currently expensive")
    if len(hits) == 1:
        log.append("drop For-users para: " + clear_or_drop_para(hits[0]))
    else:
        log.append(f"SKIP drop For-users: {len(hits)} hits")
    exact(
        "continuous rather than periodic monitoring",
        "The efficiency result makes continuous rather than periodic monitoring economically feasible for smaller protocols.",
        "The efficiency result makes continuous monitoring economically feasible for smaller protocols that could not sustain periodic transfer-graph refresh at equal cost.",
    )
    exact(
        "That stands in contrast to the black-box",
        "That stands in contrast to the black-box decentralised credit scores whose due-process risks Packin and Lev-Aretz[2] describe, and it offers a template for the explainability that regulatory analyses of DeFi call for [63].",
        "That differs from the black-box decentralised credit scores whose due-process risks Packin and Lev-Aretz[2] describe, and it matches the explainability that regulatory analyses of DeFi call for [63].",
    )
    one(
        "stands in contrast to the black-box",
        "That stands in contrast to",
        "call for [63].",
        "That differs from the black-box decentralised credit scores whose due-process risks Packin and Lev-Aretz[2] describe, and it matches the explainability that regulatory analyses of DeFi call for [63].",
    )
    one(
        "Two limits on impact should be stated",
        "Two limits on impact should be stated with equal clarity.",
        "not that it is impossible.",
        "The evidence is from one chain and one six-month window, and it concerns the endorsement construct, not credit outcomes. Social benefit therefore depends on deployments that respect the construct boundary. Any reputation signal that gates value also invites strategic behaviour. The cost model of the next section shows where that behaviour is expensive; it does not show that the behaviour is impossible.",
    )
    exact(
        "the DeFi landscape is heterogeneous",
        "the DeFi landscape is heterogeneous in protocol design [8] and in market structure [1].",
        "DeFi venues differ in protocol design [8] and in market structure [1].",
    )

    # Ch6
    one(
        "Taken together, Claims",
        "Taken together, Claims",
        "about authorisation or about flow.",
        "Claims C1–C4 (Section 4.8) describe an efficiency–alignment trade-off. EndorseRank has lower PageRank cost, allowance-construct alignment and out-of-window evidence on future approvals. AWP has stronger transfer and longitudinal-stability alignment. Which to deploy depends on whether the operator’s question is about authorisation or about flow.",
    )
    exact(
        "What it has in fact established",
        "What it has in fact established, in the terms of the literature reviewed in Chapter 2, is the following.",
        "In the terms of the literature reviewed in Chapter 2, the following is established.",
    )
    one(
        "knowledge claim is not that",
        "Its knowledge claim is not that a new algorithm outperforms an old one; PageRank is used unchanged [15]. It is that the choice of edge determines",
        "while being weaker than the transfer-based score on flow and stability.",
        "PageRank is used unchanged [15]. The knowledge claim is that the choice of edge determines what an on-chain reputation score measures, that this can be shown with quantified uncertainty on one cohort, and that the allowance edge yields a score which is cheaper to refresh, distinct from the transfer-based score, aligned with its own construct and predictive of later endorsement, while weaker than the transfer-based score on flow and stability.",
    )
    exact(
        "rather than a single aggregate metric",
        "such designs should report construct-specific checks and time-split evidence rather than a single aggregate metric,",
        "such designs should report construct-specific checks and time-split evidence, not a single aggregate metric,",
    )
    one(
        "will not dissolve the need",
        "On-chain reputation will not dissolve the need",
        "two honest null results about its own internal structure.",
        "On-chain reputation does not remove the need for collateral in adversarial, pseudonymous markets [9]. It can make behavioural structure readable, and this research shows that the ranking depends on which edges are used. Transfers record economic flow; allowances record delegated authority. PageRank can rank either graph, but the same ranking cannot serve both constructs. EndorseRank uses the authorisation graph and reports its costs and benefits, including a time-split check of later approvals and two null within-method contrasts.",
    )
    exact(
        "The practical upshot is modest and actionable.",
        "The practical upshot is modest and actionable. A protocol or researcher who needs a fast, auditable score of who is trusted to spend has, on Arbitrum One data of the kind studied here, a credible instrument in EndorseRank. One who needs to find transfer hubs should still use AWP. One who wants to predict trading profit from social graphs alone is asking a question this thesis has shown to be outside what either instrument can answer.",
        "A protocol or researcher who needs a fast, auditable score of who is trusted to spend has, on Arbitrum One data of the kind studied here, a usable instrument in EndorseRank. One who needs to find transfer hubs should still use AWP. Predicting trading profit from social graphs alone is outside what either method can answer.",
    )

    # Appendix
    exact(
        "not automatically failure",
        "High within-construct τ supports interpretation; low cross-construct τ is not automatically failure—it may indicate discriminant validity.",
        "High within-construct τ supports interpretation. Low cross-construct τ is not automatically failure; it may indicate discriminant validity.",
    )
    one(
        "not automatically failure",
        "High within-construct",
        "may indicate discriminant validity.",
        "High within-construct τ supports interpretation. Low cross-construct τ is not automatically failure; it may indicate discriminant validity.",
    )
    exact(
        "rather than independent discovery",
        "indicate shared transfer structure rather than independent discovery.",
        "indicate shared transfer structure, not independent discovery.",
    )
    exact(
        "construct overlap rather than validation",
        "so any alignment between them is construct overlap rather than validation",
        "so any alignment between them is construct overlap, not validation",
    )
    exact(
        "rather than treating archive rows as peer-reviewed baselines",
        "These notes exist so that future researchers can decide which variants deserve full re-implementation rather than treating archive rows as peer-reviewed baselines.",
        "These notes exist so that future researchers can decide which variants deserve full re-implementation. Archive rows are not peer-reviewed baselines.",
    )
    exact(
        "broader landscape without diluting",
        "Archive tables remain available for readers who want the broader landscape without diluting the primary claims.",
        "Archive tables remain available for readers who want the seven-method and six-Aave matrices without mixing them into the primary claims.",
    )

    return log


def apply_comments(comments) -> list[str]:
    log = []
    repls = [
        (
            "methodological, practical and societal significance",
            "Rewritten (2026-09-12). The abstract now gives the background, the identified problem, the design (matched cohort n = 5,521, Kendall's tau with a paired bootstrap, temporal holdout, one timing protocol), the numerical results with intervals, and the benchmark against AWP. Same text as en/01-Intro/02-Abstract.tex.",
        ),
        (
            "Abstract rewritten to state background, problem, design, numerical results with intervals, benchmark against AWP and significance",
            "Taehong Kwon 2026-09-12: Abstract rewritten to state background, problem, design, numerical results with intervals, and the benchmark against AWP (comments 1, 3, 6, 2, 7). Citations and bold removed; AWP attributed to Do, Do and Nguyen (2023, IEEE RIVF). Source: en/01-Intro/02-Abstract.tex.",
        ),
        (
            "The text states that the originality lies in the construct, the inference design and the out-of-window test, not in the solver",
            "Contributions rewritten as three: (1) the latest-allowance edge construct, (2) a same-cohort comparison with bootstrap intervals and paired difference tests, (3) the temporal holdout of future new approvals. PageRank is used unchanged; the contribution is the construct, the inference design and the out-of-window test. The Research gap section (Chapter 2) shows that no reviewed method uses the allowance edge.",
        ),
        (
            "Bands deleted rather than referenced",
            "Bands were deleted, not kept as a cross-reference; see the reply to the adjacent comment.",
        ),
        (
            "that it is an intended-construct check rather than external validation",
            "Confronted directly. The allowance section now says that EndorseRank-allowance agreement is expected because the score is a global smoothing of allowance in-degree, that it is an intended-construct check, not external validation, and that the within-method difference against transfer is not significant (delta tau +0.022, interval includes 0). Trading-success and inverse-risk families are withdrawn from the main narrative.",
        ),
    ]
    for c in comments.iter(qn("w:comment")):
        if c.get(qn("w:author")) != "Taehong Kwon":
            continue
        t = comment_text(c)
        for needle, new in repls:
            if needle in t:
                set_comment_text(c, new)
                log.append(f"TK [{c.get(qn('w:id'))}] updated ({needle[:40]}…)")
                break
    return log


def leftover(doc) -> list[str]:
    needles = [
        "The significance of the work is methodological",
        "has transformed how capital",
        "it does not, however, model",
        "merely different, or differently aligned",
        "integrating ERC-20 allowance edges",
        "originality does not lie",
        "The table highlights that",
        "underscore that allowances",
        "Taken together, the damping",
        "Taken together, Claims",
        "The significance of this research beyond",
        "qualifies rather than extends",
        "broader landscape without diluting",
        "For users, counterparty screening",
        "Two limits on impact",
        "will not dissolve the need",
        "The practical upshot",
        "None of these scenarios",
        "None of the claims states",
        "What the evidence does license",
        "The next chapter begins",
        "Critically, an allowance",
        "not whether AWP is",
        "stands in contrast",
        "DeFi landscape is heterogeneous",
    ]
    body = "".join(para_text(p) for p in doc.iter(qn("w:p")))
    return [n for n in needles if n in body]


def main() -> None:
    raw = DOCX.read_bytes()
    zin = zipfile.ZipFile(io.BytesIO(raw))
    names = zin.namelist()
    doc = etree.fromstring(zin.read("word/document.xml"))
    comments = etree.fromstring(zin.read("word/comments.xml"))

    before_authors = Counter(
        c.get(qn("w:author")) for c in comments.iter(qn("w:comment"))
    )
    before_n = sum(before_authors.values())
    print("comments before", before_n, dict(before_authors), flush=True)

    for line in apply_body(doc):
        print(line)
    for line in apply_comments(comments):
        print(line)

    left = leftover(doc)
    print("leftover old phrases", left)

    after_authors = Counter(
        c.get(qn("w:author")) for c in comments.iter(qn("w:comment"))
    )
    after_n = sum(after_authors.values())
    print("comments after", after_n, dict(after_authors))
    if after_n != before_n:
        raise SystemExit(f"comment count changed {before_n} -> {after_n}")

    # Fix accidental ", not external" if we doubled a comma after "Meehl [22], not"
    for p in doc.iter(qn("w:p")):
        t = para_text(p)
        if ",, not external validation" in t:
            replace_in_para(p, ",, not external validation", ", not external validation")

    def dump(el) -> bytes:
        return etree.tostring(el, xml_declaration=True, encoding="UTF-8", standalone=True)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in names:
            if name == "word/document.xml":
                zout.writestr(name, dump(doc))
            elif name == "word/comments.xml":
                zout.writestr(name, dump(comments))
            else:
                zout.writestr(name, zin.read(name))
    data = buf.getvalue()
    zcheck = zipfile.ZipFile(io.BytesIO(data))
    assert zcheck.testzip() is None
    xmls = [n for n in zcheck.namelist() if n.endswith(".xml")]
    for n in xmls:
        raw_xml = zcheck.read(n)
        if b"ns0:" in raw_xml:
            raise SystemExit("ns0: in " + n)
    tmp = DOCX.with_suffix(".docx.humanize.tmp")
    tmp.write_bytes(data)
    tmp.replace(DOCX)
    print("wrote", DOCX, "bytes", len(data), flush=True)


if __name__ == "__main__":
    main()
