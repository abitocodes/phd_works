"""Fix Dissertation/Thesis Outline numbering and References formatting."""
from __future__ import annotations

import re
import shutil
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
NS = {"w": W, "w14": W14}

BASE = Path(__file__).resolve().parent
UNPACKED = BASE / "unpacked"
DOC_XML = UNPACKED / "word" / "document.xml"
NUM_XML = UNPACKED / "word" / "numbering.xml"
COMMENTS_XML = UNPACKED / "word" / "comments.xml"
OUT_DOCX = BASE.parent / "Proposal-Final_Taehong Kwon.docx"

OUTLINE_NUM_ID = "35"  # abstract 40: %1 / %1.%2
CHAPTER10_NUM_ID = "47"  # new instance with start 10 at ilvl 0
AUTHOR = "Taehong Kwon"
COMMENT_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

CHAPTER_RE = re.compile(r"^Chapter\s+(\d+):\s*", re.IGNORECASE)


def q(tag: str) -> str:
    return f"{{{W}}}{tag}"


def para_text(p: ET.Element) -> str:
    parts = []
    for t in p.iter(q("t")):
        if t.text:
            parts.append(t.text)
        if t.tail:
            parts.append(t.tail)
    return "".join(parts).strip()


def get_ppr(p: ET.Element) -> ET.Element:
    ppr = p.find("w:pPr", NS)
    if ppr is None:
        ppr = ET.SubElement(p, q("pPr"))
    return ppr


