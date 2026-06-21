import zipfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
path = r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx"
out = open(__file__.replace(".py", "_out.txt"), "w", encoding="utf-8")

with zipfile.ZipFile(path) as z:
    nums = etree.fromstring(z.read("word/numbering.xml"))
    root = etree.fromstring(z.read("word/document.xml"))

for nid in ["44", "35", "32", "47"]:
    n = nums.xpath(f'//w:num[@w:numId="{nid}"]', namespaces=NS)
    if n:
        aid = n[0].find("w:abstractNumId", NS).get(f"{{{W}}}val")
        out.write(f"numId {nid} -> abstract {aid}\n")

body = root.find("w:body", NS)
markers = [
    "Introduction and research problem",
    "Dissertation/Thesis Outline",
]
counts = {("44", "0"): 0, ("35", "0"): 0, ("47", "0"): 0, ("47", "1"): 0}

for p in body.xpath("w:p", namespaces=NS):
    t = "".join(x.text or "" for x in p.xpath(".//w:t", namespaces=NS)).strip()
    for m in markers:
        if m in t and (m == t or t.startswith(m[:30])):
            out.write(f"AT [{m}] counts: {dict(counts)}\n")
    num = p.find(".//w:numPr", namespaces=NS)
    if num is not None:
        nid = num.find("w:numId", NS).get(f"{{{W}}}val")
        il = num.find("w:ilvl", NS)
        ilv = il.get(f"{{{W}}}val") if il is not None else "0"
        k = (nid, ilv)
        if k in counts:
            counts[k] += 1

out.close()
print("done")
