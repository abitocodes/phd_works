"""Replace ASCII spaces between Hangul characters with U+3000 for xeCJK PDF output."""

from __future__ import annotations

import re
import sys
from pathlib import Path

HANGUL = re.compile(r"[\uAC00-\uD7A3]")
# Hangul syllables only; do not touch spaces inside commands/citations.
BETWEEN_HANGUL = re.compile(r"(?<=[\uAC00-\uD7A3]) (?=[\uAC00-\uD7A3])")


def fix_text(text: str) -> tuple[str, int]:
    return BETWEEN_HANGUL.subn("\u3000", text)


def fix_file(path: Path) -> int:
    original = path.read_text(encoding="utf-8")
    updated, count = fix_text(original)
    if count:
        path.write_text(updated, encoding="utf-8")
    return count


def main() -> None:
    root = Path(__file__).resolve().parent.parent / "proposal-ko"
    total = 0
    files = 0
    for path in sorted(root.rglob("*.tex")):
        if path.name.startswith("_"):
            continue
        count = fix_file(path)
        if count:
            files += 1
            total += count
            print(f"{path.relative_to(root)}: {count}")
    print(f"Updated {files} files, {total} replacements")


if __name__ == "__main__":
    main()
