"""Diagnose docx XML issues that trigger Word recovery dialog."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

FILES = [
    Path(r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx"),
    Path(r"D:\Github\phd_works\Proposal\_docx_outline_fix\backup.docx"),
]


def check(path: Path) -> list[str]:
    issues = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        for req in (
            "[Content_Types].xml",
            "_rels/.rels",
            "word/document.xml",
            "word/_rels/document.xml.rels",
            "word/styles.xml",
            "word/numbering.xml",
        ):
            if req not in names:
                issues.append(f"missing entry: {req}")

        doc = z.read("word/document.xml").decode("utf-8")
        if "ns0:" in doc or "ns1:" in doc:
            issues.append("bad namespace prefix in document.xml")
        if "<?xml" not in doc[:50]:
            issues.append("document.xml missing xml declaration")
        if "<w:document" not in doc:
            issues.append("no w:document root")
        if "wpc:" not in doc and "wordprocessingCanvas" not in doc:
            issues.append("document.xml lost wpc/canvas namespaces")

        # lxml parse
        try:
            from lxml import etree

            etree.fromstring(z.read("word/document.xml"))
        except Exception as e:
            issues.append(f"document.xml parse error: {e}")

        for part in (
            "word/comments.xml",
            "word/commentsExtended.xml",
            "word/numbering.xml",
            "word/styles.xml",
        ):
            if part in names:
                try:
                    from lxml import etree

                    etree.fromstring(z.read(part))
                except Exception as e:
                    issues.append(f"{part} parse error: {e}")

        ct = z.read("[Content_Types].xml").decode("utf-8")
        for part in ("commentsExtended", "people", "persons"):
            if part in ct:
                if f"word/{part}.xml" not in names and part != "commentsExtended":
                    pass
        if "commentsExtended.xml" in ct and "word/commentsExtended.xml" not in names:
            issues.append("Content_Types references commentsExtended but file missing")

        if "word/commentsExtended.xml" in names:
            try:
                from lxml import etree

                etree.fromstring(z.read("word/commentsExtended.xml"))
            except Exception as e:
                issues.append(f"commentsExtended parse error: {e}")

        # rels check
        rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
        for target in re.findall(r'Target="([^"]+)"', rels):
            t = target.lstrip("/")
            if t.startswith("media/") or t.startswith("theme/"):
                full = "word/" + t
            elif t.startswith("http"):
                continue
            else:
                full = "word/" + t if not t.startswith("word/") else t
            if full not in names and not target.startswith("http"):
                issues.append(f"broken rel target: {target}")

    return issues


lines = []
for f in FILES:
    lines.append(f"\n=== {f.name} ===")
    iss = check(f)
    lines.append("OK" if not iss else "\n".join(f"  - {x}" for x in iss))

out = Path(__file__).parent / "diagnose.txt"
out.write_text("\n".join(lines), encoding="utf-8")
