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
    "7": "Dropped GMX trading-success, inverse-risk, liquidation, and GF-PR from the claims. The matched sample is now wallets with non-zero endorsement- and transfer-graph connectivity (n = 5,521). The external check is a temporal holdout of future new owner–spender approvals.",
    "14": "Removed GF-PR / SRQ1 / SC1 from the research claims. The remaining external check is the temporal holdout.",
    "20": "Split this opening paragraph so each claim has one source: [53] for DeFi intermediation; [48] for the absence of conventional credit histories. A document-wide cluster pass is deferred.",
    "62": "Kept the 2.105 s / 8.9× measurement. Added in red that the speedup is the expected O(|E|) consequence of approval sparsity, that the solver matches AWP, and that C1 is demoted from a headline contribution.",
    "72": "Inserted a Research objectives section (four objectives, mapped to RQ1–RQ4) immediately before Research questions. Chapter 5 mapping of each objective is deferred until after the meeting.",
    "74": "Re-posed RQ4 as a temporal holdout: t1 scores versus t2 new owner–spender approvals on inbound spenders.",
    "77": "Rewrote the contribution paragraph: the claim is latest-allowance edges, same-window allowance versus transfer checks, and a temporal holdout of future new approvals—not a new ranking algorithm.",
    "78": "Implemented a temporal holdout rather than another same-window proxy. Scores freeze at 28 February 2026; labels are new owner–spender approvals in March–May 2026 on t1 inbound spenders (n = 1,335). EndorseRank Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529); AWP = 0.044. That is the same endorsement construct in the future tense, with CIs. Method is still stock PageRank; the contribution is the time-split check, not a new solver.",
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
    "310": "I keep the honesty you asked for: same-window allowance tau = 0.355 is an intended-construct check, not an external test (AWP is -0.030). The external check is now a holdout of future new approvers on spenders: EndorseRank tau = 0.479 (CI 0.426–0.529) versus AWP 0.044.",
    "349": "Collapsed this subsection to one short paragraph and removed the Akerlof / Graham–Dodd / Basu / Fama–French / Healy–Wahlen cluster from this location.",
    "378": "Acknowledged: major revision before examination. This working copy now reports the connectivity cohort (n = 5,521) and the spender holdout (EndorseRank tau = 0.479, CI 0.426–0.529). Still open: ethics certificate, raw logs, and a full LaTeX–Word cleanup. I do not have Supervisory_Review_Taehong_Thesis.",
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
        "Decentralized finance protocols allocate capital among pseudonymous wallets and therefore need on-chain reputation scores that can be refreshed often and checked against public ledger signals. The identified problem is that transfer-graph reputation is costly to refresh and does not encode explicit spending authorization. This study introduces EndorseRank, PageRank on latest ERC-20 allowance edges on Arbitrum One, and compares it with Adaptive Weighted PageRank (AWP) on a matched wallet cohort (n = 5,521) with non-zero endorsement- and transfer-graph connectivity.",
    )

    p40 = find_para(
        paras,
        lambda p: para_text(p).startswith("EndorseRank runs") and "8.9" in para_text(p),
    )
    replace_para_text(
        p40,
        "On the matched cohort, EndorseRank completes PageRank in 2.105 s versus 18.711 s for AWP (approximately 8.9 times faster). Allowance-family alignment is an intended-construct check, not an external test: EndorseRank mean Kendall tau = 0.355, while AWP is near zero (-0.030). AWP remains closer to transfer proxies (tau = 0.534 versus 0.333). Inter-method rank correlation (tau = 0.316) indicates overlapping but not interchangeable rankings. On the holdout spender cohort (n = 1,335), EndorseRank aligns with future new approvers at Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529); AWP is 0.044.",
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
        "The matched sample is wallets with non-zero endorsement- and transfer-graph connectivity in the observation window (n = 5,521). Contemporaneous checks use allowance and transfer local statistics. A temporal holdout tests whether t1 scores predict t2 new owner–spender approvals.",
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
        "RQ4. After scores are frozen at 28 February 2026, does EndorseRank predict new owner–spender approvals in March–May 2026 on t1 inbound spenders more strongly than AWP?",
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
        "This pattern must be read honestly. EndorseRank is essentially a global smoothing of allowance in-degree, so correlating it with allowance in-degree is close to correlating a quantity with itself (tau = 0.355). I do not call that an external test. The out-of-window check is future new approvers on spenders: EndorseRank tau = 0.479 (CI 0.426–0.529) versus AWP 0.044.",
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
        "Note: The external check is the temporal holdout of future new approvals on t1 inbound spenders.",
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
    "Dropped trading-success proxies and the GF-PR ceiling": "7",
    "Dropped GMX trading-success, inverse-risk": "7",
    "Added a one-sentence circular-construction caveat": "14",
    "Removed GF-PR / SRQ1 / SC1 from the": "14",
    "Re-posed RQ4 in red as a construct-validity": "74",
    "Re-posed RQ4 as a temporal holdout": "74",
    "Added a red paragraph under Contributions stating that the present claim is latest-allowance": "77",
    "Rewrote the contribution paragraph": "77",
    "Acknowledged. I am not inserting a two-page": "78",
    "Implemented a temporal holdout rather than another": "78",
    "Rewrote the close of this paragraph in red: allowance tau": "310",
    "I keep the honesty you asked for": "310",
    "Acknowledged: major revision before examination. This working copy only": "378",
    "Acknowledged: major revision before examination. This working copy now": "378",
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
        try:
            return find_para(paras, lambda p: para_has_comment(p, cid))
        except KeyError:
            return None

    def by_prefix(prefix: str):
        try:
            return find_para(paras, lambda p: para_text(p).startswith(prefix))
        except KeyError:
            return None

    replace_para_text(
        by_prefix("Decentralized finance protocols allocate capital among pseudonymous wallets"),
        "Decentralized finance protocols allocate capital among pseudonymous wallets and therefore need on-chain reputation scores that can be refreshed often and checked against public ledger signals. The identified problem is that transfer-graph reputation is costly to refresh and does not encode explicit spending authorization. This study introduces EndorseRank, PageRank on latest ERC-20 allowance edges on Arbitrum One, and compares it with Adaptive Weighted PageRank (AWP) on a matched wallet cohort (n = 5,521) with non-zero endorsement- and transfer-graph connectivity.",
    )
    replace_para_text(
        by_prefix("On the matched cohort, EndorseRank completes PageRank in 2.105"),
        "On the matched cohort, EndorseRank completes PageRank in 2.105 s versus 18.711 s for AWP (approximately 8.9 times faster). Allowance-family alignment is an intended-construct check, not an external test: EndorseRank mean Kendall tau = 0.355, while AWP is near zero (-0.030). AWP remains closer to transfer proxies (tau = 0.534 versus 0.333). Inter-method rank correlation (tau = 0.316) indicates overlapping but not interchangeable rankings. On the holdout spender cohort (n = 1,335), EndorseRank aligns with future new approvers at Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529); AWP is 0.044.",
    )
    replace_para_text(
        by_prefix("GMX V2 activity defines the matched sample"),
        "The matched sample is wallets with non-zero endorsement- and transfer-graph connectivity in the observation window (n = 5,521). Contemporaneous checks use allowance and transfer local statistics. A temporal holdout tests whether t1 scores predict t2 new owner–spender approvals.",
    )
    replace_para_text(
        by_prefix("Decentralized Finance (DeFi) has transformed how capital is allocated"),
        "Decentralized Finance (DeFi) has transformed how capital is allocated on public blockchains, enabling lending, borrowing, and leveraged trading without traditional financial intermediaries [53]. Yet most credit-like interactions remain highly collateralized because protocols cannot rely on off-chain identity systems or conventional credit histories [48]. In a pseudonymous environment, the operational challenge is to allocate capital safely when counterparties are addresses rather than identified persons.",
    )
    replace_para_text(
        by_prefix("This thesis addresses a concrete research problem"),
        "This thesis addresses a concrete research problem within that setting: whether an on-chain reputation score built from ERC-20 approve/permit allowances—implemented as EndorseRank—can reduce computational cost, represent endorsement semantics more faithfully, and yield a distinct yet credible alignment profile compared with transfer-based Adaptive Weighted PageRank (AWP) on Arbitrum One. The primary empirical comparison is EndorseRank versus AWP on an identical wallet sample, using same-window allowance and transfer checks plus a temporal holdout of future new approvals.",
    )
    replace_para_text(
        by_prefix("Note: GF-PR is circular by construction"),
        "Note: The external check is the temporal holdout of future new approvals on t1 inbound spenders.",
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
        by_prefix("RQ4. After scores are frozen at 28 February 2026"),
        "RQ4. After scores are frozen at 28 February 2026, does EndorseRank predict new owner–spender approvals in March–May 2026 on t1 inbound spenders more strongly than AWP?",
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
        by_prefix("The originality claimed here is not a new ranking algorithm"),
        "The originality claimed here is not a new ranking algorithm. EndorseRank applies stock PageRank to latest ERC-20 allowance edges, compares that score with AWP on same-window allowance and transfer checks, and tests whether t1 scores predict t2 new approvals on inbound spenders. Whether that time-split check is a sufficient doctoral contribution is for the supervisory meeting; this draft only makes the present scope explicit.",
    )
    replace_para_text(
        by_prefix("Five-proxy domain alignment evaluation: Compares EndorseRank and AWP on leveraged"),
        "Holdout of future approvals: After scores freeze at 28 February 2026, new owner–spender pairs in March–May 2026 are the external check on t1 inbound spenders (n = 1,335).",
    )
    replace_para_text(
        by_prefix("DeFi activity. Proxies span transfer centrality"),
        "EndorseRank Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529); AWP is 0.044. Same-window checks remain allowance versus transfer.",
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
        "Temporal holdout: The external check is future new owner–spender approvals on t1 inbound spenders.",
    )
    replace_para_text(
        by_prefix("This pattern must be read honestly"),
        "This pattern must be read honestly. EndorseRank is essentially a global smoothing of allowance in-degree, so correlating it with allowance in-degree is close to correlating a quantity with itself (tau = 0.355). I do not call that an external test. The out-of-window check is future new approvers on spenders: EndorseRank tau = 0.479 (CI 0.426–0.529) versus AWP 0.044.",
    )
    replace_para_text(
        by_prefix("GF-PR is likewise near zero on allowance"),
        "Same-window allowance tau is an intended-construct check; the external check is the spender holdout.",
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
        "List of figures: GMX profit-and-loss panels are withdrawn from this working copy.",
    )
    replace_para_text(
        by_prefix("Distribution of GMX close success rates"),
        "List of figures: GMX close-success panels are withdrawn from this working copy.",
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
        "On the holdout spender cohort (n = 1,335), EndorseRank aligns with future new approvers at Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529); AWP is 0.044. That is the same endorsement construct in the future tense.",
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
        "C4. On t1 inbound spenders (n = 1,335), EndorseRank predicts t2 new owner–spender approvals at Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529). AWP is 0.044. That holdout is the external check.",
    )
    replace_para_text(
        by_prefix("faster depending on sample definition"),
        "faster depending on sample definition. RQ4 is addressed by the spender holdout (EndorseRank tau = 0.479, CI 0.426–0.529; AWP 0.044). SRQ1 and SC1 are withdrawn.",
    )
    replace_para_text(
        by_prefix("Chapter 5 interprets these findings against RQ1–RQ4 and SRQ1"),
        "Chapter 5 interprets these findings against RQ1–RQ4 and discusses implications, threats to validity, and limitations.",
    )
    replace_para_text(
        by_prefix("This chapter interprets the Chapter 4 findings against RQ1–RQ4 and SRQ1"),
        "This chapter interprets the Chapter 4 findings against RQ1–RQ4, discusses implications for DeFi screening, addresses threats to validity, and states limitations of the EndorseRank–AWP comparison. Headline quantities are inter-method Kendall tau = 0.316, EndorseRank allowance tau = 0.355, AWP transfer tau = 0.534, holdout future-new-approvers tau = 0.479 (CI 0.426–0.529) versus AWP 0.044, and PageRank runtimes of 2.105 s versus 18.711 s.",
    )
    replace_para_text(
        by_prefix("The primary empirical comparison concerns EndorseRank and AWP"),
        "The primary empirical comparison concerns EndorseRank and AWP as social reputation methods on wallet-to-wallet graphs. The following subsections interpret each research question in light of same-window allowance and transfer checks, the computational benchmarks, and the temporal holdout.",
    )
    replace_para_text(
        by_prefix("RQ2 asks which social method aligns more strongly with each of the five proxy families"),
        "RQ2 asks which social method aligns more strongly with contemporaneous allowance checks and with transfer checks. EndorseRank wins on allowance (tau = 0.355); AWP wins on transfer (tau = 0.534).",
    )
    replace_para_text(
        by_prefix("On trading-success proxies derived from GMX V2"),
        "Same-window findings use allowance and transfer checks. The out-of-window check is the temporal holdout of future new approvals.",
    )
    replace_para_text(
        by_prefix("0.096 falls in the negligible-noise band"),
        "Those families remain in the evaluation artifact. They are not used as evidence of trading skill, credit risk, or malicious spenders.",
    )
    replace_para_text(
        by_prefix("RQ4 asks which validation frame yields stronger rank alignment"),
        "RQ4 asks whether t1 scores predict t2 new owner–spender approvals on inbound spenders. On the spender cohort (n = 1,335), EndorseRank Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529); AWP is 0.044.",
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
        "Proxy not ground truth: No under-collateralized lending default labels are available at sufficient density. The matched sample is wallets with non-zero endorsement- and transfer-graph connectivity (n = 5,521).",
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
        "This thesis formulated EndorseRank, a PageRank method on a latest-allowance endorsement graph that produces an on-chain reputation score on Arbitrum One, and evaluated it against Adaptive Weighted PageRank (AWP) on an identical matched wallet cohort (n = 5,521) with non-zero endorsement- and transfer-graph connectivity. Same-window checks are allowance versus transfer. The external check is a temporal holdout of future new approvals on t1 inbound spenders (n = 1,335).",
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
        "On the temporal holdout (RQ4), EndorseRank predicts future new approvers at Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529) versus AWP 0.044.",
    )
    replace_para_text(
        by_prefix("As a supplementary finding (SRQ1)"),
        "SRQ1 / SC1 are withdrawn. GF-PR is not a deployable social reputation score and is not used as a ceiling claim.",
    )
    replace_para_text(
        by_prefix("Five-proxy domain alignment evaluation: Compares EndorseRank and AWP on leveraged DeFi"),
        "Same-window and holdout evaluation: Compares EndorseRank and AWP on allowance versus transfer checks and on t2 new owner–spender approvals.",
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
        "Following Do et al.[16] and Cronbach & Meehl[14], construct alignment for rank-based scores uses Spearman’s ρ and Kendall’s τ. This research reports same-window allowance and transfer checks plus a temporal holdout of future new approvals.",
    )
    replace_para_text(
        by_prefix("This chapter reports the empirical evaluation of EndorseRank against Adaptive Weighted"),
        "This chapter reports the empirical evaluation of EndorseRank against Adaptive Weighted PageRank (AWP) on Arbitrum One. The analysis proceeds from cohort construction, through computational benchmarks and robustness checks, to contemporaneous allowance and transfer checks, inter-method rank divergence, and a temporal holdout of future new approvals. Primary claims C1–C4 address the EndorseRank–AWP comparison.",
    )
    replace_para_text(
        by_prefix("transfer alignment is moderate"),
        "transfer alignment is moderate (τ = 0.333)—credible as a secondary axis, but below AWP. Same-window allowance tau is an intended-construct check; the external check is the spender holdout.",
    )
    replace_para_text(
        by_prefix("GF-PR achieves the highest family mean"),
        "Same-window checks remain allowance versus transfer. The external check is the spender holdout.",
    )
    replace_para_text(
        by_prefix("GF-PR was added during empirical work"),
        "The external check that remains is the spender holdout under RQ4 (EndorseRank tau = 0.479, CI 0.426–0.529; AWP 0.044).",
    )
    replace_para_text(
        by_prefix("GF-PR achieves the highest trading-success mean"),
        "The external check is the temporal holdout of future new approvals, not an outcome-native ceiling.",
    )
    replace_para_text(
        by_prefix("GF-PR construct overlap:"),
        "Same-window checks are allowance versus transfer. The external check is the temporal holdout.",
    )
    replace_para_text(
        by_prefix("Hybrid social and outcome-aware methods:"),
        "Hybrid social methods: Operators may combine endorsement-graph features with transfer-graph features, or with DeFi-informed representation learning [39], while preserving the auditability emphasized by Packin and Lev-Aretz[48]. Hybrid designs should report construct-specific checks and, where claimed, a time-split holdout.",
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
        try:
            return find_para(paras(), lambda p: para_text(p).startswith(prefix))
        except KeyError:
            return None

    def by_exact(text: str):
        try:
            return find_para(paras(), lambda p: para_text(p).strip() == text)
        except KeyError:
            return None

    def try_find(pred):
        try:
            return find_para(paras(), pred)
        except KeyError:
            return None

    replace_para_text(
        by_prefix("Arbitrum One is an EVM-compatible optimistic rollup"),
        "Arbitrum One is an EVM-compatible optimistic rollup widely used for DeFi activity [23]. For this research, Arbitrum One is the empirical setting because (i) ERC-20 Approval and Transfer logs are available in public BigQuery datasets and (ii) fee levels permit dense activity within a six-month window.",
    )
    replace_para_text(
        by_prefix("On Arbitrum One, dense wallet-attributed PositionDecrease"),
        "On Arbitrum One, the matched sample is wallets with non-zero endorsement- and transfer-graph connectivity (n = 5,521) [23],[53]. Contemporaneous checks use allowance and transfer local statistics.",
    )
    replace_para_text(
        try_find(lambda p: para_text(p).startswith("closes offer dense, wallet-level realized")),
        "Under-collateralized lending default labels remain out of scope.",
    )
    replace_para_text(
        try_find(lambda p: para_text(p).startswith("Perpetual markets allow leveraged long")),
        "The remaining external check is a temporal holdout of future new owner–spender approvals.",
    )
    replace_para_text(
        by_prefix("Primary chain: All on-chain events"),
        "Primary chain: All on-chain events are drawn from Arbitrum One (chain ID 42161), an Ethereum Layer-2 rollup with dense DeFi activity and public log availability [53]. Restricting to a single chain avoids cross-chain address aliasing—the same private key controlling addresses on multiple chains would otherwise appear as unrelated nodes—and keeps gas-cost and latency regimes comparable across wallets. The chain is the sole empirical venue for this comparison.",
    )
    replace_para_text(
        by_prefix("Figure 3.1 summarizes the end-to-end flow from public logs to"),
        "Figure 3.1 summarizes the end-to-end flow from public logs to the research tables. Remote stages write immutable parquet; local stages are idempotent given those inputs and a single versioned configuration file.",
    )
    replace_para_text(
        by_prefix("Before comparing reputation rankings, it is useful to characterize"),
        "The matched cohort (n = 5,521) is wallets with non-zero endorsement- and transfer-graph connectivity in the observation window. Endorsement and transfer graphs differ by nearly an order of magnitude in edge count (14,727 versus 137,087), so efficiency and alignment claims are evaluated jointly.",
    )
    replace_para_text(
        by_prefix("Figure 4.1: Distribution of GMX V2 PositionDecrease close counts"),
        "Figure 4.1 is withdrawn. The matched cohort is defined by non-zero endorsement- and transfer-graph connectivity (n = 5,521).",
    )
    replace_para_text(
        by_prefix("Distribution of GMX V2 PositionDecrease close counts per wallet"),
        "The matched cohort is wallets with non-zero endorsement- and transfer-graph connectivity (n = 5,521).",
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
        "Matched cohort (connectivity)",
    )
    replace_para_text(
        by_exact("GMX V2 as a sampling frame"),
        "Matched cohort (connectivity)",
    )
    replace_para_text(
        try_find(lambda p: para_text(p).startswith("Trading success validation frame (GMX V2)")),
        "Matched cohort (connectivity)",
    )

    perp_body = try_find(
        lambda p: para_text(p).startswith('Perpetual futures (“perps”) are derivative'),
    )
    related = try_find(
        lambda p: para_text(p).strip() == "Related measurement traditions"
        and pstyle(p).startswith("Heading"),
    )
    if perp_body is not None and related is not None:
        perp_head = None
        cur = perp_body.getprevious()
        while cur is not None:
            if etree.QName(cur).localname == "p" and pstyle(cur).startswith("Heading"):
                perp_head = cur
                break
            cur = cur.getprevious()
        if perp_head is not None and "Perpetual markets" in para_text(perp_head):
            remove_between(perp_head, related, keep_start=False, keep_stop=True)

    toc_perp = try_find(
        lambda p: "Perpetual markets as a validation laboratory" in para_text(p),
    )
    if toc_perp is not None:
        remove_para(toc_perp)

    lof_pnl = try_find(
        lambda p: para_text(p).startswith("Distribution of GMX realized PnL summaries"),
    )
    lof_sr = try_find(
        lambda p: para_text(p).startswith("Distribution of GMX close success rates"),
    )
    if lof_pnl is not None and lof_sr is not None:
        remove_between(lof_pnl, lof_sr, keep_start=False, keep_stop=False)

    fig41 = by_prefix("Figure 4.1: Distribution of GMX V2 PositionDecrease close counts")
    if fig41 is None:
        fig41 = by_prefix("Figure 4.1 is withdrawn")
    bench = try_find(
        lambda p: para_text(p).strip() == "EndorseRank vs. AWP benchmark (Claim C1)",
    )
    if fig41 is not None and bench is not None:
        remove_between(fig41, bench, keep_start=True, keep_stop=True)
        replace_para_text(
            fig41,
            "The matched cohort (n = 5,521) has non-zero endorsement- and transfer-graph connectivity. Endorsement and transfer graphs differ by nearly an order of magnitude in edge count (14,727 versus 137,087), so efficiency and alignment claims are evaluated jointly.",
        )

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
        if p is None:
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


def apply_body_pass4(doc) -> None:
    """Strip remaining GMX / GF-PR / PositionDecrease narrative. Keep connectivity + holdout."""
    body = doc.find(qn("body"))

    def paras():
        return [p for p in body.iter(qn("p"))]

    def try_find(pred):
        try:
            return find_para(paras(), pred)
        except KeyError:
            return None

    def try_prefix(prefix: str, new: str) -> None:
        replace_para_text(
            try_find(lambda p: para_text(p).startswith(prefix)),
            new,
        )

    def try_exact(old: str, new: str) -> None:
        replace_para_text(
            try_find(lambda p: para_text(p).strip() == old),
            new,
        )

    replacements = [
        (
            "Keywords— DeFi, EndorseRank",
            "Keywords— DeFi, EndorseRank, Adaptive Weighted PageRank, On-Chain Reputation, ERC-20 allowance, temporal holdout, Arbitrum One, Kendall’s tau",
        ),
        (
            "Evaluation pipeline: public Arbitrum logs are extracted and decoded, reputation edges and GMX outcomes",
            "Evaluation pipeline: public Arbitrum logs are extracted and decoded, reputation edges are preprocessed, EndorseRank and AWP ranks are computed, allowance and transfer checks are evaluated, and LaTeX result fragments",
        ),
        (
            "PageRank wall-clock runtime versus cohort size (log x-axis). Solid lines: in-cohort scaling on the matched GMX sample",
            "PageRank wall-clock runtime versus cohort size (log x-axis). Solid lines: in-cohort scaling on the matched cohort (n ≤ 5,521). Dashed lines: expanded wallet pool (N = 31,612). EndorseRank remains approximately 9–10× faster than AWP",
        ),
        (
            "Dataset characteristics for the matched cohort (n = 5,521 wallets with ≥ 3 GMX",
            "Dataset characteristics for the matched cohort (n = 5,521 wallets with non-zero reputation-subgraph connectivity).",
        ),
        (
            "ank and AWP are social reputation graphs; GF-PR is an outcome-native GMX PnL",
            "EndorseRank and AWP are social reputation graphs on allowance and transfer edges.",
        ),
        (
            "star baseline (construct overlap on GMX proxies).",
            "Same-window checks are allowance versus transfer.",
        ),
        (
            "Domain alignment with inverse-risk proxies from GMX realized PnL",
            "Withdrawn inverse-risk alignment table (not a research claim).",
        ),
        (
            "Domain alignment with GMX V2 margin-trading success proxies",
            "Withdrawn trading-success alignment table (not a research claim).",
        ),
        (
            "matched GMX cohort).",
            "matched cohort).",
        ),
        (
            "GF-PRGainFlow PageRank",
            "AWPAdaptive Weighted PageRank LPLiquidity Provider",
        ),
        (
            "making, or passive receipt",
            "making, or passive receipt; an allowance is an explicit delegation of spending authority. Treating allowances as endorsement edges aligns PageRank’s citation metaphor [49] with a trust-like act that protocols already rely on for token interactions. Whether that semantic difference produces rankings that are merely different, or differently aligned with authorization and transfer checks, is an empirical question. This research answers that question on Arbitrum One using a matched sample of wallets with non-zero endorsement- and transfer-graph connectivity (n = 5,521).",
        ),
        (
            "1The matched cohort is the intersection",
            "1The matched cohort is wallets with non-zero connectivity in the reputation subgraphs (n = 5,521). Runtime scaling uses a larger expanded wallet pool (N = 31,612).",
        ),
        (
            "The research problem is therefore comparative and evaluative:",
            "The research problem is therefore comparative and evaluative: on an identical Arbitrum One wallet sample with non-zero endorsement- and transfer-graph connectivity, does EndorseRank produce wallet orderings that are construct-distinct from AWP, align credibly with allowance and transfer checks, and do so at substantially lower computational cost? The primary comparison is EndorseRank versus AWP.",
        ),
        (
            "Smart contract: Self-executing program code",
            "Smart contract: Self-executing program code deployed on a blockchain that enforces agreement terms without a trusted intermediary [9],[55]. In this research, smart contracts are the source of ERC-20 allowance logs and transfer logs.",
        ),
        (
            "On-chain credit risk: Observable adverse outcomes",
            "On-chain credit risk: Observable adverse outcomes such as authorization abuse or repeated losses on public blockchains [44]. This research uses allowance and transfer checks plus a temporal holdout, not loan-repayment ground truth.",
        ),
        (
            "GMX V2 perpetual swap position:",
            "Matched wallet cohort: The primary evaluation sample of n = 5,521 wallets with non-zero endorsement- and transfer-graph connectivity.",
        ),
        (
            "During empirical analysis, GF-PR (GainFlow PageRank) was added",
            "The remaining external check is a temporal holdout of future new owner–spender approvals (Chapters 3 and 4).",
        ),
        (
            "This dissertation thesis focuses on Arbitrum One",
            "This research focuses on Arbitrum One over the observation window 2025-12-01 to 2026-05-31. The primary empirical sample is a matched wallet cohort of n = 5,521 addresses with non-zero endorsement- and transfer-graph connectivity, comprising 14,727 EndorseRank edges and 137,087 AWP edges. Runtime scaling is reported on an expanded wallet pool (N = 31,612). Robustness checks examine damping sensitivity, top-token subgraphs, and sample-size sensitivity.",
        ),
        (
            "This thesis thesis focuses on Arbitrum One",
            "This research focuses on Arbitrum One over the observation window 2025-12-01 to 2026-05-31. The primary empirical sample is a matched wallet cohort of n = 5,521 addresses with non-zero endorsement- and transfer-graph connectivity, comprising 14,727 EndorseRank edges and 137,087 AWP edges. Runtime scaling is reported on an expanded wallet pool (N = 31,612). Robustness checks examine damping sensitivity, top-token subgraphs, and sample-size sensitivity.",
        ),
        (
            "Generalization beyond Arbitrum One, GMX V2",
            "Generalization beyond Arbitrum One and the six-month window is not claimed. Token-decimal normalization, price oracles, and permit-versus-approve coverage may affect edge weights. Adversarial manipulation of allowances or transfers remains a threat discussed in Chapter 5; Sybil-adjusted proxies partially address but do not eliminate that risk [17].",
        ),
        (
            "Chapter 2 reviews graph-based on-chain reputation, ERC-20 allowance semantics, and GMX V2",
            "Chapter 2 reviews graph-based on-chain reputation and ERC-20 allowance semantics. It develops the theoretical framework—hyperlink propagation, domain alignment, and computational complexity—that motivates the primary EndorseRank versus AWP comparison.",
        ),
        (
            "This chapter reviews the conceptual and technical foundations required to interpret EndorseRank, Adaptive Weighted PageRank (AWP), and the supplementary outcome-native reference GF-PR.",
            "This chapter reviews the conceptual and technical foundations required to interpret EndorseRank and Adaptive Weighted PageRank (AWP). It begins with blockchain and DeFi primitives for readers who may not specialize in distributed ledgers, then develops graph ranking theory, reputation-system lineage, ERC-20 allowance semantics, and rank-correlation statistics. A theoretical framework—hyperlink–citation propagation, domain alignment, and computational complexity—motivates the primary EndorseRank versus AWP comparison. Later sections supply a terminology guide, worked example, risk taxonomy, AWP in depth, method comparison, and open problems that lead into Chapters 3 and 4.",
        ),
        (
            "On Arbitrum One, GMX V2 PositionDecrease events define the matched sample",
            "On Arbitrum One, the matched sample is wallets with non-zero endorsement- and transfer-graph connectivity (n = 5,521) [23],[53]. Contemporaneous checks use allowance and transfer local statistics.",
        ),
        (
            "During the empirical phase, GF-PR (GainFlow PageRank) was added",
            "The remaining external check is a temporal holdout of future new owner–spender approvals.",
        ),
        (
            "Domain alignment framework: In measurement theory, construct alignment assesses how well an indicator tracks an observable outcome",
            "Domain alignment framework: In measurement theory, construct alignment assesses how well an indicator tracks an intended construct [14]. For rank-based reputation scoring, Spearman’s ρ and Kendall’s τ evaluate monotonic and pairwise ordering agreement without assuming a classification threshold [16]. Contemporaneous transfer and allowance statistics check graph coherence; a temporal holdout of future new approvals is the out-of-window check.",
        ),
        (
            "Supplementary reference: GF-PR on GMX PnL flow",
            "Temporal holdout: Scores frozen at t1; labels from t2 new owner–spender approvals on inbound spenders.",
        ),
        (
            "Validation proxy: Observable wallet metric (e.g., in-degree, GMX close-success count)",
            "Contemporaneous check: Local transfer or allowance statistics computed in the same window as the score [14].",
        ),
        (
            "Matched wallet cohort: The primary evaluation sample of n = 5,521 wallets with at least three GMX closes",
            "Matched wallet cohort: The primary evaluation sample of n = 5,521 wallets with non-zero endorsement- and transfer-graph connectivity.",
        ),
        (
            "31 23:59:59 UTC (six calendar months).",
            "31 23:59:59 UTC (six calendar months). Exclusive end timestamps in SQL use 2026-06-01 00:00:00 UTC so that the inclusive calendar end is 2026-05-31. This window is long enough for monthly-batched reputation extracts under BigQuery byte budgets and short enough that latest-allowance snapshots remain contemporaneous with transfer histories.",
        ),
        (
            "GMX events: Trading-success and risk proxies",
            "Reputation events: EndorseRank uses ERC-20 Approval logs. AWP uses ERC-20 Transfer logs. Both streams are wallet-filtered to the cohort under study.",
        ),
        (
            "HYPERLINK \\l \"_bookmark156\"[23]. Traders are identified",
            "The public log table is authoritative. Decoding is performed in the open pipeline [23],[53].",
        ),
        (
            "Matched cohort definition: The primary alignment sample is the intersection",
            "Matched cohort definition: The primary alignment sample is wallets with non-zero connectivity in the reputation subgraph induced by approval or transfer edges. After BigQuery extraction and preprocessing, this matched wallet cohort has size n = 5,521. Both EndorseRank and AWP are scored on the same seed",
        ),
        (
            "What is not in scope: The study does not ingest mempool data",
            "What is not in scope: The study does not ingest mempool data, off-chain order books, centralized-exchange account maps, or cross-chain bridges. It does not attempt entity resolution across multiple addresses controlled by one actor. The public log table is authoritative, and decoding is performed in the open pipeline.",
        ),
        (
            "Phase 1 (GMX validation stream):",
            "Phase 1 (reputation streams): Extract wallet-filtered ERC-20 Approval and Transfer events in monthly batches. The matched wallet cohort is the subset with non-zero approval or transfer connectivity (n = 5,521). Each month is an independent query with its own dry-run estimate and checkpoint, so a failure in one month does not invalidate prior months.",
        ),
        (
            "Phase 2 (reputation streams): For the GMX-eligible set",
            "Phase 2 (local evaluation): From cached parquet, compute reputation ranks, transfer and allowance checks, Spearman and Kendall alignment, computational benchmarks, and scaling/robustness extensions. No additional BigQuery scans are required once the Phase 1 extracts are available.",
        ),
        (
            "Figure 3.1: Evaluation pipeline: public Arbitrum logs are extracted and decoded, reputation edges and GMX outcomes",
            "Figure 3.1: Evaluation pipeline: public Arbitrum logs are extracted and decoded, reputation edges are preprocessed, EndorseRank and AWP ranks are computed, allowance and transfer checks are evaluated, and LaTeX result fragments are exported.",
        ),
        (
            "Operationally, Phase 1 scripts write GMX raw logs",
            "Operationally, Phase 1 scripts write monthly approval/transfer shards and consolidated latest-allowance and transfer-event tables.",
        ),
        (
            "GMX PositionDecrease: GMX V2 emits structured events",
            "Address and event decoding: ERC-20 Approval and Transfer logs are identified by standard topic-0 hashes and restricted to the evaluation wallet list.",
        ),
        (
            "Address normalization and units: All addresses are lower-cased",
            "Address normalization and units: All addresses are lower-cased before joins so that checksummed and non-checksummed hex forms collide correctly. Token amounts are stored as floating-point decimal-adjusted values for weighting; ranking uses relative magnitudes within a cohort rather than absolute USD conversion for allowance and transfer edges.",
        ),
        (
            "GF-PR is an outcome-native reference built only from GMX PositionDecrease",
            "The remaining external check is a temporal holdout of future new owner–spender approvals on t1 inbound spenders (n = 1,335).",
        ),
        (
            "Inverse risk (GMX PnL):",
            "Allowance checks: latest-allowance in-degree and related local statistics.",
        ),
        (
            "Trading success: GMX close outcomes",
            "Transfer checks: inbound transfer count and value statistics.",
        ),
        (
            "Let W be the matched cohort. For GMX-derived proxies",
            "Let W be the matched cohort. Allowance and transfer checks are defined on wallets with non-zero reputation-subgraph connectivity.",
        ),
        (
            "Let C(w) be the set of non-missing GMX closes",
            "Contemporaneous checks use allowance and transfer local statistics. Outcome-native close series are not used.",
        ),
        (
            "The primary definition of realized_gain_proxy",
            "Same-window claims use allowance and transfer checks. The external check is the temporal holdout under RQ4.",
        ),
        (
            "The expanded wallet pool Wpool unions the matched GMX cohort",
            "The expanded wallet pool Wpool unions the matched cohort with supplemental active addresses derived from the reputation subgraph, yielding N = |Wpool| = 31,612 addresses in this study. Supplemental addresses increase graph size for timing experiments. Runtime benchmarks at intermediate sizes use deterministic SHA256 subsampling with seed string benchmark-tier2-v1: wallets are ordered by",
        ),
        (
            "Alignment statistics are recomputed on staged subsamples drawn from the expanded wallet pool using the same deterministic seed. Subsamples include supplemental addresses without GMX",
            "Alignment statistics are recomputed on staged subsamples drawn from the expanded wallet pool using the same deterministic seed. Reported sample-size τ is interpreted primarily for transfer and allowance families on Wpool; primary claims remain on the matched wallet cohort (n = 5,521). Because rank correlations have sampling variability, modest movement in τ across sizes is expected; the robustness question is whether EndorseRank and AWP preserve their relative ordering on key graph-adjacent families.",
        ),
        (
            "GMX proxy definition variants",
            "Holdout label definition",
        ),
        (
            "All empirical tables in Chapter 4 are produced by an open evaluation pipeline.",
            "All empirical tables in Chapter 4 are produced by an open evaluation pipeline. After Phase 1 parquet artifacts are present, a single evaluation driver recomputes checks, alignment statistics, and benchmarks from those inputs. Observation window, damping, decay parameters, and benchmark seeds are collected in a single versioned configuration file. Fixture mode supports offline verification without cloud credentials.",
        ),
        (
            "The matched cohort is a purposeful sample, not a random sample of all Arbitrum addresses. El-igibility requires GMX activity",
            "The matched cohort is a purposeful sample, not a random sample of all Arbitrum addresses. Eligibility requires reputation-subgraph connectivity, so results speak to wallets with observable approval or transfer structure. Idle wallets, pure holders, and addresses that interact only through non-ERC-20 mechanisms are out of scope by design.",
        ),
        (
            "The matched cohort is a purposeful sample, not a random sample of all Arbitrum addresses. Eligibility requires GMX activity",
            "The matched cohort is a purposeful sample, not a random sample of all Arbitrum addresses. Eligibility requires reputation-subgraph connectivity, so results speak to wallets with observable approval or transfer structure. Idle wallets, pure holders, and addresses that interact only through non-ERC-20 mechanisms are out of scope by design.",
        ),
        (
            "Supplemental addresses in the expanded wallet pool (N = 31,612) increase coverage for runtime tests but do not automatically carry GMX labels.",
            "Supplemental addresses in the expanded wallet pool (N = 31,612) increase coverage for runtime tests. Alignment claims remain anchored to the matched cohort (n = 5,521), while scaling claims use the pool.",
        ),
        (
            "Privacy and anonymity: Arbitrum One addresses are pseudonymous identifiers",
            "Privacy and anonymity: Arbitrum One addresses are pseudonymous identifiers, not inherently linked to real-world identities [48]. Pseudonymity is not anonymity: determined adversaries can sometimes link addresses to persons through exchange deposits, public profiles, or clustering heuristics. This study deliberately refrains from such linkage. Collection is restricted to on-chain events—Approval and Transfer—with no scraping or integration of off-chain personal data such as IP addresses, exchange KYC records, social-media handles, or deanonymization graphs. No attempt was made to cluster addresses into real-world entities, to publish address-level rankings that could reasonably",
        ),
        (
            "Data minimization: Only fields required for graph construction and proxies are retained",
            "Data minimization: Only fields required for graph construction and checks are retained in processed tables (addresses, token amounts, timestamps). Raw logs are stored for auditability of the research pipeline but are not redistributed as a deanonymization aid. Query filters are wallet-scoped where possible to avoid indiscriminate full-chain dumps beyond the study design.",
        ),
        (
            "All primary results use an identical matched cohort of n = 5,521 wallets that satisfy both a GMX trading-activity filter",
            "All same-window results use an identical matched cohort of n = 5,521 wallets with non-zero connectivity in the reputation subgraphs. The holdout uses t1 inbound spenders (n = 1,335). Runtime scaling is evaluated on an expanded wallet pool of N = 31,612 addresses. Robustness checks vary PageRank damping, restrict the reputation graph to high-volume tokens, and recompute alignment at staged subsample sizes. Methodological definitions appear in Chapter 3. Claims are summarized in Section 4.8 and mapped to hypotheses and research questions in Table 1.3.",
        ),
        (
            "The matched cohort comprises n = 5,521 wallets with at least three GMX",
            "The matched cohort comprises n = 5,521 wallets with non-zero endorsement- and transfer-graph connectivity, drawn from six months of Arbitrum One BigQuery logs spanning 2025-12-01 through 2026-05-31. EndorseRank scores are computed on the latest-allowance endorsement graph Gapprove; AWP scores are computed on the time-decayed transfer graph Gtransfer. Same-window claims use transfer and allowance local statistics.",
        ),
        (
            "Table 4.1: Dataset characteristics for the matched cohort (n = 5,521 wallets with ≥ 3 GMX closes",
            "Table 4.1: Dataset characteristics for the matched cohort (n = 5,521 wallets with non-zero reputation-subgraph connectivity).",
        ),
        (
            "GMX PositionDecrease events (decoded)",
            "—",
        ),
        (
            "Min. GMX closes per wallet",
            "—",
        ),
        (
            "The matched-cohort design deliberately intersects two filters. The GMX activity filter",
            "The matched-cohort design requires non-zero reputation-subgraph connectivity so that both EndorseRank and AWP produce non-degenerate scores. The sample is large enough for stable Kendall τ estimates, yet small enough that full PageRank solves remain interactive on commodity hardware.",
        ),
        (
            "ensures that trading-success and inverse-risk proxies are defined",
            "Wallets with no approval edges and no transfer edges cannot be ranked meaningfully by either social method. The connectivity filter yields n = 5,521 wallets over the six-month window.",
        ),
        (
            "GMX trading activity in the matched cohort",
            "Matched cohort connectivity",
        ),
        (
            "Figure 4.1 shows GMX close counts per wallet.",
            "The matched cohort (n = 5,521) is wallets with non-zero endorsement- and transfer-graph connectivity. Endorsement and transfer graphs differ by nearly an order of magnitude in edge count (14,727 versus 137,087).",
        ),
        (
            "GMX closes per wallet (winsorized at 99th percentile)",
            "—",
        ),
        (
            "The close-count figure and the edge-count gap",
            "The edge-count gap in the dataset table fixes a sample constraint: endorsement and transfer graphs differ by nearly an order of magnitude in edge count (14,727 versus 137,087), so efficiency and alignment claims must be evaluated jointly. The matched cohort is large enough for stable rank statistics (n = 5,521).",
        ),
        (
            "The runtime advantage is not merely a constant-factor curiosity",
            "The runtime advantage is not merely a constant-factor curiosity on a single cohort size. If EndorseRank’s edge set remains substantially smaller than AWP’s as the wallet pool grows, the speedup should persist under staged scaling. Table 4.3 reports runtime scaling on an expanded wallet pool of N = 31,612 addresses: the matched cohort unioned with supplemental active wallets drawn from the reputation subgraph. Deterministic SHA256 subsampling yields staged cohorts at n = 10,000 and at full pool size. In-cohort scaling for n ≤ 5,521 is reported in Appendix 8.1 (Table 8.1).",
        ),
        (
            "Figure 4.4: PageRank wall-clock runtime versus cohort size (log x-axis). Solid lines: in-cohort scaling on the matched GMX sample",
            "Figure 4.4: PageRank wall-clock runtime versus cohort size (log x-axis). Solid lines: in-cohort scaling on the matched cohort (n ≤ 5,521). Dashed lines: expanded wallet pool (N = 31,612). EndorseRank remains approximately 9–10× faster than AWP at n = 10,000 (≈ 10.4×) and at full pool size (≈ 9.4×).",
        ),
        (
            "active wallets that are not GMX-matched",
            "active wallets outside the matched cohort; proxies and score supports therefore change with the sample definition. The relevant robustness claim is ordinal and comparative: the construct-specific winners and the runtime advantage persist under pool expansion and staged subsampling. In-cohort scaling detail for the matched sample alone appears in Appendix 8.1.",
        ),
        (
            "Table 4.7: Mean Kendall τ by proxy family across 3 PageRank methods",
            "Table 4.7: Mean Kendall τ for allowance and transfer checks (n = 5,521). Runtime = mean PageRank wall time. EndorseRank and AWP are social reputation graphs.",
        ),
        (
            "GF-PR is weak on transfer proxies (family mean 0.246)",
            "Same-window transfer alignment remains a construct check for AWP, not a substitute for the holdout.",
        ),
        (
            "Inverse-risk family (GMX PnL)",
            "Allowance and transfer checks",
        ),
        (
            "Table 4.10: Domain alignment with inverse-risk proxies from GMX realized PnL",
            "Table 4.10 is withdrawn from the claims. Same-window evidence is allowance versus transfer.",
        ),
        (
            "Table 4.12: Domain alignment with GMX V2 margin-trading success proxies",
            "Table 4.12 is withdrawn from the claims. The external check is the spender holdout.",
        ),
        (
            "cially instructive. It shows that the evaluation pipeline can recover extremely high τ",
            "The holdout is the out-of-window check. Same-window allowance tau is an intended-construct check.",
        ),
        (
            "Hybrid deployments are feasible: EndorseRank for continuous authorization-aware monitoring, AWP for periodic transfer-hub audits, and GMX-linked outcome metrics",
            "Hybrid deployments are feasible: EndorseRank for continuous authorization-aware monitoring and AWP for periodic transfer-hub audits [23],[53]. The open pipeline enables cross-protocol replication on any ERC-20 chain with allowance logs (Appendix 8.1). Integration with live risk oracles and governance tooling remains future work (Chapter 6), but the efficiency profile of En-",
        ),
        (
            "Perpetual DEX operators: Protocols such as GMX V2 earn primarily from trading fees",
            "Protocol operators: Operators face a continuous decision problem: which wallets to prioritize for monitoring or feature access when reputation must be refreshed frequently. EndorseRank fits this loop because allowance τ = 0.355 aligns the score with authorization activity and PageRank completes in 2.105 s on the matched cohort, enabling frequent updates without transfer-history aggregation.",
        ),
        (
            "Cohort selection: The matched wallet cohort requires at least three GMX closes",
            "Cohort selection: The matched wallet cohort requires non-zero reputation-subgraph connectivity (n = 5,521). Results may not extend to addresses absent from allowance and transfer subgraphs.",
        ),
        (
            "Single protocol and chain: Evidence is limited to Arbitrum One and GMX V2.",
            "Single chain: Evidence is limited to Arbitrum One. Generalization to other Layer-1 or Layer-2 chains requires re-validation [28],[53],[59].",
        ),
        (
            "31,612) supports efficiency claims at larger n; alignment results remain anchored to the matched cohort with GMX outcomes.",
            "31,612) supports efficiency claims at larger n; alignment results remain anchored to the matched connectivity cohort. Efficiency gains should not be assumed to preserve the same τ profile at arbitrary population sizes without further alignment studies.",
        ),
        (
            "Cross-protocol and cross-chain validation: Replication on other perpetual markets",
            "Cross-protocol and cross-chain validation: Replication on other Layer-2 or Layer-1 networks would test whether the allowance–transfer trade-off generalizes beyond Arbitrum One [53],[59]. Where lending default labels are denser, credit-ground-truth validation can complement the holdout used here [26],[44].",
        ),
        (
            "Trading-success labels: Decode GMX V2 PositionDecrease events",
            "Holdout labels: After scores freeze at 28 February 2026, new owner–spender pairs in March–May 2026 are the external check on t1 inbound spenders (n = 1,335).",
        ),
        (
            "ERC-20 Approval and Transfer events are identified by their standard topic-0 hashes and re-stricted to logs whose owner/spender or from/to address lies in the evaluation wallet list, so scan cost scales with the cohort rather than the full chain. Monthly batching keeps each query under the operational byte cap. GMX V2 events are read from the EventEmitter contract at",
            "ERC-20 Approval and Transfer events are identified by their standard topic-0 hashes and restricted to logs whose owner/spender or from/to address lies in the evaluation wallet list, so scan cost scales with the cohort rather than the full chain. Monthly batching keeps each query under the operational byte cap. Representative SQL patterns appear in Appendix 8.2.",
        ),
        (
            "Table 8.1: In-cohort runtime scaling (SHA256 seed benchmark-scale-v1; n ≤ 5,521 matched GMX cohort).",
            "Table 8.1: In-cohort runtime scaling (SHA256 seed benchmark-scale-v1; n ≤ 5,521 matched cohort).",
        ),
        (
            "Min. GMX closes3Cohort eligibility Observation window2025-12-01 – 2026-05-31 UTC inclusive",
            "Cohort eligibility: non-zero reputation-subgraph connectivity. Observation window: 2025-12-01 – 2026-05-31 UTC inclusive.",
        ),
        (
            "GMX PositionDecrease extraction pattern",
            "Approval and Transfer extraction pattern",
        ),
        (
            "GMX V2 events are read from the EventEmitter contract.",
            "ERC-20 Approval and Transfer events are read from the public BigQuery log table. The pipeline filters on standard topic-0 hashes and the evaluation wallet list. Wallets without approval or transfer connectivity are excluded from the matched cohort.",
        ),
        (
            "GMX emitter address and topic filters;",
            "Approval and Transfer topic filters;",
        ),
        (
            "GMX closes (decoded)",
            "—",
        ),
        (
            "Table 8.4 reports family-level mean Kendall τ for seven methods",
            "Appendix 8.4 runtime and allowance/transfer checks remain available for the social methods. Outcome-native columns are not interpreted as claims.",
        ),
        (
            "that results generalize beyond Arbitrum One, GMX V2",
            "that results generalize beyond Arbitrum One and the study window without replication;",
        ),
        (
            "Decoded GMX close events with PnL and liquidation flags.",
            "Decoded ERC-20 Approval and Transfer events used for graph construction.",
        ),
        (
            "GF-PR was computed during exploratory work",
            "The external check that remains is the spender holdout under RQ4 (EndorseRank tau = 0.479, CI 0.426–0.529; AWP 0.044).",
        ),
        (
            "This research does not predict trading profit",
            "The remaining external check is a temporal holdout of future new owner–spender approvals.",
        ),
        (
            "SRQ1 is withdrawn. GF-PR is not a research claim.",
            "SRQ1 is withdrawn. The external check is the temporal holdout under RQ4.",
        ),
        (
            "GF-PR is not a claim and is not a third peer social method.",
            "The primary comparison is EndorseRank versus AWP. The external check is the temporal holdout.",
        ),
        (
            "Withdrawn: SC1 / GF-PR is not a research claim.",
            "Withdrawn: SC1 is not a research claim. The external check that remains is the spender holdout under RQ4.",
        ),
        (
            "SRQ1 / SC1 are withdrawn. GF-PR is not a deployable social reputation score",
            "SRQ1 / SC1 are withdrawn. The external check that remains is the spender holdout.",
        ),
        (
            "Temporal holdout: t1 scores versus t2 new approvals on inbound spenders (EndorseRank tau = 0.479, CI 0.426–0.529; AWP 0.044). GF-PR is excluded from the claims.",
            "Temporal holdout: t1 scores versus t2 new approvals on inbound spenders (EndorseRank tau = 0.479, CI 0.426–0.529; AWP 0.044).",
        ),
        (
            "I do not read social-method trading-success tau against a GF-PR ceiling.",
            "The external check that remains is the spender holdout.",
        ),
        (
            "GF-PR is not used as a diagnostic ceiling in the claims.",
            "The remaining validation logic separates same-window allowance and transfer checks from the temporal holdout.",
        ),
        (
            "Trading-success alignments (formerly 0.096 / 0.179) are dropped from the claims.",
            "Same-window checks remain allowance versus transfer. The external check is the spender holdout.",
        ),
        (
            "Trading-success families are not used to support H2.",
            "H2 is supported in the construct-specific form: allowance versus transfer.",
        ),
    ]
    for prefix, new in replacements:
        try_prefix(prefix, new)

    try_exact("GMX V2 as a sampling frame", "Matched cohort (connectivity)")
    try_exact("GMX", "—")
    try_exact("365,488", "—")
    try_exact("GMX PositionDecrease extraction pattern135", "Approval and Transfer extraction")

    # Phrase sweep on leftover body (keep the GMX bibliography item).
    phrases = (
        ("defined by GMX activity as a sampling frame only", "with non-zero endorsement- and transfer-graph connectivity"),
        ("GMX V2 activity is a sampling frame (365,488 decoded PositionDecrease events; at least three closes). ", ""),
        ("GMX V2 activity defines the matched sample (at least three PositionDecrease closes). ", ""),
        ("at least three GMX V2 PositionDecrease closes", "non-zero endorsement- and transfer-graph connectivity"),
        ("at least three GMX PositionDecrease closes", "non-zero endorsement- and transfer-graph connectivity"),
        ("at least three GMX PositionDecrease events", "non-zero endorsement- and transfer-graph connectivity"),
        ("at least three GMX closes", "non-zero endorsement- and transfer-graph connectivity"),
        ("≥ 3 GMX closes", "non-zero reputation-subgraph connectivity"),
        ("; 365,488 decoded closes", ""),
        ("; 365,488 decoded PositionDecrease events", ""),
        ("; 365,488 PositionDecrease events", ""),
        ("365,488 decoded closes", "the connectivity cohort"),
        ("365,488 decoded PositionDecrease events", "the connectivity cohort"),
        ("365,488 PositionDecrease events", "the connectivity cohort"),
        (" and GMX V2 perpetual trading", ""),
        (", GMX V2,", ","),
        (" and GMX V2", ""),
        ("including GMX V2 [23]", "[23]"),
        ("GMX-matched", "matched"),
        ("matched GMX sample", "matched cohort"),
        ("matched GMX cohort", "matched cohort"),
        ("GMX-qualified matched cohort", "matched cohort"),
        ("with GMX outcomes", ""),
        ("and GMX outcomes", ""),
        ("GMX-linked outcome metrics as separate risk dash-boards rather than as substitutes for social scores ", ""),
        ("GMX-eligible set", "evaluation wallet list"),
        ("PositionDecrease events that serve only as an activity filter", "public Approval and Transfer logs"),
        ("whose PositionDecrease events are used only as an activity filter", "the sole empirical venue for this comparison"),
        ("circular with GMX profit-and-loss", "not used as a research claim"),
        ("from GMX realized PnL", ""),
        ("from the same GMX profit-and-loss stream", "from outcome streams"),
        ("from the same GMX PositionDecrease stream", "from outcome streams"),
        ("outcome-native GMX PnL star baseline", "withdrawn outcome-native baseline"),
        ("construct overlap on GMX proxies", "not a social-graph claim"),
        ("GMX success by construction", "outcome columns that are not claims"),
        ("and GMX V2. Generaliza-tion", ". Generalization"),
        ("beyond Arbitrum One and GMX V2", "beyond Arbitrum One"),
        ("Cross-chain GMX deployments and alternative L2s offer natural replication sites with comparable event schemas.", "Alternative L2s offer natural replication sites."),
        ("GMX V2 closes define the matched sample. ", ""),
        ("It is not a trading-success test. ", ""),
        ("Trading-success, inverse-risk, liquidation, and GF-PR alignments are not claims.", "Contemporaneous checks use allowance and transfer local statistics."),
        ("Trading-success and GF-PR alignments are not claims.", ""),
        ("Trading-success families are not claims.", ""),
        ("GF-PR and trading-success families are excluded from the research claims. ", ""),
        ("GF-PR and trading-success alignments are excluded from the claims.", ""),
    )
    for p in paras():
        old = para_text(p)
        if old.startswith("GMX. (n.d.)"):
            continue
        new = old
        for a, b in phrases:
            if a in new:
                new = new.replace(a, b)
        if new != old:
            replace_para_text(p, new)


def apply_body_pass5(doc) -> None:
    """Second sweep: leftover GF-PR/GMX headings, notes, and exact table cells."""
    body = doc.find(qn("body"))

    def paras():
        return [p for p in body.iter(qn("p"))]

    def replace_all_exact(old: str, new: str) -> None:
        for p in paras():
            if para_text(p).strip() == old:
                replace_para_text(p, new)

    def replace_all_prefix(prefix: str, new: str) -> None:
        for p in paras():
            if para_text(p).startswith(prefix):
                replace_para_text(p, new)

    def replace_all_contains(needle: str, new: str) -> None:
        for p in paras():
            t = para_text(p)
            if t.startswith("GMX. (n.d.)"):
                continue
            if needle in t:
                replace_para_text(p, new)

    prefix_map = [
        ("Supplementary extension (GF-PR)", "Temporal holdout of future new approvals"),
        ("Supplementary extension: outcome-native reference (GF-PR)", "Temporal holdout of future new approvals"),
        ("Supplementary GF-PR graph (extension)", "Temporal holdout of future new approvals"),
        ("Supplementary GF-PR ceiling analysis", "Temporal holdout of future new approvals (RQ4)"),
        ("SRQ1 / SC1 — GF-PR ceiling", "RQ4 — temporal holdout of future new approvals"),
        (" Family-level mean Kendall τ heatmap for EndorseRank, AWP, and supplementary GF-PR", "Family-level mean Kendall τ heatmap for EndorseRank and AWP on the matched cohort (n = 5,521). EndorseRank peaks on allowance;"),
        ("AWP peaks on transfer among social methods; GF-PR peaks", "AWP peaks on transfer. Same-window checks are allowance versus transfer."),
        ("Mean Kendall τ by proxy family: EndorseRank, AWP, and GF-PR", "Mean Kendall τ by proxy family: EndorseRank and AWP (n = 5,521)."),
        ("Note: GF-PR", "Note: The external check is the temporal holdout of future new approvals on t1 inbound spenders."),
        ("SRQ1What does GF-PR ceiling imply", "RQ4. After scores are frozen at 28 February 2026, does EndorseRank predict t2 new owner–spender approvals?"),
        ("SC1Supplementary GF-PR", "C4 Spender holdout of future new approvals"),
        ("Temporal holdout, not GF-PR:", "Temporal holdout: The external check is future new approvals on t1 inbound spenders."),
        ("on this chain for reliable ground-truth validation.", "Constructs and ethics are defined in Chapters 1 and 3. Same-window transfer alignment does not diminish EndorseRank’s allowance-specific validity or runtime advantage. The external check is the temporal holdout. Extended baselines archived for future comparison are excluded from the main narrative (Appendix 8.1)."),
        ("Figure 2.3 presents the conceptual model mapping the primary EndorseRank–AWP comparison to H1–H3 and RQ1–RQ4. GF-PR", "Figure 2.3 presents the conceptual model mapping the primary EndorseRank–AWP comparison to H1–H3 and RQ1–RQ4. The remaining external check is the temporal holdout."),
        ("Supplementary role of GF-PR:", "Holdout, not outcome ranking: H1 and H3 concern EndorseRank and AWP only. H2/RQ2 compares contemporaneous allowance and transfer checks. RQ4 is a time-split test of future new owner–spender approvals on the spender cohort."),
        ("Primary comparison: EndorseRank vs AWPTrading Success Alignment", "Primary comparison: EndorseRank vs AWP. Computational efficiency H3/RQ3. Reputation structure H1/RQ1. Construct checks H2/RQ2. Temporal holdout RQ4."),
        ("Supplementary: GF-PR outcome-native ceiling (SRQ1)", "Temporal holdout of future new approvals (RQ4)"),
        ("Figure 2.3: Conceptual model:", "Figure 2.3: Conceptual model: primary EndorseRank vs. AWP comparison mapped to reputation structure (H1/RQ1), construct checks (H2/RQ2), computational efficiency (H3/RQ3), and the temporal holdout of future new approvals (RQ4)."),
        ("Construct overlap: When a method’s input graph", "Contemporaneous check: Local transfer or allowance statistics computed in the same window as the score."),
        ("EndorseRank addresses (1)–(3) directly, contributes a diagnostic for (4) via GF-PR", "EndorseRank addresses (1)–(4) with allowance edges, contemporaneous checks, runtime benchmarks, and a temporal holdout, and analyzes"),
        ("This chapter specifies the empirical design used to compare EndorseRank and Adaptive Weighted PageRank (AWP) as social reputation scores on Arbitrum One.", "This chapter specifies the empirical design used to compare EndorseRank and Adaptive Weighted PageRank (AWP) as social reputation scores on Arbitrum One. The design covers notation, data sources, a two-phase collection strategy, pipeline architecture, event decoding, graph construction algorithms, contemporaneous checks, statistical tests, computational benchmarks, scaling and robustness extensions, reproducibility, and ethics. The primary comparison is between EndorseRank on the ERC-20 allowance graph and AWP on the time-decayed transfer graph [16],[49]."),
        ("Primary versus supplementary scope:", "Primary scope: claims C1–C4 and hypotheses H1–H3 concern EndorseRank and AWP. RQ4 is the temporal holdout."),
        ("GGF-PRSupplementary GF-PR star graph", "Gapprove Directed endorsement graph from latest ERC-20 allowances"),
        ("εloss, εliqGF-PR sink additives (0.1, 1.0)", "—"),
        ("Traders are identified via the event account field.", "The public log table is authoritative. Decoding is performed in the open pipeline [23],[53]. Lending-protocol default labels remain out of scope."),
        ("The additives εloss and εliq break ties", "Same-window checks use allowance and transfer local statistics. Outcome-native sink additives are not used."),
        ("Supplementary evaluation includes GF-PR only for SRQ1", "Supplementary evaluation is the temporal holdout under RQ4. Lending-protocol default labels remain out of scope. Packin and Lev-Aretz[48] caution that decentralized credit scores can become opaque; the design counters opacity by publishing explicit formulas and by separating same-window checks from the holdout."),
        ("These metrics support sensitivity analyses and GF-PR diagnostics", "These metrics support sensitivity analyses but are not part of the primary claims."),
        ("Cohorts: The primary benchmark uses the matched wallet cohort (n = 5,521). Scaling benchmarks use deterministic subsamples of the expanded wallet pool (Section 3.12). GF-PR runtime", "Cohorts: The primary benchmark uses the matched wallet cohort (n = 5,521). Scaling benchmarks use deterministic subsamples of the expanded wallet pool (Section 3.12)."),
        ("Fairness and transparency: Graph reputation systems can systematically undervalue new entrants", "Fairness and transparency: Graph reputation systems can systematically undervalue new entrants, low-volume participants, or wallets that avoid public approvals [48]. EndorseRank and AWP were therefore audited for such structural biases: allowance graphs favor addresses that receive spending authority; transfer graphs favor addresses embedded in value-flow networks. Limitations—including cold-start effects and Sybil susceptibility of approval graphs—are discussed in Chapter 5. All code paths, parameter choices, and evaluation metrics are documented in the open pipeline (Appendix 8.1) to enable peer review and independent replication."),
        ("Summary of methodological commitments:", "Summary of methodological commitments: The design fixes the chain, window, cohort rules, graph formulas, check definitions, and statistical tests before interpreting results. Primary claims compare only EndorseRank and AWP on the matched wallet cohort and the spender holdout; the expanded pool and robustness sweeps test efficiency and stability. Chapter 4 reports the empirical outcomes of this protocol."),
        ("GF-PR runtime (1.461 s) is reported", "The primary efficiency comparison is EndorseRank versus AWP on wallet-to-wallet social graphs (2.105 s versus 18.711 s)."),
        ("Claims C2 and C3 address whether EndorseRank and AWP achieve credible domain alignment", "Claims C2 and C3 address whether EndorseRank and AWP achieve credible domain alignment and whether winners are construct-specific. Same-window evidence is allowance versus transfer."),
        ("Figure 4.6 provides a compact visual summary of family-level alignment.", "Figure 4.6 provides a compact visual summary of family-level alignment. The heatmap makes the construct-specific pattern immediate: EndorseRank’s strongest cell is allowance; AWP’s strongest cell is transfer."),
        ("Figure 4.6: Family-level mean Kendall τ heatmap for EndorseRank, AWP, and supplementary GF-PR", "Figure 4.6: Family-level mean Kendall τ heatmap for EndorseRank and AWP on the matched cohort (n = 5,521). EndorseRank peaks on allowance; AWP peaks on transfer."),
        ("The exported summary also includes a liquidation-related column and the GF-PR row.", "The primary narrative of this section is the EndorseRank–AWP contrast across transfer and allowance checks."),
        ("The following subsections report Spearman ρ and Kendall τ for each proxy within family.", "The following subsections report Spearman ρ and Kendall τ for allowance and transfer checks. All checks are oriented so that higher values imply higher expected reputation before correlation, following Do et al.[16] and the operational definitions in Chapter 3."),
        ("I do not use GF-PR, trading-success, or inverse-risk alignments as supporting evidence.", "Same-window allowance tau is an intended-construct check; the external check is the spender holdout."),
        ("GF-PR’s near-identity with realized-gain", "Same-window checks remain allowance versus transfer. The external check is the spender holdout."),
        ("The ceiling is therefore a diagnostic for evaluation design", "The holdout is the out-of-window check. Same-window allowance tau is an intended-construct check."),
        ("The near-perfect GF-PR alignment", "The holdout is the out-of-window check."),
        ("In summary, the matched-cohort evaluation supports a coherent empirical narrative.", "In summary, the matched-cohort evaluation supports a coherent empirical narrative. EndorseRank is substantially faster than AWP because Gapprove is an order of magnitude sparser than Gtransfer. The two methods produce related but distinct rankings (inter-method τ = 0.316) and win on different checks: EndorseRank on allowance, AWP on transfer. Robustness checks do not overturn these patterns."),
        ("What the chapter does not claim is equally important.", "The contribution is a construct-aware comparison: EndorseRank offers a sparse, authorization-native ranking that is much cheaper to compute, aligns with allowance checks (τ = 0.355), diverges moderately from AWP, and predicts later new approvals on the spender holdout."),
        ("Chapter 5 interprets these findings against RQ1–RQ4 and discusses implications, threats to validity, and limitations. Trading-success and GF-PR", "Chapter 5 interprets these findings against RQ1–RQ4 and discusses implications, threats to validity, and limitations."),
        ("Trading-success, inverse-risk, liquidation, and malicious-spender alignments are excluded from the findings. GMX activity remains a sampling frame only.", "Same-window findings use allowance and transfer checks. The out-of-window check is the temporal holdout of future new approvals."),
        ("GF-PR is circular with trading-success", "The external check is the temporal holdout of future new approvals, not an outcome-native ceiling."),
        ("Non-claim: GF-PR shares input semantics", "Same-window checks are allowance versus transfer. The external check is the temporal holdout."),
        ("The practical upshot is modest and actionable.", "The practical upshot is modest and actionable. If a protocol or researcher needs a fast, auditable score of who is trusted to spend, EndorseRank is a credible instrument on Arbitrum One data of the kind studied here. If the goal is to find transfer hubs, AWP remains stronger among social methods."),
        ("Reputation graphs and scores: Extract ERC-20 Approval and Transfer logs", "Reputation graphs and scores: Extract ERC-20 Approval and Transfer logs for cohort wallets in monthly batches (per-query dry-run and a 150 GiB abort cap). Build the latest-allowance endorsement graph and the time-decayed transfer graph, then compute EndorseRank and AWP scores by power iteration (damping d = 0.85, tolerance 10−8, at most 300 iterations)."),
        ("Table 8.2 restates family-level mean τ from Table 4.7", "Table 8.2 restates family-level mean τ from Table 4.7 in columnar form for EndorseRank and AWP. The main narrative uses Table 4.7."),
        ("Table 8.2: Mean Kendall τ by proxy family: EndorseRank, AWP, and GF-PR", "Table 8.2: Mean Kendall τ by proxy family: EndorseRank and AWP (n = 5,521)."),
        ("GF-PR loss εloss0.1Ordinary loss edge boost", "—"),
        ("GF-PR liquidation εliq1.0Liquidation edge boost", "Expanded pool subsample seed benchmark-tier2-v1. Deterministic SHA256 seed."),
        ("GMX PositionDecrease extraction pattern", "Approval and Transfer extraction pattern"),
        ("Identify whether a row is a social method (EndorseRank, AWP) or the supplementary GF-PR reference.", "Identify whether a row is EndorseRank or AWP."),
        ("Treat GF-PR highs on trading-success and inverse-risk as construct-overlap diagnostics (SRQ1).", "Treat the spender holdout as the external check (RQ4)."),
        ("Cronbach and Meehl[14] distinguish criterion-related validity from construct validity.", "Cronbach and Meehl[14] distinguish criterion-related validity from construct validity. In the absence of a gold-standard default label, this research pursues a construct-oriented strategy: each method is tested against checks that operationalize its intended meaning (allowance receipt for EndorseRank; inbound transfer activity for AWP). High within-construct τ supports interpretation; low cross-construct τ is not automatically failure—it may indicate discriminant validity."),
        ("GF-PR trading-success mean τ", "—"),
        ("GF-PR inverse-risk mean τ", "—"),
        ("GF-PR’s dominance on outcome families remains a construct-overlap warning, identical to Chapter 4.", "Same-window evidence remains allowance versus transfer, identical to Chapter 4."),
        ("Focusing the dissertationthesis on EndorseRank, AWP, and supplementary GF-PR serves three goals:", "Focusing this research on EndorseRank and AWP serves three goals:"),
        ("Honest use of GF-PR:", "Honest use of the holdout: The external check is future new approvals, not an outcome-native ceiling."),
        ("The decision to keep only EndorseRank, AWP, and supplementary GF-PR in Chapters 4–5 was made after inspecting the seven-method and six-Aave matrices. Criteria were:", "The decision to keep only EndorseRank and AWP in Chapters 4–5 keeps the primary comparison focused. Criteria were:"),
        ("Under these criteria, EndorseRank (allowance), AWP (transfer), and GF-PR (outcome-native ceil-ing) form a minimal sufficient set.", "Under these criteria, EndorseRank (allowance) and AWP (transfer) form a minimal sufficient set. Archive tables remain available for readers who want the broader landscape without diluting the primary claims."),
        ("Statement: GF-PR bounds trading-outcome alignment via construct overlap.", "Statement: The external check is the temporal holdout of future new approvals."),
        ("Evidence: Table 4.7 row GF-PR:", "Evidence: spender holdout, EndorseRank tau = 0.479 (CI 0.426–0.529); AWP 0.044."),
        ("that GF-PR is a deployable social reputation score;", "that an outcome-native score is a deployable social reputation score;"),
        ("Merged wallet-ranking table — scores for ER, AWP, GF-PR.", "Merged wallet-ranking table — scores for EndorseRank and AWP."),
        ("This dissertationthesis focuses on Arbitrum One", "This research focuses on Arbitrum One over the observation window 2025-12-01 to 2026-05-31. The primary empirical sample is a matched wallet cohort of n = 5,521 addresses with non-zero endorsement- and transfer-graph connectivity, comprising 14,727 EndorseRank edges and 137,087 AWP edges. Runtime scaling is reported on an expanded wallet pool (N = 31,612)."),
        ("This dissertation thesis focuses on Arbitrum One", "This research focuses on Arbitrum One over the observation window 2025-12-01 to 2026-05-31. The primary empirical sample is a matched wallet cohort of n = 5,521 addresses with non-zero endorsement- and transfer-graph connectivity, comprising 14,727 EndorseRank edges and 137,087 AWP edges. Runtime scaling is reported on an expanded wallet pool (N = 31,612)."),
    ]
    for prefix, new in prefix_map:
        replace_all_prefix(prefix, new)

    replace_all_exact("GF-PR", "—")
    replace_all_exact("GMX", "—")
    replace_all_exact("365,488", "—")
    replace_all_exact("GF-PR (supp.)", "—")

    # Concatenated table blobs that still name GMX/GF-PR: drop the leftover tokens only.
    token_swaps = (
        ("GF-PR", "—"),
        ("GMX", "—"),
        ("PositionDecrease", "Approval/Transfer"),
        ("365,488", "—"),
    )
    for p in paras():
        old = para_text(p)
        if old.startswith("GMX. (n.d.)"):
            continue
        new = old
        for a, b in token_swaps:
            if a in new:
                new = new.replace(a, b)
        if new != old:
            replace_para_text(p, new)

    leftover_prefix = [
        ("RQ4Transfer vs. trading-success validation frame", "RQ4 Temporal holdout of future new approvals"),
        ("Transfer and allowance families are graph-adjacent:", "Transfer and allowance families are graph-adjacent: they are computed from the same event classes that build Gtransfer and Gapprove, but they are simple local statistics (degree and value sums) rather than global PageRank scores. Strong alignment of AWP with transfer checks, or of EndorseRank with allowance checks, is therefore evidence of within-construct coherence."),
        ("w with realized PnL x (field basePnlUsd):", "Contemporaneous checks use allowance and transfer local statistics."),
        ("Equation (3.10) sums absolute loss magnitudes", "Same-window claims use allowance and transfer checks. Outcome-native close series are not used."),
        ("For trading-success robustness, realized_gain_proxy", "Robustness checks vary damping, top-token subgraphs, and sample size. Primary claims remain on allowance versus transfer and the spender holdout."),
        ("Reading Table 4.7 requires care on two points.", "Reading Table 4.7 requires care. Family means average heterogeneous checks. Primary-construct correlations (EndorseRank with allowance; AWP with transfer) confirm that PageRank recovers the graph signal it was given. EndorseRank’s moderate transfer τ = 0.333 is a secondary axis. The external check is the spender holdout (τ = 0.479 versus AWP 0.044)."),
        ("The out-of-window check is not trading-success tau.", "On the holdout spender cohort (n = 1,335), EndorseRank aligns with future new approvers at Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529); AWP is 0.044. That is the same endorsement construct in the future tense."),
        ("RQ4: Transfer versus trading-success validation frames", "RQ4: Temporal holdout of future new approvals"),
        ("RQ4 asks whether t1 scores predict t2 new owner–spender approvals on inbound spenders. On the spender cohort (n = 1,335), EndorseRank Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529); AWP is 0.044. That is a time-split test of the endorsement construct, not a transfer-versus-trading-success contest.", "RQ4 asks whether t1 scores predict t2 new owner–spender approvals on inbound spenders. On the spender cohort (n = 1,335), EndorseRank Kendall tau = 0.479 (bootstrap 95% CI 0.426–0.529); AWP is 0.044."),
        ("alignment is therefore evidence of construct overlap", "The external check that remains is the spender holdout."),
        ("Protocols that emphasize explicit spending authorization", "Protocols that emphasize explicit spending authorization—token vaults, allowance-gated integrations, or risk engines that treat approvals as trust acts—may prefer EndorseRank. The method’s allowance τ = 0.355, sparse graph (14,727 edges), and 2.105 s PageRank time support frequent recomputation. Pool scaling (≈ 10.4× at n = 10,000; ≈ 9.4× at N = 31,612) indicates that the efficiency advantage persists beyond the matched cohort."),
        ("The practical value of EndorseRank and AWP is not that either score predicts trading profit", "The practical value of EndorseRank and AWP is that both supply a cheap, standardized, and independently recomputable ordinal signal that protocols can plug into operational decisions. Value capture is hypothesized to run through fees, utilization, and monitoring cost, rather than through reducing collateral."),
        ("Lending protocols: Lending markets seek higher capital utilization", "Lending protocols: Lending markets seek higher capital utilization without abandoning collateralization [5],[26]. Reputation can enter as an auxiliary signal for interest-rate or fee tiers and review cadence on already-collateralized positions, not as a substitute for collateral. EndorseRank is the natural social input when the protocol already relies on ERC-20 approvals for deposits and borrows (Section 2.7)."),
        ("the product differentiator relative to opaque machine-learning scores [48]. Providers should disclose weak trading-success alignment", "the product differentiator relative to opaque machine-learning scores [48]. Providers should disclose Sybil exposure alongside any dashboard that surfaces ranks."),
        ("Ethically, scores must not be presented as identity", "Ethically, scores must not be presented as identity, creditworthiness in the consumer-lending sense, or proof of unique personhood [17]. They are ordinal indicators of on-chain graph position under specified edge semantics. Deployments that gate access to financial services should disclose the graph definition, observation window, and known failure modes—including Sybil exposure. Regulatory regimes that require explainability favor graph propagation over opaque machine-learning scores [39],[48], provided operators resist overclaiming predictive power for loan default."),
        ("Same-window and holdout evaluation: Compares EndorseRank and AWP on allowance versus transfer checks and on t2 new owner–spender approvals. The result is a construct-specific map, not a trading-success ranking.", "Same-window and holdout evaluation: Compares EndorseRank and AWP on allowance versus transfer checks and on t2 new owner–spender approvals."),
        ("Hybrid social methods: Operators may combine endorsement-graph features with transfer-graph features, or with DeFi-informed representation learning [39], while preserving the auditability emphasized by Packin and Lev-Aretz[48]. Hybrid designs should report construct-specific checks and, where claimed, a time-split holdout rather than a single aggregate trading-success metric.", "Hybrid social methods: Operators may combine endorsement-graph features with transfer-graph features, or with DeFi-informed representation learning [39], while preserving the auditability emphasized by Packin and Lev-Aretz[48]. Hybrid designs should report construct-specific checks and, where claimed, a time-split holdout."),
        (" Collateral-differentiation experiments:", "Collateral-differentiation experiments: Section 5.4.4 argues that protocols can capture value through fee tiers, utilization, and monitoring cost without treating reputation as a collateral substitute. Until such evidence exists, collateral reduction remains an adoption hypothesis rather than an empirical claim of this research."),
        ("LLInverse risk:", "—"),
        ("PnLc < 0", "—"),
        ("Trading success: close_success_count", "—"),
        ("Lc max(PnLc, 0)", "—"),
        ("ER trading-success mean τ", "ER holdout Kendall τ"),
        ("AWP trading-success mean τ", "AWP holdout Kendall τ"),
        ("Statement: The external check is the temporal holdout of future new approvals, not transfer versus trading-success.", "Statement: The external check is the temporal holdout of future new approvals."),
        ("Evidence: Table 4.7: transfer means 0.333 (ER) and 0.534 (AWP) exceed trading-success means 0.096 (ER) and 0.179 (AWP).", "Evidence: holdout EndorseRank tau = 0.479 (CI 0.426–0.529); AWP 0.044. Same-window transfer means 0.333 (ER) and 0.534 (AWP)."),
        ("PnL flow to POOL/SINK", "—"),
        ("——PnLstar (POOL→wallet, wallet→SINK)", "—"),
        ("This elevation is expected:", "Same-window checks remain allowance versus transfer. The external check is the spender holdout."),
        ("−0.235), consistent with the absence of transfer-activity semantics in the PnL star graph.", "Same-window transfer alignment remains a construct check for AWP."),
    ]
    for prefix, new in leftover_prefix:
        replace_all_prefix(prefix, new)


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
    apply_body_pass4(doc)
    apply_body_pass5(doc)
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
