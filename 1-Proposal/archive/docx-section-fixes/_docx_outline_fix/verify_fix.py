import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
path = Path(r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx")
with zipfile.ZipFile(path) as z:
    root = ET.fromstring(z.read("word/document.xml"))
    num_xml = z.read("word/numbering.xml").decode("utf-8")
    print("numId 47 in numbering:", "numId=\"47\"" in num_xml or 'numId="47"' in num_xml)
    print("zip test:", z.testzip())

paras = list(root.iter(f"{W}p"))


def pt(p):
    return "".join(t.text or "" for t in p.iter(f"{W}t")).strip()


lines = []
capture = False
for i, p in enumerate(paras):
    s = pt(p)
    if s == "Dissertation/Thesis Outline":
        capture = True
    if capture:
        num = p.find(f".//{W}numPr")
        n = None
        if num is not None:
            il = num.find(f"{W}ilvl")
            nid = num.find(f"{W}numId")
            n = (nid.get(f"{W}val"), il.get(f"{W}val"))
        lines.append(f"[{i}] num={n} | {s[:120]}")
    if capture and s == "Appendices":
        break

lines.append("\n--- REFS ---")
in_r = False
for i, p in enumerate(paras):
    s = pt(p)
    if s == "References":
        in_r = True
        num = p.find(f".//{W}numPr")
        n = None
        if num is not None:
            il = num.find(f"{W}ilvl")
            nid = num.find(f"{W}numId")
            n = (nid.get(f"{W}val"), il.get(f"{W}val"))
        lines.append(f"HEAD num={n}")
        continue
    if in_r:
        if s.startswith("Appendices"):
            break
        if s:
            num = p.find(f".//{W}numPr")
            ind = p.find(f".//{W}ind")
            n = "bullet" if num is not None else "ok"
            hang = ind.get(f"{W}hanging") if ind is not None else None
            lines.append(f"  [{n}] hang={hang} | {s[:80]}")
            if len([x for x in lines if x.startswith("  ")]) >= 3:
                break

Path(__file__).parent.joinpath("verify_out.txt").write_text("\n".join(lines), encoding="utf-8")
