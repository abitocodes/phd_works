# -*- coding: utf-8 -*-
"""Build Taehong_Thesis_Reviewed_Moulla_Attipoe.replied.docx from the review original.

Red body edits are written in XML. Threaded replies are stamped with
desktop Word (win32com Replies.Add) so they nest under existing comments.
Hand-written commentRange marks alone are treated as new comments.
"""
from __future__ import annotations

import hashlib
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path

from lxml import etree

DIR = Path(__file__).resolve().parent
SRC = DIR / "Taehong_Thesis_Reviewed_Moulla_Attipoe.docx"
DST = DIR / "Taehong_Thesis_Reviewed_Moulla_Attipoe.replied.docx"

AUTHOR = "Taehong Kwon"
INITIALS = "TK"
COMMIT = "0c70518a35540c8b56be66b52452cb94ca3fb916"
REPO = "https://github.com/abitocodes/phd_works"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
W14 = "{http://schemas.microsoft.com/office/word/2010/wordml}"
W15 = "{http://schemas.microsoft.com/office/word/2012/wordml}"
W16CID = "{http://schemas.microsoft.com/office/word/2016/wordml/cid}"
CEX = "{http://schemas.microsoft.com/office/word/2018/wordml/cex}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

PARENT_ORDER = [
    "1",
    "3",
    "6",
    "2",
    "7",
    "14",
    "20",
    "62",
    "72",
    "74",
    "77",
    "78",
    "81",
    "82",
    "129",
    "128",
    "237",
    "240",
    "264",
    "283",
    "286",
    "288",
    "299",
    "310",
    "349",
    "378",
    "396",
]

REPLIES = {
    "1": "Rewrote the abstract in red to include background, the identified problem, method, numerical results, the AWP benchmark, and social impact. No numbered citations remain in the abstract.",
    "3": "Removed the numbered references from the abstract. Citations now begin in the body.",
    "6": "Removed bold from EndorseRank in the abstract. It is now plain body text.",
    "2": "Agreed. Do and Do (2023, IJSI) is PageRank and HodgeRank. AWP is the separate IEEE RIVF paper (Do, Do Van Dung, and Nguyen, 2023; doi:10.1109/rivf60135.2023.10471809). I split that attribution at the first AWP definition and added the RIVF item to References. A full in-text pass (every fused “Do et al. = AWP”) is deferred until after the meeting.",
    "7": "Dropped trading-success proxies and the GF-PR ceiling from the claims. GMX remains a sampling frame only. The external check is now a temporal holdout of future new owner–spender approvals.",
    "14": "Removed GF-PR / SRQ1 / SC1 from the research claims. Trading-success alignment is not used as evidence.",
    "20": "Split this opening paragraph so each claim has one source: [53] for DeFi intermediation; [48] for the absence of conventional credit histories. A document-wide cluster pass is deferred.",
    "62": "Kept the 2.105 s / 8.9× measurement. Added in red that the speedup is the expected O(|E|) consequence of approval sparsity, that the solver matches AWP, and that C1 is demoted from a headline contribution.",
    "72": "Inserted a Research objectives section (four objectives, mapped to RQ1–RQ4) immediately before Research questions. Chapter 5 mapping of each objective is deferred until after the meeting.",
    "74": "Re-posed RQ4 as a temporal holdout: t1 scores versus t2 new owner–spender approvals on inbound spenders, not transfer versus trading-success.",
    "77": "Rewrote the contribution paragraph: the claim is latest-allowance edges, same-window allowance versus transfer checks, and a temporal holdout of future new approvals—not a new ranking algorithm and not a five-proxy trading-success contest.",
    "78": "Implemented a temporal holdout rather than another same-window proxy. Scores freeze at 28 February 2026; labels are new owner–spender approvals in March–May 2026 on t1 inbound spenders (n = 1,335). EndorseRank Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529); AWP = 0.044. That is the same endorsement construct in the future tense, with CIs. It is not a trading-profit, liquidation, or malicious-spender result. Method is still stock PageRank; the contribution is the time-split check, not a new solver.",
    "81": "Added the public repository URL, commit 0c70518a35540c8b56be66b52452cb94ca3fb916, the versioned config path, and the machine-readable summary as the table source. I can provide an anonymised archive if required.",
    "82": "Removed the restated 0.316 / 0.355 / 0.534 / 8.9× list from this Contributions sentence and pointed back to Chapter 4. A full de-duplication pass is deferred.",
    "129": "Deleted the uncited 0.10 / 0.35 bands at this heading. I will not invent a precedent. Interpretation will use same-cohort contrasts and, after the meeting, bootstrap intervals.",
    "128": "Same change as the paired comment: the bands are deleted rather than given a fabricated citation.",
    "237": "Acknowledged. This working copy does not add bootstrap CIs or tests of the difference between correlations. I noted that gap in red at this bullet. I will compute them after the meeting.",
    "240": "Clarified in red that the primary benchmark protocol is five runs and that robustness / Appendix 8.1 use three-run averages. I have not changed the printed means.",
    "264": "Removed the “exemption or clearance” wording. I do not have the certificate number/date in hand, so I have not invented them. I will cite the exact Unisa (SoC/CAES) file and append the certificate once confirmed.",
    "283": "Explained in red: 2.105/18.711 is Table 4.2 (primary matched-cohort benchmark); 2.913/21.383 is Table 4.4 d = 0.85 (damping robustness); 2.544/22.757 is Table 8.4 (extended-baseline matrix). Different experiments. Printed means unchanged.",
    "286": "Explained in red: 10.4× is Table 4.3 (primary scaling, 1.178 s vs 12.277 s). 8.96× is Table 4.6 (sample-size sweep). Same n and seed, not the same experiment. Raw logs after the meeting.",
    "288": "Acknowledged in red: n = 10,000 is a SHA256 subsample (|E| = 7,067). Cohort and full pool both show 14,727 EndorseRank edges because the evaluation-wallet subgraph is fixed, so this design does not scale the quantity that drives PageRank cost.",
    "299": "Rewrote this paragraph in red as sample-definition sensitivity, not robustness. Primary sample remains n = 5,521. The 0.2 swing is no longer described as stability.",
    "310": "I keep the honesty you asked for: same-window allowance tau = 0.355 is an intended-construct check, not an external test (AWP is -0.030). I dropped trading-success 0.096 and inverse-risk 0.035 from the claims. The external check is now a holdout of future new approvers on spenders: EndorseRank tau = 0.479 (CI 0.426–0.529) versus AWP 0.044. I do not sell drain, revoke, or Aave liquidation as successes.",
    "349": "Collapsed this subsection to one short paragraph and removed the Akerlof / Graham–Dodd / Basu / Fama–French / Healy–Wahlen cluster from this location.",
    "378": "Acknowledged: major revision before examination. This working copy now drops trading-success / GF-PR claims and reports the spender holdout (EndorseRank tau = 0.479, CI 0.426–0.529). Still open: ethics certificate, raw logs, and a full LaTeX–Word cleanup. I do not have Supervisory_Review_Taehong_Thesis.",
    "396": "Added the verified 2023 IEEE RIVF AWP paper after Do and Do (2023). A broader currency pass on older field references is deferred; I will not add unverified replacements.",
}


def qn(local: str) -> str:
    return f"{W}{local}"


def para_text(p) -> str:
    return "".join(t.text or "" for t in p.iter(qn("t")))


def pstyle(p) -> str:
    ppr = p.find(qn("pPr"))
    if ppr is None:
        return ""
    ps = ppr.find(qn("pStyle"))
    return ps.get(qn("val")) if ps is not None else ""


def first_text_run(p):
    for r in p.findall(qn("r")):
        if r.find(qn("t")) is not None and r.find(qn("commentReference")) is None:
            return r
    return None


def make_red_run(text: str, sample_r=None):
    r = etree.Element(qn("r"))
    if sample_r is not None and sample_r.find(qn("rPr")) is not None:
        rPr = deepcopy(sample_r.find(qn("rPr")))
        r.append(rPr)
    else:
        rPr = etree.SubElement(r, qn("rPr"))
    color = rPr.find(qn("color"))
    if color is None:
        color = etree.SubElement(rPr, qn("color"))
    for attr in list(color.attrib):
        color.attrib.pop(attr)
    color.set(qn("val"), "FF0000")
    bold = rPr.find(qn("b"))
    if bold is not None:
        rPr.remove(bold)
    t = etree.SubElement(r, qn("t"))
    if text[:1].isspace() or (text[-1:].isspace() if text else False):
        t.set(XML_SPACE, "preserve")
    t.text = text
    return r


def is_marker(el) -> bool:
    tag = etree.QName(el).localname
    if tag in {"commentRangeStart", "commentRangeEnd", "bookmarkStart", "bookmarkEnd"}:
        return True
    if tag == "r" and (
        el.find(qn("commentReference")) is not None or el.find(qn("annotationRef")) is not None
    ):
        return True
    return False


