import zipfile
import re

path = r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx"
with zipfile.ZipFile(path) as z:
    xml = z.read("word/numbering.xml").decode("utf-8")
abs_ids = [int(x) for x in re.findall(r'w:abstractNumId="(\d+)"', xml)]
num_ids = [int(x) for x in re.findall(r'w:numId="(\d+)"', xml)]
print("max abstract", max(abs_ids), "max num", max(num_ids))
