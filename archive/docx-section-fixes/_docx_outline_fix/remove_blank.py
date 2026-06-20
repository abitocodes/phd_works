"""Remove stray blank paragraph between ch10 and References."""
from pathlib import Path
import shutil
import zipfile
from lxml import etree

from safe_repack import repack_from_folder

BASE = Path(__file__).resolve().parent
OUT = BASE.parent / "Proposal-Final_Taehong Kwon.docx"
UNPACKED = BASE / "unpacked_clean"
TEMPLATE = BASE / "repack_template.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def para_text(p):
    return "".join(t.text or "" for t in p.xpath(".//w:t", namespaces=NS)).strip()


with zipfile.ZipFile(OUT) as z:
    z.extractall(UNPACKED)

doc_path = UNPACKED / "word" / "document.xml"
root = etree.parse(str(doc_path)).getroot()
body = root.find("w:body", NS)
paras = body.xpath("w:p", namespaces=NS)
for i, p in enumerate(paras):
    t = para_text(p)
    if t == "References and appendices" and i + 2 < len(paras):
        n1 = para_text(paras[i + 1])
        n2 = para_text(paras[i + 2])
        if not n1 and n2 == "References":
            body.remove(paras[i + 1])
            break

root.getroottree().write(str(doc_path), xml_declaration=True, encoding="UTF-8", standalone=True)
tmp_out = OUT.with_suffix(".repack.tmp.docx")
repack_from_folder(UNPACKED, TEMPLATE, tmp_out)
try:
    shutil.copy2(tmp_out, OUT)
    tmp_out.unlink(missing_ok=True)
except PermissionError:
    print("WARN: target locked; saved as", tmp_out)
else:
    print("removed blank, OK:", OUT)