def replace_para_text(p, text: str) -> None:
    if p is None:
        return
    sample = first_text_run(p)
    starts, tails = [], []
    for child in list(p):
        tag = etree.QName(child).localname
        if tag == "pPr":
            continue
        if tag == "commentRangeStart" or tag == "bookmarkStart":
            starts.append(child)
        elif is_marker(child):
            tails.append(child)
        else:
            p.remove(child)
    run = make_red_run(text, sample)
    ppr = p.find(qn("pPr"))
    if tails:
        tails[0].addprevious(run)
    elif ppr is not None:
        ppr.addnext(run)
    else:
        p.insert(0, run)
    # starts already remain in the tree; if they were after removed runs, they stay.
    # Ensure starts precede the new run.
    for s in reversed(starts):
        if s.getparent() is p:
            p.remove(s)
        if ppr is not None:
            ppr.addnext(s)
        else:
            p.insert(0, s)


def append_red(p, text: str) -> None:
    sample = first_text_run(p)
    run = make_red_run(text, sample)
    end = None
    for child in p:
        if etree.QName(child).localname == "commentRangeEnd":
            end = child
            break
    if end is not None:
        end.addprevious(run)
    else:
        p.append(run)


def find_para(paras, pred):
    for p in paras:
        if pred(p):
            return p
    raise KeyError("paragraph not found")


def para_has_comment(p, cid: str) -> bool:
    for el in p.iter():
        tag = etree.QName(el).localname
        if tag in {"commentRangeStart", "commentRangeEnd", "commentReference"}:
            if el.get(qn("id")) == cid:
                return True
    return False


def parent_para_id(comment, ext_ids: set[str]) -> str:
    """Return the parent thread id Word already registered in commentsExtended.

    [MS-DOCX] commentEx/@paraId is the last paragraph of the associated comment.
    Multi-paragraph supervisor comments (14, 128, 240) have a different first
    paraId; paraIdParent must match the commentsEx entry, not the first para.
    """
    pids = []
    for p in comment.findall(qn("p")):
        pid = p.get(f"{W14}paraId")
        if pid:
            pids.append(pid)
    ext_upper = {x.upper() for x in ext_ids if x}
    for pid in reversed(pids):
        if pid.upper() in ext_upper:
            return pid
    if pids:
        return pids[-1]
    raise ValueError(f"no paraId on comment {comment.get(qn('id'))}")


def add_person(people_root) -> None:
    for person in people_root:
        if person.get(f"{W15}author") == AUTHOR:
            return
    person = people_root.makeelement(f"{W15}person", {f"{W15}author": AUTHOR})
    people_root.append(person)


def new_para_like(template, text: str):
    p = etree.Element(qn("p"))
    ppr = template.find(qn("pPr"))
    if ppr is not None:
        p.append(deepcopy(ppr))
    p.append(make_red_run(text, first_text_run(template)))
    return p


def rewrite_zip(path: Path, updates: dict[str, bytes]) -> None:
    tmp = path.with_name(path.stem + ".__tmp.docx")
    try:
        with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(
            tmp, "w", compression=zipfile.ZIP_DEFLATED
        ) as zout:
            for item in zin.infolist():
                data = updates.get(item.filename, zin.read(item.filename))
                zout.writestr(item, data)
        tmp.replace(path)
    except PermissionError:
        alt = DIR / "Taehong_Thesis_Reviewed_Moulla_Attipoe.replied.unlocked.docx"
        if tmp.exists():
            tmp.replace(alt)
        raise PermissionError(str(alt))


