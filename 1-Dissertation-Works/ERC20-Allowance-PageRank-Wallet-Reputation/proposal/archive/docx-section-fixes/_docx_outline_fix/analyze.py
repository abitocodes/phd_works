import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
path = Path(__file__).parent / "unpacked" / "word" / "document.xml"
root = ET.parse(path).getroot()


def pt(p):
    parts = []
    for t in p.iter(f"{W}t"):
        if t.text:
            parts.append(t.text)
        if t.tail:
            parts.append(t.tail)
    return "".join(parts).strip()


paras = [p for p in root.iter(f"{W}p")]
out = Path(__file__).parent / "analysis.txt"
lines = []

# TOC entries
lines.append("=== TOC (style 1 or similar) ===")
for i, p in enumerate(paras):
    s = pt(p)
    if any(
        k in s
        for k in [
            "Dissertation",
            "Thesis Outline",
            "References",
            "Chapter",
            "Literature Review",
            "Appendices",
        ]
    ) and len(s) < 80:
        ps = p.find(f".//{W}pStyle")
        st = ps.get(f"{W}val") if ps is not None else None
        num = p.find(f".//{W}numPr")
        n = None
        if num is not None:
            il = num.find(f"{W}ilvl")
            nid = num.find(f"{W}numId")
            n = (nid.get(f"{W}val") if nid is not None else "?", il.get(f"{W}val") if il is not None else "?")
        lines.append(f"[{i}] style={st} num={n} | {s!r}")

lines.append("\n=== DISSERTATION OUTLINE BODY ===")
capture = False
for i, p in enumerate(paras):
    s = pt(p)
    if "Dissertation/Thesis Outline" in s and "Outline" in s:
        capture = True
    if capture:
        ps = p.find(f".//{W}pStyle")
        st = ps.get(f"{W}val") if ps is not None else None
        num = p.find(f".//{W}numPr")
        n = None
        if num is not None:
            il = num.find(f"{W}ilvl")
            nid = num.find(f"{W}numId")
            n = (nid.get(f"{W}val") if nid is not None else "?", il.get(f"{W}val") if il is not None else "?")
        lines.append(f"[{i}] style={st} num={n} | {s[:200]}")
    if capture and s.startswith("SPICE"):
        break

lines.append("\n=== REFERENCES BODY (first 20) ===")
in_refs = False
count = 0
for i, p in enumerate(paras):
    s = pt(p)
    if s == "References":
        in_refs = True
        lines.append(f"[{i}] HEAD | References")
        continue
    if in_refs:
        if s.startswith("Appendices"):
            lines.append(f"[{i}] END | {s}")
            break
        num = p.find(f".//{W}numPr")
        n = "none"
        if num is not None:
            il = num.find(f"{W}ilvl")
            nid = num.find(f"{W}numId")
            n = f"numId={nid.get(f'{W}val') if nid is not None else '?'}, ilvl={il.get(f'{W}val') if il is not None else '?'}"
        ind = p.find(f".//{W}ind")
        ind_s = None
        if ind is not None:
            ind_s = {k.split("}")[-1]: ind.get(k) for k in ind.attrib}
        lines.append(f"[{i}] {n} ind={ind_s} | {s[:180]}")
        count += 1
        if count >= 25:
            lines.append("...")
            break

out.write_text("\n".join(lines), encoding="utf-8")
print(out.read_text(encoding="utf-8"))
