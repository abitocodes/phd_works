"""
Re-apply outline + references fixes on backup.docx using lxml (preserves w: namespaces).
"""
from __future__ import annotations

import re
import shutil
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

BASE = Path(__file__).resolve().parent
BACKUP = BASE / "backup.docx"
UNPACKED = BASE / "unpacked_clean"
OUT = BASE.parent / "Proposal-Final_Taehong Kwon.docx"
TEMPLATE = BASE / "repack_template.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
NSMAP = {"w": W_NS, "w14": W14_NS}

OUTLINE_NUM_ID = "35"
CHAPTER10_NUM_ID = "47"
AUTHOR = "Taehong Kwon"
COMMENT_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
CHAPTER_RE = re.compile(r"^Chapter\s+(\d+):\s*", re.IGNORECASE)


def w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def para_text(p) -> str:
    return "".join(t.text or "" for t in p.xpath(".//w:t", namespaces=NSMAP)).strip()


def get_ppr(p):
    ppr = p.find("w:pPr", NSMAP)
    if ppr is None:
        ppr = etree.SubElement(p, w("pPr"))
    return ppr


def remove_numpr(ppr):
    for numpr in ppr.xpath("w:numPr", namespaces=NSMAP):
        ppr.remove(numpr)


def set_numpr(p, num_id: str, ilvl: str, pstyle: str | None = "2"):
    ppr = get_ppr(p)
    remove_numpr(ppr)
    if pstyle:
        ps = ppr.find("w:pStyle", NSMAP)
        if ps is None:
            ps = etree.SubElement(ppr, w("pStyle"))
        ps.set(w("val"), pstyle)
    numpr = etree.SubElement(ppr, w("numPr"))
    etree.SubElement(numpr, w("ilvl")).set(w("val"), ilvl)
    etree.SubElement(numpr, w("numId")).set(w("val"), num_id)
    for tag in ("tabs", "ind"):
        for el in ppr.xpath(f"w:{tag}", namespaces=NSMAP):
            ppr.remove(el)
    tabs = etree.SubElement(ppr, w("tabs"))
    tab = etree.SubElement(tabs, w("tab"))
    tab.set(w("val"), "left")
    tab.set(w("pos"), "383")
    ind = etree.SubElement(ppr, w("ind"))
    ind.set(w("left"), "383")
    ind.set(w("hanging"), "298")