def apply_body(doc) -> None:
    body = doc.find(qn("body"))
    paras = [p for p in body if etree.QName(p).localname == "p"]

    p39 = find_para(paras, lambda p: para_has_comment(p, "2"))
    replace_para_text(
        p39,
        "Decentralized finance protocols allocate capital among pseudonymous wallets and therefore need on-chain reputation scores that can be refreshed often and checked against public ledger signals. The identified problem is that transfer-graph reputation is costly to refresh and does not encode explicit spending authorization. This study introduces EndorseRank, PageRank on latest ERC-20 allowance edges on Arbitrum One, and compares it with Adaptive Weighted PageRank (AWP) on a matched wallet cohort (n = 5,521) defined by GMX activity as a sampling frame only.",
    )

    p40 = find_para(
        paras,
        lambda p: para_text(p).startswith("EndorseRank runs") and "8.9" in para_text(p),
    )
    replace_para_text(
        p40,
        "On the matched cohort, EndorseRank completes PageRank in 2.105 s versus 18.711 s for AWP (approximately 8.9 times faster). Allowance-family alignment is an intended-construct check, not an external test: EndorseRank mean Kendall tau = 0.355, while AWP is near zero (-0.030). AWP remains closer to transfer proxies (tau = 0.534 versus 0.333). Inter-method rank correlation (tau = 0.316) indicates overlapping but not interchangeable rankings. On the holdout spender cohort (n = 1,335), EndorseRank aligns with future new approvers at Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529); AWP is 0.044. That is not a prediction of trading profit, liquidation, or malicious spenders.",
    )

    p41 = find_para(
        paras,
        lambda p: para_text(p).startswith("ank wall-clock time"),
    )
    replace_para_text(
        p41,
        "On an expanded wallet pool (N = 31,612), EndorseRank remains approximately 10.4 times faster than AWP at n = 10,000 and 9.4 times faster at full pool size. Damping, top-token, and sample-definition checks leave the allowance-versus-transfer trade-off unchanged.",
    )

    p42 = find_para(
        paras,
        lambda p: para_text(p).startswith("partially overlapping yet construct-distinct"),
    )
    replace_para_text(
        p42,
        "This abstract names Adaptive Weighted PageRank as the transfer-graph baseline and does not treat Do and Do (2023) as the AWP source; that bibliographic split is stated in Chapter 1.",
    )

    p43 = find_para(
        paras,
        lambda p: para_text(p).startswith("On an expanded wallet pool"),
    )
    replace_para_text(
        p43,
        "The social relevance of the study is a cheaper, auditable ordinal signal that protocols can recompute from public logs when screening counterparties, without treating the score as a profit forecast or a substitute for collateral.",
    )

    p44 = find_para(paras, lambda p: para_has_comment(p, "7"))
    replace_para_text(
        p44,
        "GMX V2 activity defines the matched sample (at least three PositionDecrease closes). It is not a trading-success test. Trading-success, inverse-risk, liquidation, and GF-PR alignments are not claims.",
    )

    p178 = find_para(
        paras,
        lambda p: "Do et al.[16] adapt PageRank to Ethereum transfer graphs" in para_text(p),
    )
    replace_para_text(
        p178,
        "Do and Do [16] apply PageRank and HodgeRank to Ethereum transfer graphs and validate scores against inbound transfer activity. A separate IEEE paper (Do, Do Van Dung, and Nguyen, 2023, RIVF) defines Adaptive Weighted PageRank (AWP) on value-weighted, time-decayed transfer edges. In this draft I treat [16] as the PageRank/HodgeRank and transfer-proxy source, and the RIVF paper as the AWP source. A full in-text correction of remaining fused citations is deferred until after the supervisory meeting.",
    )

    p166 = find_para(paras, lambda p: para_has_comment(p, "20"))
    replace_para_text(
        p166,
        "Decentralized Finance (DeFi) has transformed how capital is allocated on public blockchains, enabling lending, borrowing, and leveraged trading without traditional financial intermediaries [53]. Yet most credit-like interactions remain highly collateralized because protocols cannot rely on off-chain identity systems or conventional credit histories [48]. In a pseudonymous environment, the operational challenge is to allocate capital safely when counterparties are addresses rather than identified persons.",
    )

    p193 = find_para(paras, lambda p: para_has_comment(p, "62"))
    append_red(
        p193,
        " That 8.9 times speedup is an expected consequence of sparsity: the allowance graph has about nine times fewer edges because approvals are rarer on-chain events than transfers, and PageRank is O(|E|). The solver is the same as AWP’s. I therefore keep the measurement but demote Claim C1 from a headline contribution to a documented consequence of the data.",
    )

    p302 = find_para(paras, lambda p: para_has_comment(p, "74"))
    replace_para_text(
        p302,
        "RQ4. After scores are frozen at 28 February 2026, does EndorseRank predict new owner–spender approvals in March–May 2026 on t1 inbound spenders more strongly than AWP? This is a time-split test of the endorsement construct, not a trading-success contest.",
    )

    p308 = find_para(paras, lambda p: para_has_comment(p, "78"))
    replace_para_text(
        p308,
        "The originality claimed here is not a new ranking algorithm. EndorseRank applies stock PageRank to latest ERC-20 allowance edges, compares that score with AWP on same-window allowance and transfer checks, and tests whether t1 scores predict t2 new approvals on inbound spenders. Whether that time-split check is a sufficient doctoral contribution is for the supervisory meeting; this draft only makes the present scope explicit.",
    )

    p313 = find_para(paras, lambda p: para_has_comment(p, "81"))
    append_red(
        p313,
        f" Repository: {REPO} (commit {COMMIT}). Versioned configuration: A-Skill-Programs/margin_rank/config/margin_config.yaml. Tables are transcribed from the pipeline’s machine-readable evaluation summary. An anonymised archive can be supplied if a private snapshot is required.",
    )

    p315 = find_para(paras, lambda p: para_has_comment(p, "82"))
    replace_para_text(
        p315,
        "Empirically, the primary comparison is reported once in Chapter 4 (inter-method rank correlation, allowance alignment, transfer alignment, and matched-cohort runtime). Those Chapter 4 quantities are not restated here.",
    )

    p316 = find_para(
        paras,
        lambda p: para_text(p).startswith("on the matched cohort, with pool scaling"),
    )
    replace_para_text(
        p316,
        "Pool-scaling runtimes are likewise those already established in Chapter 4 and are not repeated as headline numbers here.",
    )

    p492 = find_para(paras, lambda p: para_has_comment(p, "129"))
    replace_para_text(
        p492,
        "There is no universal cutoff for strong Kendall tau in blockchain ranking studies. This draft therefore drops the uncited 0.10 / 0.35 operational bands.",
    )
    p493 = None
    for p in paras:
        if para_has_comment(p, "128") and not para_has_comment(p, "129"):
            p493 = p
            break
    if p493 is None:
        raise KeyError("para 493 not found")
    replace_para_text(
        p493,
        "Interpretation will rest on relative comparisons on the same cohort and, after the meeting, on bootstrap confidence intervals. I do not invent a cited precedent for the deleted bands.",
    )

    p998 = find_para(paras, lambda p: para_has_comment(p, "237"))
    append_red(
        p998,
        " This working copy still lacks bootstrap confidence intervals and tests of the difference between correlations. Until those are added, statements that one tau is meaningfully larger than another are unsupported.",
    )

    p1006 = find_para(paras, lambda p: para_has_comment(p, "240"))
    append_red(
        p1006,
        " The primary matched-cohort benchmark protocol uses five independent runs. Robustness sweeps and Appendix 8.1 report three-run averages. Table 4.2’s “three runs” footnote records that table’s protocol; I will reconcile the printed protocol statements after the meeting and do not alter the means here.",
    )

    p1058 = find_para(paras, lambda p: para_has_comment(p, "264"))
    replace_para_text(
        p1058,
        "This study uses exclusively publicly available blockchain data and does not intervene with human participants. Institutional ethics review was completed before empirical data collection. The exact Unisa (SoC/CAES) certificate number and date will be cited here, and the certificate appended, once I have confirmed the file; those identifiers are not invented in this draft.",
    )

    p1191 = find_para(paras, lambda p: para_has_comment(p, "283") and "8.9" in para_text(p))
    append_red(
        p1191,
        " These 2.105 s / 18.711 s figures are the primary matched-cohort benchmark (Table 4.2). They are not the same experiment as the d = 0.85 row of Table 4.4 (2.913 s / 21.383 s; damping robustness) or Table 8.4 (2.544 s / 22.757 s; archived extended-baseline matrix). Printed means are unchanged.",
    )

    p1204 = find_para(paras, lambda p: para_has_comment(p, "286"))
    append_red(
        p1204,
        " The 10.4 times figure is from the primary runtime-scaling table (Table 4.3: 1.178 s versus 12.277 s). Table 4.6 is a different experiment on the same n and seed (alignment plus runtime under the sample-size sweep) and reports speedup 8.960. The two tables must not be read as one experiment.",
    )

    p1210 = find_para(paras, lambda p: para_has_comment(p, "288"))
    append_red(
        p1210,
        " The n = 10,000 stage is a SHA256 subsample, so EndorseRank |E| = 7,067 need not lie between the matched-cohort and full-pool counts. Matched cohort and full pool both show 14,727 EndorseRank edges because the reputation subgraph among evaluation wallets is fixed; expanding the node set without new edges among scored wallets does not scale the quantity that drives PageRank cost. That is a limitation of this scaling design.",
    )

    p1304 = find_para(paras, lambda p: para_has_comment(p, "299"))
    replace_para_text(
        p1304,
        "At n = 10,000 and N = 31,612, EndorseRank continues to lead on allowance and AWP on transfer, with EndorseRank speedups of approximately 9.0 times and 9.9 times. Absolute tau values differ from the matched-cohort figures (allowance 0.355 to 0.555; transfer 0.534 to 0.789). That movement is sample-definition sensitivity, not robustness. The primary sample remains the matched cohort (n = 5,521).",
    )
    p1307 = find_para(
        paras,
        lambda p: para_text(p).startswith("Collectively, the robustness checks support"),
    )
    replace_para_text(
        p1307,
        "Collectively, these checks show that the comparative pattern (EndorseRank faster; EndorseRank wins on allowance; AWP wins on transfer) persists when the sample definition changes. They do not show that absolute tau is stable. A 0.2 swing is not described as robustness.",
    )

    p1386 = find_para(paras, lambda p: para_has_comment(p, "310"))
    replace_para_text(
        p1386,
        "This pattern must be read honestly. EndorseRank is essentially a global smoothing of allowance in-degree, so correlating it with allowance in-degree is close to correlating a quantity with itself (tau = 0.355). I do not call that an external test. The out-of-window check is future new approvers on spenders: EndorseRank tau = 0.479 (CI 0.426–0.529) versus AWP 0.044. Trading-success and inverse-risk alignments are dropped from the claims.",
    )

    # P/E collapse
    pe_h = find_para(
        paras,
        lambda p: para_text(p).strip() == "From valuation multiples to reputation multiples",
    )
    nxt = pe_h.getnext()
    first_body = None
    to_remove = []
    cur = nxt
    while cur is not None and etree.QName(cur).localname == "p":
        st = pstyle(cur)
        if st.startswith("Heading"):
            break
        if first_body is None and para_text(cur).strip():
            first_body = cur
        elif first_body is not None:
            to_remove.append(cur)
        cur = cur.getnext()
    if first_body is None:
        raise KeyError("P/E body not found")
    replace_para_text(
        first_body,
        "A short analogy only: like price-to-earnings ratios, on-chain reputation scores are useful mainly as a shared, auditable ordinal language rather than as return or profit forecasts. This draft does not rely on the extended finance-theory citation cluster (Akerlof, Graham and Dodd, Basu, Fama–French, Healy and Wahlen) to advance the empirical claims; those citations are removed from this subsection.",
    )
    for old in to_remove:
        body.remove(old)

    # GF-PR caveat after abbreviations row
    p14 = find_para(paras, lambda p: para_has_comment(p, "14"))
    caveat = new_para_like(
        p39,
        "Note: GF-PR and trading-success families are excluded from the research claims. The external check is the temporal holdout of future new approvals.",
    )
    p14.addnext(caveat)

    # Research objectives before Research questions
    rq_h = find_para(
        paras,
        lambda p: para_text(p).strip() == "Research questions" and pstyle(p) == "Heading2",
    )
    obj_h = new_para_like(rq_h, "Research objectives")
    # heading should not be forced red-only if we cloned Heading2 — keep style, still red as requested for new text
    obj_body = new_para_like(
        p39,
        "Four objectives are derived from the problem statement and map onto the primary research questions. O1: establish whether EndorseRank and AWP produce distinct wallet orderings on one Arbitrum cohort (RQ1). O2: compare contemporaneous allowance and transfer checks (RQ2). O3: measure computational cost of EndorseRank versus AWP at equal n (RQ3). O4: test whether t1 scores predict t2 new owner–spender approvals on inbound spenders (RQ4).",
    )
    rq_h.addprevious(obj_h)
    rq_h.addprevious(obj_body)

    # AWP IEEE reference after Do & Do 2023
    do_ref = find_para(
        paras,
        lambda p: para_text(p).startswith("Do, H., & Do, T. (2023)"),
    )
    awp_ref = new_para_like(
        do_ref,
        "Do, T., Do Van Dung, & Nguyen, L. (2023). On-chain reputation ranking by Adaptive Weighted PageRank. In Proceedings of the 2023 RIVF International Conference on Computing and Communication Technologies (pp. 318–323). IEEE. doi:10.1109/rivf60135.2023.10471809",
    )
    do_ref.addnext(awp_ref)


def norm_comment_text(s: str) -> str:
    return " ".join((s or "").replace("\r", " ").replace("\x07", " ").split())


def xml_id_by_text(comments_root) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for c in comments_root.findall(qn("comment")):
        if c.get(qn("author")) == AUTHOR:
            continue
        text = "".join(t.text or "" for t in c.iter(qn("t")))
        mapping[norm_comment_text(text)] = c.get(qn("id"))
    return mapping


def match_parent_id(word_text: str, id_by_text: dict[str, str]) -> str | None:
    wt = norm_comment_text(word_text)
    if wt in id_by_text:
        return id_by_text[wt]
    for xt, pid in id_by_text.items():
        if wt[:50] and (wt[:50] in xt or xt[:50] in wt):
            return pid
    return None


def stamp_replies_with_word(path: Path, id_by_text: dict[str, str]) -> None:
    """Let Word create real threaded replies (COM Replies.Add).

    A reply that also has commentRangeStart/End in document.xml is a new
    root balloon in this Word build. Replies.Add after those marks are
    gone is what the Comments pane nests.
    """
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    doc = None
    old_name = old_init = None
    try:
        try:
            old_name = word.UserName
            old_init = word.UserInitials
        except Exception:
            old_name = old_init = None
        try:
            word.UserName = AUTHOR
            word.UserInitials = INITIALS
        except Exception:
            pass
        try:
            doc = word.Documents.Open(str(path), False, False, False)
        except Exception as exc:
            raise PermissionError(
                f"Word could not open {path}. Close the file in Word and rerun. ({exc})"
            ) from exc
        parents = []
        for i in range(1, doc.Comments.Count + 1):
            c = doc.Comments(i)
            try:
                if c.Ancestor is not None:
                    continue
            except Exception:
                pass
            if getattr(c, "Author", "") == AUTHOR:
                continue
            if getattr(c, "Replies", None) is not None and c.Replies.Count >= 1:
                continue
            parents.append(c)
        if len(parents) != 27:
            raise RuntimeError(f"expected 27 parent comments, got {len(parents)}")
        added = 0
        for c in parents:
            parent_id = match_parent_id(c.Range.Text, id_by_text)
            if parent_id is None or parent_id not in REPLIES:
                raise KeyError(
                    f"unmatched Word comment: {norm_comment_text(c.Range.Text)[:80]!r}"
                )
            reply = c.Replies.Add(c.Range, REPLIES[parent_id])
            try:
                reply.Author = AUTHOR
                reply.Initial = INITIALS
            except Exception:
                pass
            added += 1
        if added != 27:
            raise RuntimeError(f"added {added} replies, expected 27")
        doc.Save()
        doc.Close(False)
        doc = None
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
        if old_name is not None:
            try:
                word.UserName = old_name
                word.UserInitials = old_init
            except Exception:
                pass
        word.Quit()
        pythoncom.CoUninitialize()


