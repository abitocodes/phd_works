"""
Fix Dissertation/Thesis Outline formatting on the current proposal docx.

- Chapters 1-6: dedicated list instance (numId 48) restarting at 1
- References and appendices: 10 (numId 49, startOverride 10)
- References: 10.1 with body style 2 (not TOC Heading 1 / 34pt)
- lvlText uses '%1.' so number and text are separated
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
SRC = BASE.parent / "Proposal-Final_Taehong Kwon.docx"
UNPACKED = BASE / "unpacked_work"
TEMPLATE = BASE / "repack_template_work.docx"
OUT = SRC

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
NSMAP = {"w": W_NS, "w14": W14_NS}

OUTLINE_CHAPTER_NUM = "48"
OUTLINE_SECTION_NUM = "49"
NEW_ABSTRACT_ID = "46"
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


def set_numpr(p, num_id: str, ilvl: str, pstyle: str = "2"):
    ppr = get_ppr(p)
    remove_numpr(ppr)
    if pstyle:
        ps = ppr.find("w:pStyle", NSMAP)
        if ps is None:
            ps = etree.SubElement(ppr, w("pStyle"))
        ps.set(w("val"), pstyle)
    else:
        for ps in ppr.xpath("w:pStyle", namespaces=NSMAP):
            ppr.remove(ps)
    numpr = etree.SubElement(ppr, w("numPr"))
    etree.SubElement(numpr, w("ilvl")).set(w("val"), ilvl)
    etree.SubElement(numpr, w("numId")).set(w("val"), num_id)
    for tag in ("tabs", "ind"):
        for el in ppr.xpath(f"w:{tag}", namespaces=NSMAP):
            ppr.remove(el)


def clear_heading_rpr(p):
    """Remove TOC-style large/bold run formatting from References heading."""
    for r in p.xpath("w:r", namespaces=NSMAP):
        rpr = r.find("w:rPr", NSMAP)
        if rpr is None:
            continue
        for tag in ("sz", "szCs", "b", "bCs"):
            for el in rpr.xpath(f"w:{tag}", namespaces=NSMAP):
                rpr.remove(el)


def add_outline_numbering(numbering_path: Path):
    root = etree.parse(str(numbering_path)).getroot()
    if root.xpath(f'//w:abstractNum[@w:abstractNumId="{NEW_ABSTRACT_ID}"]', namespaces=NSMAP):
        return

    src = root.xpath('//w:abstractNum[@w:abstractNumId="40"]', namespaces=NSMAP)
    if not src:
        raise RuntimeError("abstractNum 40 not found")
    abstract = deepcopy(src[0])
    abstract.set(w("abstractNumId"), NEW_ABSTRACT_ID)
    for lvl in abstract.xpath("w:lvl", namespaces=NSMAP):
        il = lvl.get(w("ilvl"))
        if il not in ("0", "1"):
            abstract.remove(lvl)
            continue
        lt = lvl.find("w:lvlText", NSMAP)
        if lt is not None and il == "0":
            lt.set(w("val"), "%1.")
            suff = lvl.find("w:suff", NSMAP)
            if suff is None:
                suff = etree.SubElement(lvl, w("suff"))
            suff.set(w("val"), "tab")

    root.append(abstract)

    def make_num(num_id: str, start10: bool):
        if root.xpath(f'//w:num[@w:numId="{num_id}"]', namespaces=NSMAP):
            return
        num = etree.Element(w("num"), {w("numId"): num_id})
        etree.SubElement(num, w("abstractNumId")).set(w("val"), NEW_ABSTRACT_ID)
        if start10:
            override = etree.SubElement(num, w("lvlOverride"))
            override.set(w("ilvl"), "0")
            etree.SubElement(override, w("startOverride")).set(w("val"), "10")
        root.append(num)

    make_num(OUTLINE_CHAPTER_NUM, False)
    make_num(OUTLINE_SECTION_NUM, True)

    root.getroottree().write(
        str(numbering_path),
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )


def unpack_src():
    if UNPACKED.exists():
        shutil.rmtree(UNPACKED)
    UNPACKED.mkdir(parents=True)
    with zipfile.ZipFile(SRC) as z:
        z.extractall(UNPACKED)
    shutil.copy2(SRC, TEMPLATE)


def repack(target: Path):
    from safe_repack import repack_from_folder

    repack_from_folder(UNPACKED, TEMPLATE, target)


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
        {f"{{{W14_NS}}}paraId": f"OF{cid:04X}", f"{{{W14_NS}}}textId": "77777777"},
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


def find_body_outline(body):
    """Body 'Dissertation/Thesis Outline' (exact title; TOC line includes page number)."""
    outline_heading = None
    chapter_paras = []
    refs_appendices = None
    refs_heading = None
    state = "before"  # before | chapters | after_appendices

    for p in body.xpath("w:p", namespaces=NSMAP):
        s = para_text(p)
        if s == "Dissertation/Thesis Outline":
            outline_heading = p
            state = "chapters"
            continue
        if state == "before":
            continue
        if state == "after_appendices":
            if s == "References":
                refs_heading = p
                break
            continue
        if s == "References and appendices":
            refs_appendices = p
            state = "after_appendices"
            continue
        if not s:
            continue
        if CHAPTER_RE.match(s):
            set_chapter_text(p, CHAPTER_RE.sub("", s))
        chapter_paras.append(p)

    if not chapter_paras or refs_heading is None:
        raise RuntimeError("Body outline block not found")
    return outline_heading, chapter_paras, refs_appendices, refs_heading


def set_chapter_text(p, text: str):
    for child in list(p):
        if child.tag in (
            w("pPr"),
            w("bookmarkStart"),
            w("bookmarkEnd"),
            w("commentRangeStart"),
            w("commentRangeEnd"),
        ):
            continue
        if child.tag == w("r") and child.find("w:commentReference", NSMAP) is not None:
            continue
        p.remove(child)
    r = etree.SubElement(p, w("r"))
    t = etree.SubElement(r, w("t"))
    t.text = text
    if text.startswith(" ") or text.endswith(" "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def main():
    unpack_src()
    doc_path = UNPACKED / "word" / "document.xml"
    num_path = UNPACKED / "word" / "numbering.xml"
    comments_path = UNPACKED / "word" / "comments.xml"

    add_outline_numbering(num_path)

    parser = etree.XMLParser(remove_blank_text=False)
    doc = etree.parse(str(doc_path), parser)
    body = doc.getroot().find("w:body", NSMAP)

    outline_heading, chapter_paras, refs_appendices, refs_heading = find_body_outline(body)

    for p in chapter_paras:
        set_numpr(p, OUTLINE_CHAPTER_NUM, "0", "2")

    if refs_appendices is None:
        refs_appendices = insert_after(
            body, chapter_paras[-1], "References and appendices"
        )
    else:
        set_chapter_text(refs_appendices, "References and appendices")
        set_numpr(refs_appendices, OUTLINE_SECTION_NUM, "0", "2")

    # Remove blank between 10 and 10.1
    paras = body.xpath("w:p", namespaces=NSMAP)
    for i, p in enumerate(paras):
        if para_text(p) == "References and appendices" and i + 2 < len(paras):
            if not para_text(paras[i + 1]) and para_text(paras[i + 2]) == "References":
                body.remove(paras[i + 1])
                break

    set_numpr(refs_heading, OUTLINE_SECTION_NUM, "1", "2")
    clear_heading_rpr(refs_heading)

    doc.write(str(doc_path), xml_declaration=True, encoding="UTF-8", standalone=True)

    cdoc = etree.parse(str(comments_path), parser)
    croot = cdoc.getroot()
    cid = next_comment_id(comments_path)
    add_comment(
        croot,
        cid,
        "Dissertation/Thesis Outline 서식: 장 1–6은 전용 목록(numId 48)으로 1부터 재시작, "
        "References and appendices는 10, References는 10.1(numId 49). "
        "References 제목의 Heading 1(대글꼴)을 본문 스타일 2로 맞춤.",
    )
    anchor = outline_heading if outline_heading is not None else chapter_paras[0]
    wrap_comment(anchor, cid)
    cdoc.write(str(comments_path), xml_declaration=True, encoding="UTF-8", standalone=True)

    try:
        repack(OUT)
        written = OUT
    except PermissionError:
        alt = OUT.with_suffix(".repack.tmp.docx")
        repack(alt)
        written = alt
        print("LOCKED: wrote", alt)

    with zipfile.ZipFile(written) as z:
        assert z.testzip() is None
        h = z.read("word/document.xml")[:400].decode("utf-8")
        assert "ns0:" not in h and "w:document" in h

    # verify body outline
    with zipfile.ZipFile(written) as z:
        root = etree.fromstring(z.read("word/document.xml"))
    body = root.find("w:body", NSMAP)
    _, chapters, ra, rh = find_body_outline(body)
    for p in chapters:
        nid = p.find(".//w:numId", NSMAP).get(f"{{{W_NS}}}val")
        assert nid == OUTLINE_CHAPTER_NUM
    assert ra is not None
    assert rh.find(".//w:pStyle", NSMAP).get(f"{{{W_NS}}}val") == "2"
    print("OK:", written)


def insert_after(body, after_p, text: str):
    idx = list(body).index(after_p)
    new_p = etree.Element(w("p"))
    set_chapter_text(new_p, text)
    set_numpr(new_p, OUTLINE_SECTION_NUM, "0", "2")
    body.insert(idx + 1, new_p)
    return new_p


if __name__ == "__main__":
    main()