def set_chapter_text(p, text: str):
    """Replace text runs only; keep bookmarks/comments."""
    for child in list(p):
        if child.tag in (w("pPr"), w("bookmarkStart"), w("bookmarkEnd"), w("commentRangeStart"), w("commentRangeEnd")):
            continue
        if child.tag == w("r") and child.find("w:commentReference", NSMAP) is not None:
            continue
        p.remove(child)
    r = etree.SubElement(p, w("r"))
    t = etree.SubElement(r, w("t"))
    t.text = text
    if text.startswith(" ") or text.endswith(" "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def apply_ref_entry_ppr(p):
    ppr = get_ppr(p)
    remove_numpr(ppr)
    for ps in ppr.xpath("w:pStyle", namespaces=NSMAP):
        ppr.remove(ps)
    spacing = ppr.find("w:spacing", NSMAP)
    if spacing is None:
        spacing = etree.SubElement(ppr, w("spacing"))
    spacing.set(w("before"), "0")
    spacing.set(w("after"), "120")
    spacing.set(w("line"), "276")
    spacing.set(w("lineRule"), "auto")
    jc = ppr.find("w:jc", NSMAP)
    if jc is None:
        jc = etree.SubElement(ppr, w("jc"))
    jc.set(w("val"), "both")
    ind = ppr.find("w:ind", NSMAP)
    if ind is None:
        ind = etree.SubElement(ppr, w("ind"))
    ind.set(w("left"), "720")
    ind.set(w("hanging"), "360")
    for k in list(ind.attrib):
        if k.endswith("right"):
            del ind.attrib[k]


def add_chapter10_num(numbering_path: Path):
    root = etree.parse(str(numbering_path)).getroot()
    existing = root.xpath(f'//w:num[@w:numId="{CHAPTER10_NUM_ID}"]', namespaces=NSMAP)
    if existing:
        return
    num = etree.Element(w("num"), {w("numId"): CHAPTER10_NUM_ID})
    etree.SubElement(num, w("abstractNumId")).set(w("val"), "40")
    override = etree.SubElement(num, w("lvlOverride"))
    override.set(w("ilvl"), "0")
    etree.SubElement(override, w("startOverride")).set(w("val"), "10")
    root.append(num)
    root.getroottree().write(
        str(numbering_path),
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )


def insert_after(body, after_p, text: str, num_id: str, ilvl: str):
    idx = list(body).index(after_p)
    new_p = etree.Element(w("p"))
    set_chapter_text(new_p, text)
    set_numpr(new_p, num_id, ilvl)
    body.insert(idx + 1, new_p)
    return new_p


def next_comment_id(comments_path: Path) -> int:
    text = comments_path.read_text(encoding="utf-8")
    ids = [int(x) for x in re.findall(r'w:comment w:id="(\d+)"', text)]
    return max(ids) + 1 if ids else 0


def add_comment(comments_root, cid: int, text: str):
    c = etree.Element(
        w("comment"),
        {
            w("id"): str(cid),
            w("author"): AUTHOR,
            w("date"): COMMENT_DATE,
            w("initials"): "TK",
        },
        nsmap={None: W_NS, "w14": W14_NS},
    )
    cp = etree.SubElement(
        c,
        w("p"),
        {f"{{{W14_NS}}}paraId": f"SC{cid:04X}", f"{{{W14_NS}}}textId": "77777777"},
    )
    etree.SubElement(cp, w("r")).append(etree.Element(w("annotationRef")))
    r = etree.SubElement(cp, w("r"))
    etree.SubElement(r, w("t")).text = text
    comments_root.append(c)


def wrap_comment(p, cid: int):
    if p.find(w("commentRangeStart"), NSMAP) is not None:
        return
    p.insert(0, etree.Element(w("commentRangeStart"), {w("id"): str(cid)}))
    p.append(etree.Element(w("commentRangeEnd"), {w("id"): str(cid)}))
    ref_r = etree.Element(w("r"))
    rpr = etree.SubElement(ref_r, w("rPr"))
    etree.SubElement(rpr, w("rStyle")).set(w("val"), "ab")
    etree.SubElement(ref_r, w("commentReference")).set(w("id"), str(cid))
    p.append(ref_r)


def unpack_backup():
    if UNPACKED.exists():
        shutil.rmtree(UNPACKED)
    UNPACKED.mkdir(parents=True)
    with zipfile.ZipFile(BACKUP) as z:
        z.extractall(UNPACKED)
    shutil.copy2(BACKUP, TEMPLATE)


def repack():
    from safe_repack import repack_from_folder

    repack_from_folder(UNPACKED, TEMPLATE, OUT)


def main():
    unpack_backup()
    doc_path = UNPACKED / "word" / "document.xml"
    num_path = UNPACKED / "word" / "numbering.xml"
    comments_path = UNPACKED / "word" / "comments.xml"

    add_chapter10_num(num_path)

    parser = etree.XMLParser(remove_blank_text=False)
    doc = etree.parse(str(doc_path), parser)
    root = doc.getroot()
    body = root.find("w:body", NSMAP)

    chapter_paras = []
    outline_heading = None
    refs_heading = None
    in_outline = False

    for p in body.xpath("w:p", namespaces=NSMAP):
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
        raise RuntimeError("Outline block not found")

    for p in chapter_paras:
        set_chapter_text(p, CHAPTER_RE.sub("", para_text(p)))
        set_numpr(p, OUTLINE_NUM_ID, "0")

    insert_after(body, chapter_paras[-1], "References and appendices", CHAPTER10_NUM_ID, "0")

    ppr = get_ppr(refs_heading)
    remove_numpr(ppr)
    ps = ppr.find("w:pStyle", NSMAP)
    if ps is None:
        ps = etree.SubElement(ppr, w("pStyle"))
    ps.set(w("val"), "1")
    numpr = etree.SubElement(ppr, w("numPr"))
    etree.SubElement(numpr, w("ilvl")).set(w("val"), "1")
    etree.SubElement(numpr, w("numId")).set(w("val"), CHAPTER10_NUM_ID)
    for tag in ("tabs", "ind"):
        for el in ppr.xpath(f"w:{tag}", namespaces=NSMAP):
            ppr.remove(el)
    tabs = etree.SubElement(ppr, w("tabs"))
    tab = etree.SubElement(tabs, w("tab"))
    tab.set(w("val"), "left")
    tab.set(w("pos"), "968")

    # Remove stray blank between Chapter 10 line and References heading
    paras = body.xpath("w:p", namespaces=NSMAP)
    for i, p in enumerate(paras):
        s = para_text(p)
        if s == "References and appendices" and i + 2 < len(paras):
            if not para_text(paras[i + 1]) and para_text(paras[i + 2]) == "References":
                body.remove(paras[i + 1])
                break

    after_refs = False
    ref_entries = []
    for p in body.xpath("w:p", namespaces=NSMAP):
        s = para_text(p)
        if p is refs_heading:
            after_refs = True
            continue
        if after_refs:
            if s.startswith("Appendices"):
                break
            if not s:
                ppr = p.find("w:pPr", NSMAP)
                ind = ppr.find("w:ind", NSMAP) if ppr is not None else None
                if ind is not None and ind.get(w("right")):
                    body.remove(p)
                continue
            ref_entries.append(p)

    for p in ref_entries:
        apply_ref_entry_ppr(p)

    for p in body.xpath("w:p", namespaces=NSMAP):
        s = para_text(p)
        if s.startswith("References") and s.endswith("37") and len(s) < 30:
            ppr = get_ppr(p)
            remove_numpr(ppr)
            numpr = etree.SubElement(ppr, w("numPr"))
            etree.SubElement(numpr, w("ilvl")).set(w("val"), "1")
            etree.SubElement(numpr, w("numId")).set(w("val"), CHAPTER10_NUM_ID)

    doc.write(str(doc_path), xml_declaration=True, encoding="UTF-8", standalone=True)

    cdoc = etree.parse(str(comments_path), parser)
    croot = cdoc.getroot()
    cid = next_comment_id(comments_path)
    add_comment(
        croot,
        cid,
        "Dissertation/Thesis Outline: Chapter 1–6 번호 목록 적용, References는 10.1(목록 numId 47)로 정리. "
        "XML은 lxml로 패치해 Word 복구 경고(ns0 접두사)가 나지 않도록 재저장했습니다.",
    )
    wrap_comment(outline_heading if outline_heading is not None else chapter_paras[0], cid)
    cid2 = cid + 1
    add_comment(
        croot,
        cid2,
        "References 참고문헌: 글머리 없이 APA hanging indent 적용.",
    )
    if ref_entries:
        wrap_comment(ref_entries[0], cid2)
    cdoc.write(str(comments_path), xml_declaration=True, encoding="UTF-8", standalone=True)

    repack()

    # validate
    head = (UNPACKED / "word" / "document.xml").read_text(encoding="utf-8")[:200]
    assert "ns0:" not in head and "<w:document" in head, head
    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None
        h = z.read("word/document.xml")[:300].decode("utf-8")
        assert "ns0:" not in h and "w:document" in h
    print("OK:", OUT)


if __name__ == "__main__":
    main()