def strip_independent_reply_balloons(path: Path) -> dict[str, str]:
    """Drop Taehong Kwon comments that were stored as their own balloons.

    Replies must not keep commentRangeStart/End/commentReference in the body.
    After this, only supervisor root comments remain; Word Replies.Add
    recreates the 27 answers as nested replies.
    """
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        doc = etree.fromstring(z.read("word/document.xml"))
        comments = etree.fromstring(z.read("word/comments.xml"))
        ext = etree.fromstring(z.read("word/commentsExtended.xml"))
        cids = (
            etree.fromstring(z.read("word/commentsIds.xml"))
            if "word/commentsIds.xml" in names
            else None
        )
        cex = (
            etree.fromstring(z.read("word/commentsExtensible.xml"))
            if "word/commentsExtensible.xml" in names
            else None
        )

    tk_ids: set[str] = set()
    tk_pids: set[str] = set()
    for c in comments.findall(qn("comment")):
        if c.get(qn("author")) != AUTHOR:
            continue
        tk_ids.add(c.get(qn("id")))
        for p in c.findall(qn("p")):
            pid = p.get(f"{W14}paraId")
            if pid:
                tk_pids.add(pid.upper())
    if len(tk_ids) != 27:
        raise RuntimeError(f"expected 27 Taehong Kwon comments to strip, got {len(tk_ids)}")

    tk_durable: set[str] = set()
    if cids is not None:
        for el in cids:
            pid = (el.get(f"{W16CID}paraId") or "").upper()
            if pid in tk_pids:
                dur = el.get(f"{W16CID}durableId")
                if dur:
                    tk_durable.add(dur.upper())

    for tag in ("commentRangeStart", "commentRangeEnd", "commentReference"):
        for el in list(doc.iter(qn(tag))):
            if el.get(qn("id")) not in tk_ids:
                continue
            parent = el.getparent()
            if parent is None:
                continue
            parent.remove(el)
            if tag == "commentReference":
                leftover = [
                    ch
                    for ch in parent
                    if etree.QName(ch).localname != "rPr"
                ]
                if not leftover and parent.getparent() is not None:
                    parent.getparent().remove(parent)

    for c in list(comments.findall(qn("comment"))):
        if c.get(qn("id")) in tk_ids:
            comments.remove(c)

    for el in list(ext):
        pid = (el.get(f"{W15}paraId") or "").upper()
        if pid in tk_pids:
            ext.remove(el)

    if cids is not None:
        for el in list(cids):
            pid = (el.get(f"{W16CID}paraId") or "").upper()
            if pid in tk_pids:
                cids.remove(el)

    if cex is not None:
        for el in list(cex):
            dur = (el.get(f"{CEX}durableId") or "").upper()
            if dur in tk_durable:
                cex.remove(el)

    mapping = xml_id_by_text(comments)
    if len(mapping) != 27:
        raise RuntimeError(f"expected 27 supervisor comments after strip, got {len(mapping)}")

    updates = {
        "word/document.xml": serialize(doc),
        "word/comments.xml": serialize(comments),
        "word/commentsExtended.xml": serialize(ext),
    }
    if cids is not None:
        updates["word/commentsIds.xml"] = serialize(cids)
    if cex is not None:
        updates["word/commentsExtensible.xml"] = serialize(cex)
    rewrite_zip(path, updates)
    return mapping


def rethread_replies(path: Path) -> None:
    """Turn independent Taehong Kwon balloons into Word replies on parents."""
    mapping = strip_independent_reply_balloons(path)
    stamp_replies_with_word(path, mapping)
    force_reply_authors(path)
    verify(path)
    verify_word_threads(path)
    print("rethreaded replies into existing supervisor comments")
    print("wrote", path)


def force_reply_authors(path: Path) -> None:
    reply_norm = {norm_comment_text(t) for t in REPLIES.values()}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        comments = etree.fromstring(z.read("word/comments.xml"))
        people = (
            etree.fromstring(z.read("word/people.xml"))
            if "word/people.xml" in names
            else None
        )
    n = 0
    changed = False
    for c in comments.findall(qn("comment")):
        text = norm_comment_text("".join(t.text or "" for t in c.iter(qn("t"))))
        if text not in reply_norm:
            continue
        n += 1
        if c.get(qn("author")) != AUTHOR:
            c.set(qn("author"), AUTHOR)
            changed = True
        if c.get(qn("initials")) != INITIALS:
            c.set(qn("initials"), INITIALS)
            changed = True
    if n != 27:
        raise RuntimeError(f"expected 27 reply comments to author-stamp, got {n}")
    updates: dict[str, bytes] = {}
    if changed:
        updates["word/comments.xml"] = serialize(comments)
    if people is not None:
        before = [p.get(f"{W15}author") for p in people]
        add_person(people)
        after = [p.get(f"{W15}author") for p in people]
        if after != before:
            updates["word/people.xml"] = serialize(people)
    if updates:
        rewrite_zip(path, updates)


def verify_word_threads(path: Path) -> None:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    doc = None
    try:
        doc = word.Documents.Open(str(path), False, True, False, "", "", True, "", "", 0, 0, False, False)
        n_parent = 0
        n_reply = 0
        n_tk = 0
        for i in range(1, doc.Comments.Count + 1):
            c = doc.Comments(i)
            ancestor = None
            try:
                ancestor = c.Ancestor
            except Exception:
                ancestor = None
            if ancestor is None:
                n_parent += 1
                if c.Replies.Count != 1:
                    raise AssertionError(f"parent {i} {c.Author!r} replies={c.Replies.Count}")
            else:
                n_reply += 1
                if c.Author == AUTHOR:
                    n_tk += 1
        print("Word top-level", n_parent, "replies", n_reply, "Taehong Kwon replies", n_tk)
        assert n_parent == 27
        assert n_reply == 27
        assert n_tk == 27
        doc.Close(False)
        doc = None
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
        word.Quit()
        pythoncom.CoUninitialize()


def serialize(root) -> bytes:
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def document_comment_ids(doc) -> set[str]:
    ids: set[str] = set()
    for tag in ("commentRangeStart", "commentRangeEnd", "commentReference"):
        for el in doc.iter(qn(tag)):
            cid = el.get(qn("id"))
            if cid:
                ids.add(cid)
    return ids


def verify(path: Path) -> None:
    assert zipfile.ZipFile(path).testzip() is None
    with zipfile.ZipFile(path) as z:
        for name in [
            "word/document.xml",
            "word/comments.xml",
            "word/commentsExtended.xml",
            "word/people.xml",
            "word/commentsIds.xml",
        ]:
            data = z.read(name)
            assert b"ns0:" not in data
            etree.fromstring(data)
        comments = etree.fromstring(z.read("word/comments.xml"))
        all_c = comments.findall(qn("comment"))
        tk = [c for c in all_c if c.get(qn("author")) == AUTHOR]
        others = [c for c in all_c if c.get(qn("author")) != AUTHOR]
        doc = etree.fromstring(z.read("word/document.xml"))
        red = 0
        for col in doc.iter(qn("color")):
            if col.get(qn("val"), "").upper() == "FF0000":
                red += 1
        people = etree.fromstring(z.read("word/people.xml"))
        authors = [p.get(f"{W15}author") for p in people]
        print("comments total", len(all_c))
        print("supervisor comments", len(others))
        print("Taehong Kwon replies", len(tk))
        print("red color runs", red)
        print("people", authors)
        print("sha256", hashlib.sha256(path.read_bytes()).hexdigest())
        assert len(others) == 27
        assert len(tk) == 27
        assert red >= 15
        assert AUTHOR in authors
        assert "Moulla, Donatien Koulla" in authors
        assert "Attipoe, David Sena" in authors

        comment_ids = {c.get(qn("id")) for c in all_c}
        body_ids = document_comment_ids(doc)
        print("document comment ids", len(body_ids))
        assert comment_ids <= body_ids

        ex = etree.fromstring(z.read("word/commentsExtended.xml"))
        ex_by_para = {
            el.get(f"{W15}paraId"): el for el in ex if el.get(f"{W15}paraId")
        }
        ext_ids = set(ex_by_para)
        parent_pids = {parent_para_id(c, ext_ids) for c in others}
        parents = [
            el.get(f"{W15}paraIdParent")
            for el in ex
            if el.get(f"{W15}paraIdParent")
        ]
        assert len(parents) == 27, len(parents)
        linked: set[str] = set()
        for reply in tk:
            reply_pid = parent_para_id(reply, ext_ids)
            reply_ex = ex_by_para[reply_pid]
            got = reply_ex.get(f"{W15}paraIdParent")
            assert got in parent_pids, (reply.get(qn("id")), got)
            linked.add(got)
            assert reply.get(qn("author")) == AUTHOR
            assert reply.get(qn("initials")) == INITIALS
        assert linked == parent_pids

        cids = etree.fromstring(z.read("word/commentsIds.xml"))
        cid_paras = {el.get(f"{W16CID}paraId") for el in cids}
        for reply in tk:
            reply_pid = parent_para_id(reply, ext_ids)
            assert reply_pid in cid_paras


