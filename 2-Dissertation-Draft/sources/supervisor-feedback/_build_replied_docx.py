# -*- coding: utf-8 -*-
"""Build Taehong_Thesis_Reviewed_Moulla_Attipoe.replied.docx from the review original."""
from __future__ import annotations

import hashlib
import shutil
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

DIR = Path(__file__).resolve().parent
SRC = DIR / "Taehong_Thesis_Reviewed_Moulla_Attipoe.docx"
DST = DIR / "Taehong_Thesis_Reviewed_Moulla_Attipoe.replied.docx"

AUTHOR = "Taehong Kwon"
INITIALS = "TK"
COMMENT_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
COMMIT = "0c70518a35540c8b56be66b52452cb94ca3fb916"
REPO = "https://github.com/abitocodes/phd_works"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
W14 = "{http://schemas.microsoft.com/office/word/2010/wordml}"
W15 = "{http://schemas.microsoft.com/office/word/2012/wordml}"
W16CID = "{http://schemas.microsoft.com/office/word/2016/wordml/cid}"
W16CEX = "{http://schemas.microsoft.com/office/word/2018/wordml/cex}"
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
    "7": "Rewrote that sentence in the first person: I incorporated the GMX V2 proxies and the GF-PR ceiling reference.",
    "14": "Added a one-sentence circular-construction caveat next to the GF-PR abbreviation. Collapsing SRQ1, SC1, and the named contribution across chapters is deferred until after the meeting.",
    "20": "Split this opening paragraph so each claim has one source: [53] for DeFi intermediation; [48] for the absence of conventional credit histories. A document-wide cluster pass is deferred.",
    "62": "Kept the 2.105 s / 8.9× measurement. Added in red that the speedup is the expected O(|E|) consequence of approval sparsity, that the solver matches AWP, and that C1 is demoted from a headline contribution.",
    "72": "Inserted a Research objectives section (four objectives, mapped to RQ1–RQ4) immediately before Research questions. Chapter 5 mapping of each objective is deferred until after the meeting.",
    "74": "Re-posed RQ4 in red as a construct-validity observation and noted that AWP–transfer alignment is partly mechanical because the proxies share AWP’s input.",
    "77": "Added a red paragraph under Contributions stating that the present claim is latest-allowance edges plus a five-proxy comparison, not a new ranking algorithm.",
    "78": "Acknowledged. I am not inserting a two-page doctoral-scale plan into this working copy. For the meeting I will bring a short plan on (i) methodological development beyond swapping the edge set, (ii) stronger external validity than construct-overlap correlations, and (iii) statistical inference on the reported taus.",
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
    "310": "Rewrote the close of this paragraph in red: allowance tau is near a self-correlation with smoothed in-degree; trading-success 0.096 and inverse-risk 0.035 are at noise level. I do not call that construct-specificity.",
    "349": "Collapsed this subsection to one short paragraph and removed the Akerlof / Graham–Dodd / Basu / Fama–French / Healy–Wahlen cluster from this location.",
    "378": "Acknowledged: major revision before examination. This working copy only (i) edits what can be fixed in red at the comment sites and (ii) replies on each thread. Still open after the meeting: doctoral-scale plan, CIs, GF-PR collapse, full citation and de-duplication passes, ethics certificate, raw logs, and LaTeX–Word cleanup. I do not have Supervisory_Review_Taehong_Thesis.",
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


def collect_para_ids(roots) -> set[str]:
    found: set[str] = set()
    for root in roots:
        for el in root.iter():
            pid = el.get(f"{W14}paraId")
            if pid:
                found.add(pid.upper())
            for attr, val in el.attrib.items():
                if attr.endswith("paraId") and val:
                    found.add(val.upper())
    return found


def collect_durable(root) -> set[str]:
    found = set()
    for el in root.iter():
        for attr, val in el.attrib.items():
            if attr.endswith("durableId") and val:
                found.add(val.upper())
    return found


def next_hex(used: set[str], start: int) -> str:
    n = start
    while True:
        h = f"{n:08X}"
        if h not in used:
            used.add(h)
            return h
        n += 1


def parent_para_id(comment, ext_ids: set[str]) -> str:
    pids = []
    for p in comment.findall(qn("p")):
        pid = p.get(f"{W14}paraId")
        if pid:
            pids.append(pid)
    for pid in reversed(pids):
        if pid.upper() in {x.upper() for x in ext_ids}:
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


