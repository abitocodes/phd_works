import zipfile
import sys
from collections import defaultdict
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
path = r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx"
OUT = __file__.replace(".py", ".out.txt")


def log(*a):
    line = " ".join(str(x) for x in a)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(line + "\n")


open(OUT, "w", encoding="utf-8").close()

with zipfile.ZipFile(path) as z:
    nums = etree.fromstring(z.read("word/numbering.xml"))
    root = etree.fromstring(z.read("word/document.xml"))

abs40 = nums.xpath('//w:abstractNum[@w:abstractNumId="40"]', namespaces=NS)[0]
for lvl in abs40.xpath("w:lvl", namespaces=NS):
    il = lvl.get(f"{{{W}}}ilvl")
    lt = lvl.find("w:lvlText", NS)
    log("abs40 ilvl", il, "text", lt.get(f"{{{W}}}val") if lt is not None else None)

log("--- nums using abstract 40 ---")
for n in nums.xpath("//w:num", namespaces=NS):
    aid = n.find("w:abstractNumId", NS)
    if aid is not None and aid.get(f"{{{W}}}val") == "40":
        nid = n.get(f"{{{W}}}numId")
        ovs = []
        for o in n.xpath("w:lvlOverride", namespaces=NS):
            so = o.find("w:startOverride", NS)
            ovs.append(
                (
                    o.get(f"{{{W}}}ilvl"),
                    so.get(f"{{{W}}}val") if so is not None else None,
                )
            )
        log("numId", nid, "overrides", ovs)

body = root.find("w:body", NS)
c = defaultdict(int)
outline = False
for p in body.xpath("w:p", namespaces=NS):
    t = "".join(x.text or "" for x in p.xpath(".//w:t", namespaces=NS)).strip()
    if t == "Dissertation/Thesis Outline":
        log("before outline:", dict(c))
        outline = True
        continue
    if outline and t.startswith("Introduction and research"):
        break
    num = p.find(".//w:numPr", namespaces=NS)
    if num is not None:
        nid = num.find("w:numId", NS).get(f"{{{W}}}val")
        il = num.find("w:ilvl", NS)
        ilv = il.get(f"{{{W}}}val") if il is not None else "0"
        c[(nid, ilv)] += 1

log("outline chapters:", dict(c))
print("wrote", OUT)