def set_comment_text(comment, text: str) -> None:
    """Replace visible reply text; keep paraId and the annotationRef run."""
    p = comment.find(qn("p"))
    if p is None:
        raise KeyError(f"comment {comment.get(qn('id'))} has no paragraph")
    sample = first_text_run(p)
    kept = []
    for child in list(p):
        tag = etree.QName(child).localname
        if tag == "pPr":
            continue
        if tag == "r" and child.find(qn("annotationRef")) is not None:
            kept.append(child)
            continue
        p.remove(child)
    run = make_red_run(text, sample)
    # Replies are comment text, not body; keep the author's existing run style
    # but do not force body-red on the comment pane.
    color = run.find(qn("rPr"))
    if color is not None:
        col = color.find(qn("color"))
        if col is not None:
            color.remove(col)
    if kept:
        kept[-1].addnext(run)
    else:
        ppr = p.find(qn("pPr"))
        if ppr is not None:
            ppr.addnext(run)
        else:
            p.insert(0, run)


REPLY_PREFIX_TO_PARENT = {
    "Rewrote that sentence in the first person": "7",
    "Added a one-sentence circular-construction caveat": "14",
    "Removed GF-PR / SRQ1 / SC1 from the": "14",
    "Re-posed RQ4 in red as a construct-validity": "74",
    "Added a red paragraph under Contributions stating that the present claim is latest-allowance": "77",
    "Acknowledged. I am not inserting a two-page": "78",
    "Rewrote the close of this paragraph in red: allowance tau": "310",
    "Acknowledged: major revision before examination. This working copy only": "378",
}


def update_existing_replies(comments_root) -> int:
    target_ids = set(REPLY_PREFIX_TO_PARENT.values())
    found: set[str] = set()
    for c in comments_root.findall(qn("comment")):
        if c.get(qn("author")) != AUTHOR:
            continue
        text = "".join(t.text or "" for t in c.iter(qn("t")))
        parent_id = None
        for pid in target_ids:
            if text == REPLIES[pid]:
                parent_id = pid
                break
        if parent_id is None:
            for prefix, pid in REPLY_PREFIX_TO_PARENT.items():
                if text.startswith(prefix):
                    parent_id = pid
                    break
        if parent_id is None:
            continue
        if text != REPLIES[parent_id]:
            set_comment_text(c, REPLIES[parent_id])
        found.add(parent_id)
    if found != target_ids:
        raise RuntimeError(f"updated {sorted(found)}, expected {sorted(target_ids)}")
    return len(found)


