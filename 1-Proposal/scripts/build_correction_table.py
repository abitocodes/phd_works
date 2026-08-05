# -*- coding: utf-8 -*-
"""Build the examiner correction table from the template supplied by the examiner.

Keeps the template's formatting (3-column bordered table, Arial 12pt) and only
replaces text, substituting Examiner for Supervisor as instructed. Each filled
cell carries a Taehong Kwon comment.
"""
from __future__ import annotations

import copy
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "sources" / "examiner-feedback" / "Correction-Table-Template.docx"
OUT = ROOT / "proposal" / "Correction-Table_Taehong-Kwon.docx"

AUTHOR = "Taehong Kwon"
INITIALS = "TK"
COMMENT_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
REL_COMMENTS = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
)

TITLE = "Correction Table for Work Submitted to the Examiner"
# Only the first heading line changes; the rest of the header is left as supplied.
HEADER_FIRST_LINE = "Examiner\u2019s Comments"

# (examiner comment, what was done, page numbers, tracking comment)
ROWS: list[tuple[str, str, str, str]] = [
    (
        "An entity builds a financial trust relationship on a DeFi system through consistent wallet "
        "activity which must is conducted on the block chain in a transparent, clear aprouch. The "
        "system is fairly automated in that sense and cannot really be manipulated (or if you try, "
        "then your trust score tanks, making the chance of transacting a problem.",
        "Section 1 now states how trust is normally established in a DeFi system before EndorseRank is "
        "introduced. An address accrues standing through consistent, transparent on-chain activity, "
        "and because that history is immutable and openly auditable, attempts to inflate it are costly "
        "and tend to depress rather than raise the resulting score. Definitions of attestation-based "
        "reputation and of a Sybil attack were added to the terminology list on the preceding page.",
        "pp. 6-7",
        "Examiner comment 1: Records the new Section 1 paragraph on how DeFi trust is normally built, "
        "plus the two added definitions.",
    ),
    (
        "Typical reputational metrics are achieved by using tools like Gitcoin passport, and is linked "
        "to the transactional wallet, where trust is tied directly to a wallet address and verifiable "
        "actions on the chain.",
        "A new Section 3.4, Attestation-Based Reputation Tooling in Deployed DeFi Systems, reviews this "
        "practice with Gitcoin / Human Passport as the primary case. Stamps are verifiable credentials "
        "bound to a wallet address, each weighted by its cost of forgery, summed into a score and "
        "compared against a passing threshold, and optionally minted on-chain as attestations through "
        "the Ethereum Attestation Service. Four sources were added to the reference list: Human "
        "Passport (n.d.); Bordeianu and Popescu (2026); Siddarth et al. (2020); Buterin et al. (2019).",
        "pp. 23-24; references pp. 53-54",
        "Examiner comment 2: Records the new Section 3.4 and the four added references, all verified "
        "against Crossref or the publisher before citation.",
    ),
    (
        "Considering that the proposal does not mention one of the core tools used for reputational "
        "trust in this financial system, it is not clear how the proposed \u201cEndorseRank\u201d will "
        "make a novel contribution. Without referencing how trust is usually established in a DeFi "
        "blockchain system the proposal lacks clarity on the key discussions for a tool like Gitcoin "
        "(to name just one).",
        "The novel contribution is now stated as an explicit contrast with Passport-style tooling along "
        "five dimensions: signal source, data scope, question answered, output form and validation "
        "target. Section 3.3 points forward to Section 3.4; the Section 1 gap statement was rewritten "
        "so that it no longer claims that no existing study addresses the area, and instead says what "
        "the graph-based literature and the deployed tooling each do not do; the research problem in "
        "Section 2 distinguishes an admission gate from a graded ordering of wallets; and Section 8 "
        "restates the original contribution as the treatment of delegation as a measurable, rankable "
        "trust relation.",
        "pp. 9, 10, 23, 25, 44",
        "Examiner comment 3: Records where the novelty claim is now made explicit against Gitcoin / "
        "Human Passport.",
    ),
    (
        "It must be noted that Gitcoin passport does consider both on-chain and off-chain data to "
        "calculate a trust score, to address (among other things), sybil attacks.",
        "Section 3.4 records this explicitly, including the model-based scoring that classifies EVM "
        "addresses in real time from on-chain activity on Ethereum and Layer-2 networks such as "
        "Arbitrum, and the residual credential-farming weakness reported by Bordeianu and Popescu "
        "(2026). Section 6 adds two limitations: EndorseRank draws on no off-chain evidence and "
        "therefore offers no personhood guarantee of its own, and composing a Passport-style gate with "
        "EndorseRank is left to future work because it requires labelled Sybil data not collected here.",
        "pp. 24, 40-41",
        "Examiner comment 4: Records the on-chain plus off-chain and Sybil-resistance discussion in "
        "Section 3.4 and the matching limitations in Section 6.",
    ),
    (
        "I also feel that the research question is too verbose, and as all is linked back to the "
        "essence of the main research question, I feel that the question must be more concise and not "
        "worry too much about all the \u201cside comments\u201d made in the research question.",
        "The main research question in Section 2.1 was shortened from 65 words to 28: \u201cCan "
        "EndorseRank, a Weighted PageRank computed over ERC-20 allowance relationships, match or "
        "outperform transaction-based PageRank baselines in ranking Arbitrum One wallets by trading "
        "success, at lower computational cost?\u201d The setting, perspective, comparison baselines and "
        "evaluation criteria are carried by the SPICE table immediately below the question, so no "
        "information is lost and the sub-questions are unchanged.",
        "p. 11",
        "Examiner comment 5: Records the shortened main research question and where its side "
        "conditions now sit.",
    ),
]


