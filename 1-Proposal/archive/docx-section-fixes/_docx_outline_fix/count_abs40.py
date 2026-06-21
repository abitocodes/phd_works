import zipfile
from collections import defaultdict
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
path = r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx"
out_path = __file__.replace(".py", "_out.txt")

with zipfile.ZipFile(path) as z:
    nums = etree.fromstring(z.read("word/numbering.xml"))
    root = etree.fromstring(z.read("word/document.xml"))

abs40_nums = []
for n in nums.xpath("//w:num", namespaces=NS):
    aid = n.find("w:abstractNumId", NS)
    if aid is not None and aid.get(f"{{{W}}}val") == "40":
        abs40_nums.append(n.get(f"{{{W}}}numId"))

body = root.find("w:body", NS)
by_num = defaultdict(lambda: defaultdict(int))
total40_0 = 0
stop = False

with open(out_path, "w", encoding="utf-8") as out:
    out.write(f"numIds on abstract 40: {sorted(abs40_nums)}\n\n")
    for p in body.xpath("w:p", namespaces=NS):
        t = "".join(x.text or "" for x in p.xpath(".//w:t", namespaces=NS)).strip()
        num = p.find(".//w:numPr", namespaces=NS)
        if num is not None:
            nid = num.find("w:numId", NS).get(f"{{{W}}}val")
            il = num.find("w:ilvl", NS)
            ilv = il.get(f"{{{W}}}val") if il is not None else "0"
            if nid in abs40_nums:
                by_num[nid][ilv] += 1
                if ilv == "0":
                    total40_0 += 1
        if t.startswith("Introduction and research problem"):
            out.write("BEFORE first outline chapter:\n")
            for nid in sorted(abs40_nums):
                out.write(f"  numId {nid}: {dict(by_num[nid])}\n")
            out.write(f"  total ilvl0 on abs40 nums: {total40_0}\n\n")
            stop = True
        if stop and t == "References and appendices":
            out.write("AT References and appendices:\n")
            for nid in sorted(abs40_nums):
                out.write(f"  numId {nid}: {dict(by_num[nid])}\n")
            break
        if stop and t == "References" and "appendices" not in t:
            ps = p.find(".//w:pStyle", NS)
            out.write(
                f"AT References heading: style={ps.get(f'{{{W}}}val') if ps is not None else None} "
                f"num={num.find('w:numId', NS).get(f'{{{W}}}val') if num is not None else None}\n"
            )
            break

print("wrote", out_path)