def apply_body_inplace(doc) -> None:
    """Patch the already-replied working copy. Do not insert duplicate blocks."""
    body = doc.find(qn("body"))
    paras = [p for p in body if etree.QName(p).localname == "p"]

    def by_comment(cid: str):
        return find_para(paras, lambda p: para_has_comment(p, cid))

    def by_prefix(prefix: str):
        try:
            return find_para(paras, lambda p: para_text(p).startswith(prefix))
        except KeyError:
            return None

    replace_para_text(
        by_comment("2"),
        "Decentralized finance protocols allocate capital among pseudonymous wallets and therefore need on-chain reputation scores that can be refreshed often and checked against public ledger signals. The identified problem is that transfer-graph reputation is costly to refresh and does not encode explicit spending authorization. This study introduces EndorseRank, PageRank on latest ERC-20 allowance edges on Arbitrum One, and compares it with Adaptive Weighted PageRank (AWP) on a matched wallet cohort (n = 5,521) defined by GMX activity as a sampling frame only.",
    )
    replace_para_text(
        by_prefix("On the matched cohort, EndorseRank completes PageRank in 2.105"),
        "On the matched cohort, EndorseRank completes PageRank in 2.105 s versus 18.711 s for AWP (approximately 8.9 times faster). Allowance-family alignment is an intended-construct check, not an external test: EndorseRank mean Kendall tau = 0.355, while AWP is near zero (-0.030). AWP remains closer to transfer proxies (tau = 0.534 versus 0.333). Inter-method rank correlation (tau = 0.316) indicates overlapping but not interchangeable rankings. On the holdout spender cohort (n = 1,335), EndorseRank aligns with future new approvers at Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529); AWP is 0.044. That is not a prediction of trading profit, liquidation, or malicious spenders.",
    )
    replace_para_text(
        by_comment("7"),
        "GMX V2 activity defines the matched sample (at least three PositionDecrease closes). It is not a trading-success test. Trading-success, inverse-risk, liquidation, and GF-PR alignments are not claims.",
    )
    replace_para_text(
        by_comment("20"),
        "Decentralized Finance (DeFi) has transformed how capital is allocated on public blockchains, enabling lending, borrowing, and leveraged trading without traditional financial intermediaries [53]. Yet most credit-like interactions remain highly collateralized because protocols cannot rely on off-chain identity systems or conventional credit histories [48]. In a pseudonymous environment, the operational challenge is to allocate capital safely when counterparties are addresses rather than identified persons.",
    )
    replace_para_text(
        by_prefix("This thesis addresses a concrete research problem"),
        "This thesis addresses a concrete research problem within that setting: whether an on-chain reputation score built from ERC-20 approve/permit allowances—implemented as EndorseRank—can reduce computational cost, represent endorsement semantics more faithfully, and yield a distinct yet credible alignment profile compared with transfer-based Adaptive Weighted PageRank (AWP) on Arbitrum One. The primary empirical comparison is EndorseRank versus AWP on an identical wallet sample, using same-window allowance and transfer checks plus a temporal holdout of future new approvals.",
    )
    replace_para_text(
        by_prefix("Note: GF-PR is circular by construction"),
        "Note: GF-PR and trading-success families are excluded from the research claims. The external check is the temporal holdout of future new approvals.",
    )
    replace_para_text(
        by_prefix("Four objectives are derived from the problem statement"),
        "Four objectives are derived from the problem statement and map onto the primary research questions. O1: establish whether EndorseRank and AWP produce distinct wallet orderings on one Arbitrum cohort (RQ1). O2: compare contemporaneous allowance and transfer checks (RQ2). O3: measure computational cost of EndorseRank versus AWP at equal n (RQ3). O4: test whether t1 scores predict t2 new owner–spender approvals on inbound spenders (RQ4).",
    )
    replace_para_text(
        by_prefix("RQ2. Between EndorseRank and AWP"),
        "RQ2. Between EndorseRank and AWP, which social method aligns more strongly with contemporaneous allowance checks and with transfer checks (Spearman’s ρ, Kendall’s τ)?",
    )
    replace_para_text(
        by_comment("74"),
        "RQ4. After scores are frozen at 28 February 2026, does EndorseRank predict new owner–spender approvals in March–May 2026 on t1 inbound spenders more strongly than AWP? This is a time-split test of the endorsement construct, not a trading-success contest.",
    )
    replace_para_text(
        by_prefix("SRQ1. What does the supplementary GF-PR"),
        "SRQ1 is withdrawn. GF-PR is not a research claim. The external check is the temporal holdout under RQ4.",
    )
    replace_para_text(
        by_prefix("RQ1 tests whether allowance and transfer graphs"),
        "RQ1 tests whether allowance and transfer graphs induce distinct centrality structures, operationalized by inter-method Kendall τ between score vectors. RQ2 evaluates contemporaneous allowance versus transfer checks. RQ3 compares PageRank wall-clock time on identical wallet sets. RQ4 tests whether t1 scores predict t2 new owner–spender approvals on inbound spenders.",
    )
    replace_para_text(
        by_comment("78"),
        "The originality claimed here is not a new ranking algorithm. EndorseRank applies stock PageRank to latest ERC-20 allowance edges, compares that score with AWP on same-window allowance and transfer checks, and tests whether t1 scores predict t2 new approvals on inbound spenders. Whether that time-split check is a sufficient doctoral contribution is for the supervisory meeting; this draft only makes the present scope explicit.",
    )
    replace_para_text(
        by_prefix("Five-proxy domain alignment evaluation: Compares EndorseRank and AWP on leveraged"),
        "Holdout of future approvals: After scores freeze at 28 February 2026, new owner–spender pairs in March–May 2026 are the external check on t1 inbound spenders (n = 1,335).",
    )
    replace_para_text(
        by_prefix("DeFi activity. Proxies span transfer centrality"),
        "EndorseRank Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529); AWP is 0.044. Same-window checks remain allowance versus transfer. Trading-success families are not claims.",
    )
    try:
        p316 = find_para(
            paras,
            lambda p: "claims C1–C4 and SC1" in para_text(p) or "claims C1-C4 and SC1" in para_text(p),
        )
    except KeyError:
        p316 = None
    replace_para_text(
        p316,
        "Open reproducible evaluation pipeline: Links BigQuery extraction, graph construction, PageRank scoring, proxy computation, and LaTeX result tables to a machine-readable summary (Appendix 8.1). The pipeline supports independent verification of claims C1–C4. "
        f"Repository: {REPO} (commit {COMMIT}). Versioned configuration: A-Skill-Programs/margin_rank/config/margin_config.yaml. Tables are transcribed from the pipeline’s machine-readable evaluation summary. An anonymised archive can be supplied if a private snapshot is required.",
    )
    replace_para_text(
        by_prefix("GF-PR ceiling analysis: Clarifies construct overlap on trading-outcome proxies for the matched"),
        "Temporal holdout, not GF-PR: The external check is future new approvals, not an outcome-native ceiling. GF-PR and trading-success alignments are excluded from the claims.",
    )
    replace_para_text(
        by_comment("310"),
        "This pattern must be read honestly. EndorseRank is essentially a global smoothing of allowance in-degree, so correlating it with allowance in-degree is close to correlating a quantity with itself (tau = 0.355). I do not call that an external test. The out-of-window check is future new approvers on spenders: EndorseRank tau = 0.479 (CI 0.426–0.529) versus AWP 0.044. Trading-success and inverse-risk alignments are dropped from the claims.",
    )
    replace_para_text(
        by_prefix("GF-PR is likewise near zero on allowance"),
        "I do not use GF-PR, trading-success, or inverse-risk alignments as supporting evidence. Same-window allowance tau is an intended-construct check; the external check is the spender holdout.",
    )
    replace_para_text(
        by_prefix("Conceptual model: primary EndorseRank vs. AWP"),
        "Conceptual model: primary EndorseRank vs. AWP comparison mapped to reputation structure (H1/RQ1), same-window allowance and transfer checks (H2/RQ2), and computational efficiency (H3/RQ3). RQ4 is the temporal holdout of future new approvals.",
    )
    replace_para_text(
        by_prefix("ence (SRQ1), not a third peer social method"),
        "GF-PR is not a claim and is not a third peer social method.",
    )
    replace_para_text(
        by_prefix("Distribution of GMX realized PnL summaries"),
        "Distribution of GMX realized PnL summaries in the matched cohort. These figures describe the sample. They are not a trading-success validation axis.",
    )
    replace_para_text(
        by_prefix("Distribution of GMX close success rates"),
        "Distribution of GMX close success rates in the matched cohort. Close counts define the sampling filter (at least three PositionDecrease events), not a trading-success claim.",
    )
    replace_para_text(
        by_prefix("Table 1.1 summarizes the primary comparison"),
        "Table 1.1 summarizes the primary comparison. Table 1.3 summarizes hypotheses (H1–H3), research questions (RQ1–RQ4), and Chapter 4 empirical claims (C1–C4). SRQ1 and SC1 are withdrawn.",
    )
    replace_para_text(
        by_prefix("This study tests three primary hypotheses"),
        "This study tests three primary hypotheses: H1—EndorseRank and AWP yield distinct wallet orderings on the same cohort; H2—the two social methods differ on contemporaneous allowance versus transfer checks; and H3—EndorseRank is computationally more efficient than AWP at equal n. RQ1–RQ4 form the primary comparison. RQ4 is the temporal holdout. SRQ1 is withdrawn.",
    )
    replace_para_text(
        by_prefix("directly. Transfer proxies yield higher mean"),
        "The out-of-window check is not trading-success tau. On the holdout spender cohort (n = 1,335), EndorseRank aligns with future new approvers at Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529); AWP is 0.044. That is the same endorsement construct in the future tense. It is not a prediction of trading profit, liquidation, or malicious spenders. Matched-cohort intersection events are too sparse to claim.",
    )
    replace_para_text(
        by_prefix("Supplementary GF-PR ceiling analysis"),
        "Temporal holdout of future new approvals (RQ4)",
    )
    replace_para_text(
        by_prefix("Two further observations clarify the ceiling"),
        "Two further observations limit over-reading. First, same-window allowance tau = 0.355 is an intended-construct check, not an external test. Second, revoke, drain, and Aave liquidation labels are not sold as successes: they are the wrong sign, the wrong construct, or too sparse.",
    )
    replace_para_text(
        by_prefix("Supplementary claim SC1:"),
        "Withdrawn: SC1 / GF-PR is not a research claim. The external check that remains is the spender holdout under RQ4.",
    )
    replace_para_text(
        by_prefix("Primary claims (C1–C4) and supplementary claim"),
        "Primary claims (C1–C4)",
    )
    replace_para_text(
        by_prefix("SC1. GF-PR’s highest trading-success"),
        "C4. On t1 inbound spenders (n = 1,335), EndorseRank predicts t2 new owner–spender approvals at Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529). AWP is 0.044. That holdout is the external check. Trading-success and GF-PR alignments are not claims.",
    )
    replace_para_text(
        by_prefix("faster depending on sample definition"),
        "faster depending on sample definition. RQ4 is addressed by the spender holdout (EndorseRank tau = 0.479, CI 0.426–0.529; AWP 0.044), not by comparing transfer means to trading-success means. SRQ1 and SC1 are withdrawn.",
    )
    replace_para_text(
        by_prefix("Chapter 5 interprets these findings against RQ1–RQ4 and SRQ1"),
        "Chapter 5 interprets these findings against RQ1–RQ4 and discusses implications, threats to validity, and limitations. Trading-success and GF-PR are not claims.",
    )
    replace_para_text(
        by_prefix("This chapter interprets the Chapter 4 findings against RQ1–RQ4 and SRQ1"),
        "This chapter interprets the Chapter 4 findings against RQ1–RQ4, discusses implications for DeFi screening, addresses threats to validity, and states limitations of the EndorseRank–AWP comparison. Headline quantities are inter-method Kendall tau = 0.316, EndorseRank allowance tau = 0.355, AWP transfer tau = 0.534, holdout future-new-approvers tau = 0.479 (CI 0.426–0.529) versus AWP 0.044, and PageRank runtimes of 2.105 s versus 18.711 s. Trading-success and GF-PR alignments are not claims.",
    )
    replace_para_text(
        by_prefix("The primary empirical comparison concerns EndorseRank and AWP"),
        "The primary empirical comparison concerns EndorseRank and AWP as social reputation methods on wallet-to-wallet graphs. The following subsections interpret each research question in light of same-window allowance and transfer checks, the computational benchmarks, and the temporal holdout.",
    )
    replace_para_text(
        by_prefix("RQ2 asks which social method aligns more strongly with each of the five proxy families"),
        "RQ2 asks which social method aligns more strongly with contemporaneous allowance checks and with transfer checks. EndorseRank wins on allowance (tau = 0.355); AWP wins on transfer (tau = 0.534). Trading-success and inverse-risk families are not used to answer RQ2.",
    )
    replace_para_text(
        by_prefix("On trading-success proxies derived from GMX V2"),
        "Trading-success, inverse-risk, liquidation, and malicious-spender alignments are excluded from the findings. GMX activity remains a sampling frame only.",
    )
    replace_para_text(
        by_prefix("0.096 falls in the negligible-noise band"),
        "Those families remain in the evaluation artifact. They are not used as evidence of trading skill, credit risk, or malicious spenders.",
    )
    replace_para_text(
        by_prefix("RQ4 asks which validation frame yields stronger rank alignment"),
        "RQ4 asks whether t1 scores predict t2 new owner–spender approvals on inbound spenders. On the spender cohort (n = 1,335), EndorseRank Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529); AWP is 0.044. That is a time-split test of the endorsement construct, not a transfer-versus-trading-success contest.",
    )
    replace_para_text(
        by_prefix("RQ4 therefore favors transfer proxies"),
        "RQ4 therefore favors the temporal holdout as the out-of-window check. Same-window transfer alignment remains a construct check for AWP, not a substitute for the holdout.",
    )
    replace_para_text(
        by_prefix("Supplementary finding (SRQ1)"),
        "Non-claims (withdrawn SRQ1 / SC1)",
    )
    replace_para_text(
        by_prefix("0.096 and AWP’s τ = 0.179 should be read"),
        "I do not read social-method trading-success tau against a GF-PR ceiling. GF-PR is circular with those outcomes. The external check that remains is the spender holdout.",
    )
    replace_para_text(
        by_prefix("The five-proxy framework extends Do et al"),
        "The remaining validation logic separates same-window allowance and transfer checks from the temporal holdout. EndorseRank aligns with its primary allowance construct (tau = 0.355) and predicts later new approvals on spenders (tau = 0.479). AWP aligns with transfer (tau = 0.534) and is near zero on the holdout (tau = 0.044).",
    )
    replace_para_text(
        by_prefix("GF-PR is suitable only as a diagnostic ceiling"),
        "GF-PR is not used as a diagnostic ceiling in the claims. Evaluation pipelines may retain the artifact; this research does not sell outcome-native ranking as social validity.",
    )
    replace_para_text(
        by_prefix("Proxy not ground truth:"),
        "Proxy not ground truth: No under-collateralized lending default labels are available at sufficient density. GMX V2 closes define the matched sample. They are not loan repayment and are not used as a trading-success claim.",
    )
    try:
        p1746 = find_para(
            paras,
            lambda p: para_text(p).startswith("dorseRank") and "0.179" in para_text(p),
        )
    except KeyError:
        p1746 = None
    replace_para_text(
        p1746,
        "Trading-success alignments (formerly 0.096 / 0.179) are dropped from the claims.",
    )
    replace_para_text(
        by_prefix("This thesis formulated EndorseRank"),
        "This thesis formulated EndorseRank, a PageRank method on a latest-allowance endorsement graph that produces an on-chain reputation score on Arbitrum One, and evaluated it against Adaptive Weighted PageRank (AWP) on an identical matched wallet cohort (n = 5,521). GMX V2 activity is a sampling frame (365,488 decoded PositionDecrease events; at least three closes). Same-window checks are allowance versus transfer. The external check is a temporal holdout of future new approvals on t1 inbound spenders (n = 1,335).",
    )
    replace_para_text(
        by_prefix("On social-method alignment (RQ2)"),
        "On social-method alignment (RQ2), construct-specific winners emerge. EndorseRank leads on allowance checks (tau = 0.355 versus AWP −0.030); AWP leads on transfer checks (tau = 0.534 versus EndorseRank 0.333). H2 is supported in that construct-specific form.",
    )
    replace_para_text(
        by_prefix("ically, AWP exceeds EndorseRank"),
        "Trading-success families are not used to support H2.",
    )
    replace_para_text(
        by_prefix("On validation frames (RQ4)"),
        "On the temporal holdout (RQ4), EndorseRank predicts future new approvers at Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529) versus AWP 0.044. That is not a trading-profit, liquidation, or malicious-spender result.",
    )
    replace_para_text(
        by_prefix("As a supplementary finding (SRQ1)"),
        "SRQ1 / SC1 are withdrawn. GF-PR is not a deployable social reputation score and is not used as a ceiling claim.",
    )
    replace_para_text(
        by_prefix("Five-proxy domain alignment evaluation: Compares EndorseRank and AWP on leveraged DeFi"),
        "Same-window and holdout evaluation: Compares EndorseRank and AWP on allowance versus transfer checks and on t2 new owner–spender approvals. The result is a construct-specific map, not a trading-success ranking.",
    )
    replace_para_text(
        by_prefix("GF-PR ceiling analysis: Clarifies construct overlap on trading-outcome proxies (SRQ1)"),
        "Temporal holdout: t1 scores versus t2 new approvals on inbound spenders (EndorseRank tau = 0.479, CI 0.426–0.529; AWP 0.044). GF-PR is excluded from the claims.",
    )
    replace_para_text(
        by_prefix("This thesis reports primary empirical claims C1–C4"),
        "This thesis reports primary empirical claims C1–C4 addressing RQ1–RQ4 on a matched Arbitrum One wallet cohort (n = 5,521) and a spender holdout (n = 1,335). EndorseRank is an efficient, allowance-specific alternative to transfer-based AWP: distinct in ranking geometry (inter-method tau = 0.316), aligned with its primary construct (allowance tau = 0.355), faster to compute (2.105 s versus 18.711 s), and predictive of later new approvals (tau = 0.479).",
    )
    replace_para_text(
        by_prefix("Statement: For social methods, transfer proxies align more strongly than trading-success"),
        "Statement: The external check is the temporal holdout of future new approvals, not transfer versus trading-success.",
    )
    replace_para_text(
        by_prefix("SRQ1 / SC1 — GF-PR ceiling"),
        "RQ4 — temporal holdout of future new approvals",
    )