def add_reply_comment(comments_root, cid: str, para_id: str, text: str) -> None:
    c = comments_root.makeelement(
        qn("comment"),
        {
            qn("id"): cid,
            qn("author"): AUTHOR,
            qn("date"): COMMENT_DATE,
            qn("initials"): INITIALS,
        },
    )
    p = comments_root.makeelement(
        qn("p"),
        {f"{W14}paraId": para_id, f"{W14}textId": "77777777"},
    )
    ppr = comments_root.makeelement(qn("pPr"), {})
    ps = comments_root.makeelement(qn("pStyle"), {qn("val"): "CommentText"})
    ppr.append(ps)
    p.append(ppr)
    ref_r = comments_root.makeelement(qn("r"), {})
    ref_rpr = comments_root.makeelement(qn("rPr"), {})
    ref_rpr.append(comments_root.makeelement(qn("rStyle"), {qn("val"): "CommentReference"}))
    ref_r.append(ref_rpr)
    ref_r.append(comments_root.makeelement(qn("annotationRef"), {}))
    p.append(ref_r)
    tr = comments_root.makeelement(qn("r"), {})
    t = comments_root.makeelement(qn("t"), {})
    t.text = text
    tr.append(t)
    p.append(tr)
    c.append(p)
    comments_root.append(c)


def add_reply_range(body, parent_id: str, new_id: str) -> None:
    refs = [
        el
        for el in body.iter(qn("commentReference"))
        if el.get(qn("id")) == parent_id
    ]
    if not refs:
        raise KeyError(f"no commentReference for {parent_id}")
    ref_run = refs[-1].getparent()
    parent = ref_run.getparent()
    idx = list(parent).index(ref_run)
    start = parent.makeelement(qn("commentRangeStart"), {qn("id"): new_id})
    end = parent.makeelement(qn("commentRangeEnd"), {qn("id"): new_id})
    new_run = parent.makeelement(qn("r"), {})
    cref = parent.makeelement(qn("commentReference"), {qn("id"): new_id})
    new_run.append(cref)
    parent.insert(idx + 1, start)
    parent.insert(idx + 2, end)
    parent.insert(idx + 3, new_run)


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
        alt = path.with_name(path.stem + ".replied.unlocked.docx")
        if tmp.exists():
            tmp.replace(alt)
        raise PermissionError(str(alt))


