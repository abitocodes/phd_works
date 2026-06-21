import zipfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
path = r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx"
out = open(__file__.replace(".py", ".txt"), "w", encoding="utf-8")

with zipfile.ZipFile(path) as z:
    root = etree.fromstring(z.read("word/document.xml"))
body = root.find("w:body", NS)
in_obj = False
for i, p in enumerate(body.xpath("w:p", namespaces=NS)):
    t = "".join(x.text or "" for x in p.xpath(".//w:t", namespaces=NS)).strip()
    if "2.2 Objectives" in t or t == "Objectives":
        in_obj = True
    if in_obj and ("2.3" in t or "Expected Results" in t) and "SMART" not in t:
        if i > 0:
            out.write(f"--- end objectives near {i} ---\n")
        break
    if not in_obj:
        continue
    num = p.find(".//w:numPr", namespaces=NS)
    nid = il = None
    if num is not None:
        nid = num.find("w:numId", NS)
        il = num.find("w:ilvl", NS)
        nid = nid.get(f"{{{W}}}val") if nid is not None else None
        il = il.get(f"{{{W}}}val") if il is not None else None
    ps = p.find(".//w:pStyle", NS)
    st = ps.get(f"{{{W}}}val") if ps is not None else None
    if t or num is not None:
        out.write(f"[{i}] style={st} num={nid}/{il} | {t[:100]}\n")

out.close()
print("done")