def apply_body_pass2(doc) -> None:
    """Second pass: leftover chapter openings that still sell five-proxy / GF-PR."""
    body = doc.find(qn("body"))
    paras = [p for p in body if etree.QName(p).localname == "p"]

    def by_prefix(prefix: str):
        try:
            return find_para(paras, lambda p: para_text(p).startswith(prefix))
        except KeyError:
            return None

    replace_para_text(
        by_prefix("§4.7"),
        "§4.7 Holdout of future new approvals. Table 4.2",
    )
    replace_para_text(
        by_prefix("Chapter 3 specifies data sources"),
        "Chapter 3 specifies data sources, sampling, graph construction for EndorseRank and AWP, same-window allowance and transfer checks, the temporal holdout, computational benchmarks, robustness checks, reproducibility practices, and ethics. It defines the matched wallet cohort, the expanded wallet pool used for scaling, and the operational procedures that produce the Chapter 4 tables.",
    )
    replace_para_text(
        by_prefix("Chapter 4 reports empirical results"),
        "Chapter 4 reports empirical results: cohort characteristics, runtime and scaling benchmarks (Claim C1), robustness checks, same-window allowance and transfer checks (Claims C2–C3), rank divergence (H1/RQ1), and the temporal holdout of future new approvals (RQ4 / C4). Primary claims are C1–C4. SRQ1 and SC1 are withdrawn.",
    )
    replace_para_text(
        by_prefix("Following Do et al.[16] and Cronbach"),
        "Following Do et al.[16] and Cronbach & Meehl[14], construct alignment for rank-based scores uses Spearman’s ρ and Kendall’s τ. This research reports same-window allowance and transfer checks plus a temporal holdout of future new approvals. Trading-success, inverse-risk, and liquidation families remain in the artifact and are not claims.",
    )
    replace_para_text(
        by_prefix("This chapter reports the empirical evaluation of EndorseRank against Adaptive Weighted"),
        "This chapter reports the empirical evaluation of EndorseRank against Adaptive Weighted PageRank (AWP) on Arbitrum One. The analysis proceeds from cohort construction, through computational benchmarks and robustness checks, to contemporaneous allowance and transfer checks, inter-method rank divergence, and a temporal holdout of future new approvals. Primary claims C1–C4 address the EndorseRank–AWP comparison. Trading-success, inverse-risk, liquidation, and GF-PR alignments are not claims.",
    )
    replace_para_text(
        by_prefix("transfer alignment is moderate"),
        "transfer alignment is moderate (τ = 0.333)—credible as a secondary axis, but below AWP. Inverse-risk and trading-success alignments are not used as evidence. Same-window allowance tau is an intended-construct check; the external check is the spender holdout.",
    )
    replace_para_text(
        by_prefix("GF-PR achieves the highest family mean"),
        "GF-PR’s near-identity with realized-gain is why that family is excluded: shared PnL input is not an independent test. Those rows stay in the artifact. They are not claims.",
    )
    replace_para_text(
        by_prefix("GF-PR was added during empirical work"),
        "GF-PR was computed during exploratory work and is excluded from the claims because it is circular with GMX profit-and-loss. The external check that remains is the spender holdout under RQ4 (EndorseRank tau = 0.479, CI 0.426–0.529; AWP 0.044).",
    )
    replace_para_text(
        by_prefix("GF-PR achieves the highest trading-success mean"),
        "GF-PR is circular with trading-success and inverse-risk proxies by construction. This draft does not use that ceiling as a finding. The external check is the temporal holdout.",
    )
    replace_para_text(
        by_prefix("GF-PR construct overlap:"),
        "Non-claim: GF-PR shares input semantics with trading-success and inverse-risk proxies. Those alignments are not interpreted as social reputation and are not research claims.",
    )
    replace_para_text(
        by_prefix("Hybrid social and outcome-aware methods:"),
        "Hybrid social methods: Operators may combine endorsement-graph features with transfer-graph features, or with DeFi-informed representation learning [39], while preserving the auditability emphasized by Packin and Lev-Aretz[48]. Hybrid designs should report construct-specific checks and, where claimed, a time-split holdout rather than a single aggregate trading-success metric.",
    )


DISS_PAIRS = (
    ("This dissertation", "This research"),
    ("this dissertation", "this research"),
    ("For this dissertation", "For this research"),
    ("the dissertation's", "this research's"),
    ("The dissertation's", "This research's"),
    ("The dissertation", "This research"),
    ("the dissertation", "this research"),
    ("Dissertation roadmap", "Research roadmap"),
    ("dissertation claims", "research claims"),
    ("a dissertation claim", "a research claim"),
    ("dissertation claim", "research claim"),
    ("dissertation narrative", "research narrative"),
    ("main dissertation", "main research"),
)


def rewrite_dissertation(text: str) -> str:
    for old, new in DISS_PAIRS:
        text = text.replace(old, new)
    return text


def para_has_any_comment(p) -> bool:
    for el in p.iter():
        tag = etree.QName(el).localname
        if tag in {"commentRangeStart", "commentRangeEnd", "commentReference"}:
            return True
    return False


def remove_para(p) -> None:
    parent = p.getparent()
    if parent is None:
        raise RuntimeError("paragraph has no parent")
    parent.remove(p)


def remove_between(start, stop, *, keep_start: bool, keep_stop: bool) -> int:
    """Remove siblings from start to stop (both in the same parent)."""
    parent = start.getparent()
    if stop.getparent() is not parent:
        raise RuntimeError("start/stop parents differ")
    cur = start
    removed = 0
    while cur is not None:
        nxt = cur.getnext()
        is_start = cur is start
        is_stop = cur is stop
        drop = True
        if is_start and keep_start:
            drop = False
        if is_stop and keep_stop:
            drop = False
        if drop:
            if etree.QName(cur).localname == "p" and para_has_any_comment(cur):
                raise RuntimeError(
                    f"refusing to delete commented paragraph: {para_text(cur)[:80]!r}"
                )
            parent.remove(cur)
            removed += 1
        if is_stop:
            break
        cur = nxt
    return removed