def set_para_text(p: ET.Element, text: str) -> None:
    """Replace paragraph content, keep pPr and bookmarks/comments structure."""
    keep = []
    for child in list(p):
        if child.tag in (
            q("pPr"),
            q("bookmarkStart"),
            q("bookmarkEnd"),
            q("commentRangeStart"),
            q("commentRangeEnd"),
        ):
            keep.append((child.tag, deepcopy(child)))
        elif child.tag == q("r") and child.find(q("commentReference"), NS) is not None:
            keep.append((child.tag, deepcopy(child)))

    for child in list(p):
        p.remove(child)

    for tag, el in keep:
        p.append(el)

    r = ET.SubElement(p, q("r"))
    t = ET.SubElement(r, q("t"))
    if text.startswith(" ") or text.endswith(" "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text


def remove_numpr(ppr: ET.Element) -> None:
    numpr = ppr.find("w:numPr", NS)
    if numpr is not None:
        ppr.remove(numpr)


def set_numpr(p: ET.Element, num_id: str, ilvl: str, pstyle: str | None = "2") -> None:
    ppr = get_ppr(p)
    remove_numpr(ppr)
    if pstyle:
        ps = ppr.find("w:pStyle", NS)
        if ps is None:
            ps = ET.SubElement(ppr, q("pStyle"))
        ps.set(q("val"), pstyle)
    numpr = ET.SubElement(ppr, q("numPr"))
    ET.SubElement(numpr, q("ilvl")).set(q("val"), ilvl)
    ET.SubElement(numpr, q("numId")).set(q("val"), num_id)
    # Match Ethics / numbered heading indent
    for tag in ("tabs", "ind"):
        el = ppr.find(f"w:{tag}", NS)
        if el is not None:
            ppr.remove(el)
    tabs = ET.SubElement(ppr, q("tabs"))
    ET.SubElement(tabs, q("tab")).set(q("val"), "left")
    tabs.find(q("tab")).set(q("pos"), "383")
    ind = ET.SubElement(ppr, q("ind"))
    ind.set(q("left"), "383")
    ind.set(q("hanging"), "298")


def apply_ref_entry_ppr(p: ET.Element) -> None:
    ppr = get_ppr(p)
    remove_numpr(ppr)
    ps = ppr.find("w:pStyle", NS)
    if ps is not None:
        ppr.remove(ps)
    for tag in ("tabs",):
        el = ppr.find(f"w:{tag}", NS)
        if el is not None:
            ppr.remove(el)
    spacing = ppr.find("w:spacing", NS)
    if spacing is None:
        spacing = ET.SubElement(ppr, q("spacing"))
    spacing.set(q("before"), "0")
    spacing.set(q("after"), "120")
    spacing.set(q("line"), "276")
    spacing.set(q("lineRule"), "auto")
    jc = ppr.find("w:jc", NS)
    if jc is None:
        jc = ET.SubElement(ppr, q("jc"))
    jc.set(q("val"), "both")
    ind = ppr.find("w:ind", NS)
    if ind is None:
        ind = ET.SubElement(ppr, q("ind"))
    ind.set(q("left"), "720")
    ind.set(q("hanging"), "360")
    for k in list(ind.attrib):
        if k.endswith("right"):
            del ind.attrib[k]


def add_chapter10_num_instance() -> None:
    root = ET.parse(NUM_XML).getroot()
    if root.find(f'.//w:num[@w:numId="{CHAPTER10_NUM_ID}"]', NS) is not None:
        return
    # abstractNumId 40 = same as numId 35
    num = ET.Element(q("num"), {q("numId"): CHAPTER10_NUM_ID})
    ET.SubElement(num, q("abstractNumId")).set(q("val"), "40")
    override = ET.SubElement(num, q("lvlOverride"))
    override.set(q("ilvl"), "0")
    ET.SubElement(override, q("startOverride")).set(q("val"), "10")
    root.append(num)
    tree = ET.ElementTree(root)
    tree.write(NUM_XML, encoding="UTF-8", xml_declaration=True)


def insert_paragraph_after(body: ET.Element, after_p: ET.Element, text: str, num_id: str, ilvl: str) -> ET.Element:
    children = list(body)
    idx = children.index(after_p)
    new_p = ET.Element(q("p"))
    set_para_text(new_p, text)
    set_numpr(new_p, num_id, ilvl)
    body.insert(idx + 1, new_p)
    return new_p


def next_comment_id() -> int:
    text = COMMENTS_XML.read_text(encoding="utf-8")
    ids = [int(x) for x in re.findall(r'w:comment w:id="(\d+)"', text)]
    return max(ids) + 1 if ids else 0


def add_comment(comments_root: ET.Element, cid: int, text: str) -> None:
    c = ET.Element(
        q("comment"),
        {
            q("id"): str(cid),
            q("author"): AUTHOR,
            q("date"): COMMENT_DATE,
            q("initials"): "TK",
        },
    )
    cp = ET.SubElement(
        c,
        q("p"),
        {f"{{{W14}}}paraId": f"OC{cid:04X}", f"{{{W14}}}textId": "77777777"},
    )
    ref = ET.SubElement(cp, q("r"))
    ET.SubElement(ref, q("annotationRef"))
    r = ET.SubElement(cp, q("r"))
    t = ET.SubElement(r, q("t"))
    t.text = text
    comments_root.append(c)


def wrap_comment(p: ET.Element, cid: int) -> None:
    if p.find("w:commentRangeStart", NS) is not None:
        return
    start = ET.Element(q("commentRangeStart"), {q("id"): str(cid)})
    end = ET.Element(q("commentRangeEnd"), {q("id"): str(cid)})
    ref_r = ET.Element(q("r"))
    rpr = ET.SubElement(ref_r, q("rPr"))
    ET.SubElement(rpr, q("rStyle")).set(q("val"), "ab")
    ET.SubElement(ref_r, q("commentReference")).set(q("id"), str(cid))
    p.insert(0, start)
    p.append(end)
    p.append(ref_r)


def main() -> None:
    add_chapter10_num_instance()

    tree = ET.parse(DOC_XML)
    body = tree.getroot().find("w:body", NS)
    paras = list(body.iter(q("p")))

    # --- Dissertation/Thesis Outline chapters ---
    chapter_paras = []
    outline_heading = None
    refs_heading = None
    in_outline = False

    for p in paras:
        s = para_text(p)
        if s == "Dissertation/Thesis Outline":
            in_outline = True
            outline_heading = p
            continue
        if in_outline and CHAPTER_RE.match(s):
            chapter_paras.append(p)
        if in_outline and s == "References":
            refs_heading = p
            in_outline = False
            break

    if not chapter_paras or refs_heading is None:
        raise RuntimeError("Could not locate outline chapters or References heading")

    for p in chapter_paras:
        s = para_text(p)
        new_s = CHAPTER_RE.sub("", s)
        set_para_text(p, new_s)
        set_numpr(p, OUTLINE_NUM_ID, "0")

    last_chapter = chapter_paras[-1]

    # Chapter 10 container (auto "10.") then References as 10.1
    ch10 = insert_paragraph_after(
        body,
        last_chapter,
        "References and appendices",
        CHAPTER10_NUM_ID,
        "0",
    )

    # Fix References heading: was numId 32 ilvl 1 -> 2.4
    ppr = get_ppr(refs_heading)
    # Keep heading style 1 for TOC/outline level but fix numbering
    ps = ppr.find("w:pStyle", NS)
    if ps is None:
        ps = ET.SubElement(ppr, q("pStyle"))
    ps.set(q("val"), "1")
    remove_numpr(ppr)
    numpr = ET.SubElement(ppr, q("numPr"))
    ET.SubElement(numpr, q("ilvl")).set(q("val"), "1")
    ET.SubElement(numpr, q("numId")).set(q("val"), CHAPTER10_NUM_ID)
    for tag in ("tabs", "ind"):
        el = ppr.find(f"w:{tag}", NS)
        if el is not None:
            ppr.remove(el)
    tabs = ET.SubElement(ppr, q("tabs"))
    ET.SubElement(tabs, q("tab")).set(q("val"), "left")
    tabs.find(q("tab")).set(q("pos"), "968")

    # --- Reference bibliography entries ---
    ref_entries = []
    blanks_to_remove = []
    after_refs = False
    for p in list(body.iter(q("p"))):
        s = para_text(p)
        if p is refs_heading:
            after_refs = True
            continue
        if after_refs:
            if s.startswith("Appendices") or s == "Appendices":
                break
            if not s:
                ppr = p.find("w:pPr", NS)
                ind = ppr.find("w:ind", NS) if ppr is not None else None
                if ind is not None and ind.get(q("right")):
                    blanks_to_remove.append(p)
                continue
            ref_entries.append(p)

    for p in blanks_to_remove:
        body.remove(p)

    for p in ref_entries:
        apply_ref_entry_ppr(p)

    # --- Manual TOC lines (Dissertation outline / References page nums) ---
    for p in paras:
        s = para_text(p)
        if s.startswith("References") and s.endswith("37") and len(s) < 30:
            # TOC entry: References37
            set_para_text(p, "References37")
            ppr = get_ppr(p)
            remove_numpr(ppr)
            numpr = ET.SubElement(ppr, q("numPr"))
            ET.SubElement(numpr, q("ilvl")).set(q("val"), "1")
            ET.SubElement(numpr, q("numId")).set(q("val"), CHAPTER10_NUM_ID)

    comments_tree = ET.parse(COMMENTS_XML)
    comments_root = comments_tree.getroot()
    cid = next_comment_id()
    add_comment(
        comments_root,
        cid,
        "Dissertation/Thesis Outline: Chapter 1–6에 번호 목록(%1.)을 적용하고 'Chapter N:' 중복 접두사를 제거했습니다. "
        "References는 Chapter 10 하위(10.1)로 numId 47 목록을 사용해 2.4가 아닌 10.1 References가 되도록 수정했습니다.",
    )
    wrap_comment(outline_heading or chapter_paras[0], cid)

    cid2 = cid + 1
    add_comment(
        comments_root,
        cid2,
        "References 참고문헌 항목: 글머리(numPr) 없이 APA식 hanging indent(왼쪽 720, hanging 360)와 본문 간격에 맞게 정리했습니다.",
    )
    if ref_entries:
        wrap_comment(ref_entries[0], cid2)

    ET.register_namespace("w", W)
    ET.register_namespace("w14", W14)
    ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")
    ET.register_namespace("mc", "http://schemas.openxmlformats.org/markup-compatibility/2006")
    tree.write(DOC_XML, encoding="UTF-8", xml_declaration=True)
    comments_tree.write(COMMENTS_XML, encoding="UTF-8", xml_declaration=True)

    temp_zip = BASE / "repacked.zip"
    with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zout:
        for fp in UNPACKED.rglob("*"):
            if fp.is_file():
                zout.write(fp, fp.relative_to(UNPACKED).as_posix())
    shutil.copy2(temp_zip, OUT_DOCX)
    print("Updated:", OUT_DOCX)


if __name__ == "__main__":
    main()