def apply_body(doc) -> None:
    body = doc.find(qn("body"))
    paras = [p for p in body if etree.QName(p).localname == "p"]

    p39 = find_para(paras, lambda p: para_has_comment(p, "2"))
    replace_para_text(
        p39,
        "Decentralized finance protocols allocate capital among pseudonymous wallets and therefore need on-chain reputation scores that are computationally scalable, semantically interpretable, and aligned with operationally relevant on-chain signals such as authorization, transfer activity, and risk-related proxies. The identified problem is that transfer-graph reputation is costly to refresh and does not encode explicit spending authorization. This study introduces EndorseRank, an on-chain reputation score obtained by applying PageRank to a directed endorsement graph of latest ERC-20 allowance edges on Arbitrum One, and compares it with Adaptive Weighted PageRank (AWP), a transfer-graph baseline that uses value-weighted logistic time-decay, using five proxy families on a matched wallet cohort (n = 5,521).",
    )

    p40 = find_para(
        paras,
        lambda p: para_text(p).startswith("EndorseRank runs") and "8.9" in para_text(p),
    )
    replace_para_text(
        p40,
        "On the matched cohort, EndorseRank completes PageRank in 2.105 s versus 18.711 s for AWP (approximately 8.9 times faster) and aligns more strongly with allowance proxies (mean Kendall tau = 0.355 versus -0.030 for AWP). AWP aligns more strongly with transfer proxies (tau = 0.534 versus 0.333 for EndorseRank). Inter-method rank correlation (tau = 0.316) indicates partially overlapping yet construct-distinct social reputation structures.",
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
        "I incorporated GMX V2 trading-success proxies to extend domain validation on the same cohort, and I added GainFlow PageRank (GF-PR) only as a supplementary outcome-native ceiling reference built from the same profit-and-loss stream. Among social methods, transfer proxies yield higher mean alignment than trading-success proxies on this chain.",
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
        "Decentralized Finance (DeFi) has transformed how capital is allocated on public blockchains, enabling lending, borrowing, and leveraged trading without traditional financial intermediaries [53]. Yet most credit-like interactions remain highly collateralized because protocols cannot rely on off-chain identity systems or conventional credit histories [48]. In a pseudonymous environment, the operational challenge is to allocate capital safely: distinguishing wallets that manage leveraged exposure reliably from those that exhibit repeated losses, liquidations, or adversarial behavior.",
    )

    p193 = find_para(paras, lambda p: para_has_comment(p, "62"))
    append_red(
        p193,
        " That 8.9 times speedup is an expected consequence of sparsity: the allowance graph has about nine times fewer edges because approvals are rarer on-chain events than transfers, and PageRank is O(|E|). The solver is the same as AWP’s. I therefore keep the measurement but demote Claim C1 from a headline contribution to a documented consequence of the data.",
    )

    p302 = find_para(paras, lambda p: para_has_comment(p, "74"))
    replace_para_text(
        p302,
        "RQ4. As a construct-validity observation rather than an independent empirical finding: for social reputation methods, do transfer proxies (in-degree/in-value), which share input with the AWP graph, show stronger rank alignment than trading-success proxies from GMX V2 perpetual closes? AWP–transfer alignment is expected to be partly mechanical.",
    )

    p308 = find_para(paras, lambda p: para_has_comment(p, "78"))
    replace_para_text(
        p308,
        "The originality claimed here is not a new ranking algorithm. EndorseRank applies stock PageRank to latest ERC-20 allowance edges and compares that score with AWP on one matched cohort under five proxy families. Whether that edge substitution is a sufficient doctoral contribution is for the supervisory meeting; this draft only makes the present scope explicit.",
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
        "This pattern must be read honestly. EndorseRank is essentially a global smoothing of allowance in-degree, so correlating it with allowance in-degree is close to correlating a quantity with itself. On outcomes a protocol would care about, the method is at noise level (trading-success tau = 0.096; inverse-risk tau = 0.035). I do not reframe that weak external validity as a virtue of construct-specificity.",
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
        "Note: GF-PR is circular by construction (the same GMX profit-and-loss stream that defines the trading-success proxies). I retain the abbreviation for now; collapsing SRQ1, SC1, and the named contribution is deferred until after the meeting.",
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
        "Four objectives are derived from the problem statement and map onto the primary research questions. O1: establish whether EndorseRank and AWP produce distinct wallet orderings on one Arbitrum cohort (RQ1). O2: compare construct-specific alignment of the two social methods across the five proxy families (RQ2). O3: measure computational cost of EndorseRank versus AWP at equal n (RQ3). O4: treat the transfer-versus-trading-success contrast as a construct-validity observation rather than as a like-with-like predictive contest (RQ4). Chapter 5 will be revised after the meeting to show how each objective has been met.",
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


def apply_replies(doc, comments, comments_ex, comments_ids, comments_ext, people) -> None:
    body = doc.find(qn("body"))
    ext_ids = {
        el.get(f"{W15}paraId")
        for el in comments_ex
        if el.get(f"{W15}paraId")
    }
    used_para = collect_para_ids([doc, comments, comments_ex])
    used_dur = collect_durable(comments_ids) | collect_durable(comments_ext)
    add_person(people)

    by_id = {c.get(qn("id")): c for c in comments.findall(qn("comment"))}
    next_cid = 1001
    para_n = 0xA1000001
    dur_n = 0xB1000001

    for parent_id in PARENT_ORDER:
        parent = by_id[parent_id]
        parent_pid = parent_para_id(parent, ext_ids)
        new_cid = str(next_cid)
        next_cid += 1
        new_para = next_hex(used_para, para_n)
        para_n += 1
        new_dur = next_hex(used_dur, dur_n)
        dur_n += 1
        add_reply_comment(comments, new_cid, new_para, REPLIES[parent_id])
        ex = comments_ex.makeelement(
            f"{W15}commentEx",
            {
                f"{W15}paraId": new_para,
                f"{W15}paraIdParent": parent_pid,
                f"{W15}done": "0",
            },
        )
        comments_ex.append(ex)
        cid_el = comments_ids.makeelement(
            f"{W16CID}commentId",
            {f"{W16CID}paraId": new_para, f"{W16CID}durableId": new_dur},
        )
        comments_ids.append(cid_el)
        ext_el = comments_ext.makeelement(
            f"{W16CEX}commentExtensible",
            {f"{W16CEX}durableId": new_dur, f"{W16CEX}dateUtc": COMMENT_DATE},
        )
        comments_ext.append(ext_el)
        add_reply_range(body, parent_id, new_cid)


def serialize(root) -> bytes:
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def verify(path: Path) -> None:
    assert zipfile.ZipFile(path).testzip() is None
    with zipfile.ZipFile(path) as z:
        for name in [
            "word/document.xml",
            "word/comments.xml",
            "word/commentsExtended.xml",
            "word/people.xml",
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
        # replies linked
        ex = etree.fromstring(z.read("word/commentsExtended.xml"))
        parents = [
            el.get(f"{W15}paraIdParent")
            for el in ex
            if el.get(f"{W15}paraIdParent")
        ]
        assert len(parents) == 27, len(parents)


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(SRC)
    shutil.copy2(SRC, DST)
    with zipfile.ZipFile(DST) as z:
        doc = etree.fromstring(z.read("word/document.xml"))
        comments = etree.fromstring(z.read("word/comments.xml"))
        comments_ex = etree.fromstring(z.read("word/commentsExtended.xml"))
        comments_ids = etree.fromstring(z.read("word/commentsIds.xml"))
        comments_ext = etree.fromstring(z.read("word/commentsExtensible.xml"))
        people = etree.fromstring(z.read("word/people.xml"))

    apply_body(doc)
    apply_replies(doc, comments, comments_ex, comments_ids, comments_ext, people)

    updates = {
        "word/document.xml": serialize(doc),
        "word/comments.xml": serialize(comments),
        "word/commentsExtended.xml": serialize(comments_ex),
        "word/commentsIds.xml": serialize(comments_ids),
        "word/commentsExtensible.xml": serialize(comments_ext),
        "word/people.xml": serialize(people),
    }
    rewrite_zip(DST, updates)
    verify(DST)
    print("wrote", DST)


if __name__ == "__main__":
    main()