def apply_body_pass3(doc) -> None:
    """dissertation→research; drop perp mechanics and PnL/success-rate figures."""
    body = doc.find(qn("body"))

    def paras():
        return [p for p in body.iter(qn("p"))]

    def by_prefix(prefix: str):
        return find_para(paras(), lambda p: para_text(p).startswith(prefix))

    def by_exact(text: str):
        return find_para(paras(), lambda p: para_text(p).strip() == text)

    replace_para_text(
        by_prefix("Arbitrum One is an EVM-compatible optimistic rollup"),
        "Arbitrum One is an EVM-compatible optimistic rollup widely used for DeFi activity, including GMX V2 [23]. For this research, Arbitrum One is the empirical setting because (i) ERC-20 Approval and Transfer logs are available in public BigQuery datasets, (ii) GMX V2 emits wallet-attributed PositionDecrease events that serve only as an activity filter, and (iii) fee levels permit dense activity within a six-month window.",
    )
    replace_para_text(
        by_prefix("On Arbitrum One, dense wallet-attributed PositionDecrease"),
        "On Arbitrum One, GMX V2 PositionDecrease events define the matched sample: wallets with at least three closes (n = 5,521) [23],[53]. Profit-and-loss, success rate, and liquidation are not validation.",
    )
    p_closes = find_para(
        paras(),
        lambda p: para_text(p).startswith("closes offer dense, wallet-level realized"),
    )
    replace_para_text(
        p_closes,
        "Under-collateralized lending default labels remain out of scope.",
    )
    p_perp_adv = find_para(
        paras(),
        lambda p: para_text(p).startswith("Perpetual markets allow leveraged long"),
    )
    replace_para_text(
        p_perp_adv,
        "This research does not predict trading profit, liquidation, or malicious spenders. The remaining external check is a temporal holdout of future new owner–spender approvals.",
    )
    replace_para_text(
        by_prefix("Primary chain: All on-chain events"),
        "Primary chain: All on-chain events are drawn from Arbitrum One (chain ID 42161), an Ethereum Layer-2 rollup with dense DeFi activity and public log availability [53]. Restricting to a single chain avoids cross-chain address aliasing—the same private key controlling addresses on multiple chains would otherwise appear as unrelated nodes—and keeps gas-cost and latency regimes comparable across wallets. Arbitrum One is also the deployment venue for GMX V2, whose PositionDecrease events are used only as an activity filter.",
    )
    replace_para_text(
        by_prefix("Figure 3.1 summarizes the end-to-end flow from public logs to"),
        "Figure 3.1 summarizes the end-to-end flow from public logs to the research tables. Remote stages write immutable parquet; local stages are idempotent given those inputs and a single versioned configuration file.",
    )
    replace_para_text(
        by_prefix("Before comparing reputation rankings, it is useful to characterize"),
        "Figure 4.1 shows GMX close counts per wallet. The minimum of three closes is a sampling filter. The right tail is a count of repeated PositionDecrease events, not a performance ranking.",
    )
    replace_para_text(
        by_prefix("Figure 4.1: Distribution of GMX V2 PositionDecrease close counts"),
        "Figure 4.1: Distribution of GMX V2 PositionDecrease close counts per wallet in the matched cohort (n = 5,521). The cohort filter requires at least three closes.",
    )
    replace_para_text(
        by_prefix("Distribution of GMX V2 PositionDecrease close counts per wallet"),
        "Distribution of GMX V2 PositionDecrease close counts per wallet in the matched cohort (n = 5,521). The cohort filter requires at least three closes.",
    )
    replace_para_text(
        by_prefix("Table 4.10 reports alignment with loss-avoidance"),
        "Table 4.10 is an artifact table and is not interpreted in the main text.",
    )
    replace_para_text(
        by_prefix("Table 4.12 reports alignment with close-success count"),
        "Table 4.12 is an artifact table and is not interpreted in the main text.",
    )
    replace_para_text(
        by_exact("Trading success validation frame (GMX V2)"),
        "GMX V2 as a sampling frame",
    )
    toc_gmx = find_para(
        paras(),
        lambda p: para_text(p).startswith("Trading success validation frame (GMX V2)"),
    )
    replace_para_text(toc_gmx, "GMX V2 as a sampling frame")

    perp_body = find_para(
        paras(),
        lambda p: para_text(p).startswith('Perpetual futures (“perps”) are derivative'),
    )
    related = find_para(
        paras(),
        lambda p: para_text(p).strip() == "Related measurement traditions"
        and pstyle(p).startswith("Heading"),
    )
    perp_head = None
    cur = perp_body.getprevious()
    while cur is not None:
        if etree.QName(cur).localname == "p" and pstyle(cur).startswith("Heading"):
            perp_head = cur
            break
        cur = cur.getprevious()
    if perp_head is None or "Perpetual markets" not in para_text(perp_head):
        raise RuntimeError(f"perp heading not found near {para_text(perp_body)[:60]!r}")
    remove_between(perp_head, related, keep_start=False, keep_stop=True)

    toc_perp = find_para(
        paras(),
        lambda p: "Perpetual markets as a validation laboratory" in para_text(p),
    )
    remove_para(toc_perp)

    lof_pnl = find_para(
        paras(),
        lambda p: para_text(p).startswith("Distribution of GMX realized PnL summaries"),
    )
    lof_sr = find_para(
        paras(),
        lambda p: para_text(p).startswith("Distribution of GMX close success rates"),
    )
    remove_between(lof_pnl, lof_sr, keep_start=False, keep_stop=False)

    fig41 = by_prefix("Figure 4.1: Distribution of GMX V2 PositionDecrease close counts")
    bench = find_para(
        paras(),
        lambda p: para_text(p).strip() == "EndorseRank vs. AWP benchmark (Claim C1)",
    )
    remove_between(fig41, bench, keep_start=True, keep_stop=True)
    summary = new_para_like(
        fig41,
        "The close-count figure and the edge-count gap in the dataset table fix two sample constraints. First, the matched cohort is large enough for stable rank statistics (n = 5,521; 365,488 decoded closes). Second, endorsement and transfer graphs differ by nearly an order of magnitude in edge count, so efficiency and alignment claims must be evaluated jointly.",
    )
    fig41.addnext(summary)

    # Drop leftover inverse-risk / trading-success interpretation (tables stay).
    for prefix in (
        "Among social methods, alignment is weak overall. EndorseRank family mean",
        "For the primary comparison, the inverse-risk family supports a cautious reading",
        "success rate remains weak",
        "GF-PR achieves the highest family mean (0.583)",
        "The trading-success family thus plays a dual role",
        "Comparing trading-success means to transfer means",
        "Figure 4.2 displays the distribution of realized profit-and-loss",
        "long right tail reflects a minority of highly active traders",
    ):
        try:
            p = by_prefix(prefix)
        except KeyError:
            continue
        if para_has_any_comment(p):
            raise RuntimeError(f"commented leftover: {prefix}")
        remove_para(p)

    # Remaining dissertation wording in readable body (not supervisor comments).
    for p in paras():
        old = para_text(p)
        if "dissertation" not in old.lower():
            continue
        new = rewrite_dissertation(old)
        if new != old:
            replace_para_text(p, new)


def inplace_main() -> None:
    """Update the existing replied DOCX. Never copy from the review original."""
    if set(PARENT_ORDER) != set(REPLIES):
        raise RuntimeError("PARENT_ORDER and REPLIES keys differ")
    if not DST.exists():
        raise FileNotFoundError(DST)
    with zipfile.ZipFile(DST) as z:
        doc = etree.fromstring(z.read("word/document.xml"))
        comments = etree.fromstring(z.read("word/comments.xml"))
    apply_body_inplace(doc)
    apply_body_pass2(doc)
    apply_body_pass3(doc)
    n = update_existing_replies(comments)
    try:
        rewrite_zip(
            DST,
            {
                "word/document.xml": serialize(doc),
                "word/comments.xml": serialize(comments),
            },
        )
    except PermissionError as exc:
        raise PermissionError(
            f"Target is locked (Word may have it open): {DST} ({exc})"
        ) from exc
    force_reply_authors(DST)
    verify(DST)
    print("updated replies", n)
    print("wrote", DST)


def main() -> None:
    if set(PARENT_ORDER) != set(REPLIES):
        raise RuntimeError("PARENT_ORDER and REPLIES keys differ")
    if not SRC.exists():
        raise FileNotFoundError(SRC)
    try:
        shutil.copy2(SRC, DST)
    except PermissionError as exc:
        raise PermissionError(
            f"Target is locked (Word may have it open): {DST}"
        ) from exc
    with zipfile.ZipFile(DST) as z:
        doc = etree.fromstring(z.read("word/document.xml"))
        comments = etree.fromstring(z.read("word/comments.xml"))

    id_by_text = xml_id_by_text(comments)
    apply_body(doc)
    rewrite_zip(DST, {"word/document.xml": serialize(doc)})
    stamp_replies_with_word(DST, id_by_text)
    force_reply_authors(DST)
    verify(DST)
    verify_word_threads(DST)
    print("wrote", DST)


if __name__ == "__main__":
    import sys

    if "--rethread" in sys.argv:
        rethread_replies(DST)
    elif "--inplace" in sys.argv:
        inplace_main()
    else:
        main()