def set_text_keep_format(paragraph, text: str) -> None:
    """Replace paragraph text, preserving the run or paragraph-mark formatting."""
    lines = text.split("\n")
    if paragraph.runs:
        template_rpr = paragraph.runs[0]._r.find(qn("w:rPr"))
    else:
        pPr = paragraph._p.find(qn("w:pPr"))
        template_rpr = pPr.find(qn("w:rPr")) if pPr is not None else None

    for run in list(paragraph.runs):
        run._r.getparent().remove(run._r)

    for i, line in enumerate(lines):
        run = paragraph.add_run()
        if template_rpr is not None:
            run._r.insert(0, copy.deepcopy(template_rpr))
        if i:
            run._r.append(OxmlElement("w:br"))
        t = OxmlElement("w:t")
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = line
        run._r.append(t)


def ensure_comments_part(docx_path: Path) -> None:
    tmp = docx_path.with_suffix(".comments_tmp.docx")
    with zipfile.ZipFile(docx_path, "r") as zin, zipfile.ZipFile(
        tmp, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        names = set(zin.namelist())
        ct = etree.fromstring(zin.read("[Content_Types].xml"))
        rels = etree.fromstring(zin.read("word/_rels/document.xml.rels"))

        if not any(el.get("PartName") == "/word/comments.xml" for el in ct):
            etree.SubElement(
                ct,
                "{%s}Override" % CT_NS,
                PartName="/word/comments.xml",
                ContentType=(
                    "application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.comments+xml"
                ),
            )

        if not any(el.get("Type") == REL_COMMENTS for el in rels):
            used = {el.get("Id") for el in rels}
            rid = "rIdComments"
            n = 90
            while rid in used:
                rid = f"rId{n}"
                n += 1
            etree.SubElement(
                rels,
                "{%s}Relationship" % REL_NS,
                Id=rid,
                Type=REL_COMMENTS,
                Target="comments.xml",
            )

        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = etree.tostring(
                    ct, xml_declaration=True, encoding="UTF-8", standalone=True
                )
            elif item.filename == "word/_rels/document.xml.rels":
                data = etree.tostring(
                    rels, xml_declaration=True, encoding="UTF-8", standalone=True
                )
            elif item.filename == "word/comments.xml":
                continue
            zout.writestr(item, data)

        if "word/comments.xml" not in names:
            comments = etree.Element("{%s}comments" % W_NS, nsmap={"w": W_NS})
            zout.writestr(
                "word/comments.xml",
                etree.tostring(
                    comments, xml_declaration=True, encoding="UTF-8", standalone=True
                ),
            )

    shutil.move(str(tmp), str(docx_path))


def add_comment_element(comments_root, cid: int, text: str) -> None:
    c = OxmlElement("w:comment")
    c.set(qn("w:id"), str(cid))
    c.set(qn("w:author"), AUTHOR)
    c.set(qn("w:date"), COMMENT_DATE)
    c.set(qn("w:initials"), INITIALS)
    p = OxmlElement("w:p")
    ref_run = OxmlElement("w:r")
    ref_run.append(OxmlElement("w:annotationRef"))
    p.append(ref_run)
    run = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    run.append(t)
    p.append(run)
    c.append(p)
    comments_root.append(c)


def wrap_paragraph_comment(paragraph, cid: int) -> None:
    p = paragraph._p
    start = OxmlElement("w:commentRangeStart")
    start.set(qn("w:id"), str(cid))
    end = OxmlElement("w:commentRangeEnd")
    end.set(qn("w:id"), str(cid))
    ref_run = OxmlElement("w:r")
    ref = OxmlElement("w:commentReference")
    ref.set(qn("w:id"), str(cid))
    ref_run.append(ref)

    pPr = p.find(qn("w:pPr"))
    if pPr is not None:
        pPr.addnext(start)
    else:
        p.insert(0, start)
    p.append(end)
    p.append(ref_run)


def main() -> None:
    if not TEMPLATE.is_file():
        raise SystemExit(f"Missing template: {TEMPLATE}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(TEMPLATE, OUT)
    except PermissionError:
        raise SystemExit(f"{OUT} is open in Word. Close it and re-run.")

    ensure_comments_part(OUT)
    doc = Document(str(OUT))
    table = doc.tables[0]

    if len(table.rows) < len(ROWS) + 1:
        raise SystemExit("Template has fewer rows than corrections to record")

    for extra in list(table.rows)[len(ROWS) + 1 :]:
        extra._tr.getparent().remove(extra._tr)

    comments_part = None
    for rel in doc.part.rels.values():
        if rel.reltype == REL_COMMENTS:
            comments_part = rel.target_part
            break
    if comments_part is None:
        raise SystemExit("comments part missing after ensure_comments_part")

    comments_root = comments_part.element
    cid = 0

    set_text_keep_format(doc.paragraphs[0], TITLE)
    add_comment_element(
        comments_root,
        cid,
        "Examiner instruction: title changed from Supervisor to Examiner, as requested in the "
        "covering email of 2 August 2026.",
    )
    wrap_paragraph_comment(doc.paragraphs[0], cid)
    cid += 1

    set_text_keep_format(table.rows[0].cells[0].paragraphs[0], HEADER_FIRST_LINE)
    add_comment_element(
        comments_root,
        cid,
        "Examiner instruction: first column heading changed from Supervisor\u2019s Comments to "
        "Examiner\u2019s Comments.",
    )
    wrap_paragraph_comment(table.rows[0].cells[0].paragraphs[0], cid)
    cid += 1

    for i, (comment, action, pages, note) in enumerate(ROWS, start=1):
        cells = table.rows[i].cells
        set_text_keep_format(cells[0].paragraphs[0], comment)
        set_text_keep_format(cells[1].paragraphs[0], action)
        set_text_keep_format(cells[2].paragraphs[0], pages)
        add_comment_element(comments_root, cid, note)
        wrap_paragraph_comment(cells[1].paragraphs[0], cid)
        cid += 1

    try:
        doc.save(str(OUT))
    except PermissionError:
        raise SystemExit(f"{OUT} is open in Word. Close it and re-run.")

    with zipfile.ZipFile(OUT) as z:
        if z.testzip() is not None:
            raise SystemExit("DOCX zip integrity check failed")
        body = z.read("word/document.xml").decode("utf-8")
        root = etree.fromstring(z.read("word/comments.xml"))

    found = root.findall(qn("w:comment"))
    authors = {c.get(qn("w:author")) for c in found}
    if authors != {AUTHOR}:
        raise SystemExit(f"Unexpected comment authors: {authors}")
    if len(found) != len(ROWS) + 2:
        raise SystemExit(f"Expected {len(ROWS) + 2} comments, found {len(found)}")
    if "ns0:" in body:
        raise SystemExit("document.xml contains a generic ns0: prefix")
    if "Supervisor" in body:
        raise SystemExit("document.xml still refers to Supervisor")

    header = Document(str(OUT)).tables[0].rows[0].cells[0].text
    expected = f"{HEADER_FIRST_LINE}\n(list the ones where correction is requested)"
    if header != expected:
        raise SystemExit(f"Unexpected header cell text: {header!r}")

    print(f"Built {OUT} with {len(found)} comments by {AUTHOR}")


if __name__ == "__main__":
    sys.exit(main())
