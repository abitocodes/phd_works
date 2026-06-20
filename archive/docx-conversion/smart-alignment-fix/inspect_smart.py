import zipfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
path = r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx"
out = open(__file__.replace(".py", ".txt"), "w", encoding="utf-8")

with zipfile.ZipFile(path) as z:
    root = etree.fromstring(z.read("word/document.xml"))
body = root.find("w:body", NS)
for i, p in enumerate(body.xpath("w:p", namespaces=NS)):
    t = "".join(x.text or "" for x in p.xpath(".//w:t", namespaces=NS)).strip()
    if "SMART" in t or "Computational Efficiency" in t:
        num = p.find(".//w:numPr", namespaces=NS)
        nid = il = None
        if num is not None:
            nid = num.find("w:numId", NS).get(f"{{{W}}}val")
            iln = num.find("w:ilvl", NS)
            il = iln.get(f"{{{W}}}val") if iln is not None else "0"
        ps = p.find(".//w:pStyle", NS)
        st = ps.get(f"{{{W}}}val") if ps is not None else None
        out.write(f"[{i}] style={st} num={nid}/{il} | {t[:120]}\n")

# scan numbered list items 1-6 near objectives with numId 18 or 31
out.write("\n--- num 18 ilvl 0 near Objectives ---\n")
in_range = False
for i, p in enumerate(body.xpath("w:p", namespaces=NS)):
    t = "".join(x.text or "" for x in p.xpath(".//w:t", namespaces=NS)).strip()
    if t == "Objectives" or "2.2 Objectives" in t:
        in_range = True
    if in_range and ("Expected Results" in t or "2.3" in t):
        break
    if not in_range:
        continue
    num = p.find(".//w:numPr", namespaces=NS)
    if num is not None:
        nid = num.find("w:numId", NS).get(f"{{{W}}}val")
        il = num.find("w:ilvl", NS)
        ilv = il.get(f"{{{W}}}val") if il is not None else "0"
        if ilv == "0":
            out.write(f"[{i}] num={nid}/{ilv} | {t[:90]}\n")

out.close()
