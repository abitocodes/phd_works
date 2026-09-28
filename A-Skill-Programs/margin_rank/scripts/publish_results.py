"""Copy the machine-readable evaluation summaries into the tracked results/ folder.

data/processed/ is ignored by git because it holds raw extracts and large
parquet files. The dissertation tables are generated from two small JSON
summaries, so those two files and the configuration in force are copied here
and committed next to the code. A manifest records the SHA-256 of each copy so
a reader can check that the committed summary is the one the tables came from.

Usage:
    python scripts/publish_results.py            # copy + manifest
    python scripts/publish_results.py --check    # verify results/ matches data/processed/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

# (source relative to ROOT, destination relative to RESULTS)
ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("data/processed/eval_summary.json", "eval_summary.json"),
    ("data/processed/holdout/eval_summary_spenders.json", "holdout/eval_summary_spenders.json"),
    ("config/margin_config.yaml", "config/margin_config.yaml"),
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def publish() -> int:
    manifest: dict[str, object] = {
        "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": [],
    }
    missing = []
    for src_rel, dst_rel in ARTIFACTS:
        src = ROOT / src_rel
        if not src.exists():
            missing.append(src_rel)
            continue
        dst = RESULTS / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        manifest["files"].append(  # type: ignore[union-attr]
            {
                "path": dst_rel,
                "source": src_rel,
                "sha256": _sha256(dst),
                "bytes": dst.stat().st_size,
            }
        )
        print(f"copied {src_rel} -> results/{dst_rel}")
    (RESULTS / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"manifest -> results/MANIFEST.json ({len(manifest['files'])} files)")  # type: ignore[arg-type]
    if missing:
        print("missing sources (not copied): " + ", ".join(missing), file=sys.stderr)
        return 1
    return 0


def check() -> int:
    manifest_path = RESULTS / "MANIFEST.json"
    if not manifest_path.exists():
        print("results/MANIFEST.json not found; run without --check first", file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bad = 0
    for entry in manifest["files"]:
        dst = RESULTS / entry["path"]
        if not dst.exists():
            print(f"MISSING  results/{entry['path']}")
            bad += 1
            continue
        actual = _sha256(dst)
        state = "ok      " if actual == entry["sha256"] else "CHANGED "
        bad += actual != entry["sha256"]
        src = ROOT / entry["source"]
        if src.exists() and _sha256(src) != actual:
            state = "STALE   "
            bad += 1
        print(f"{state} results/{entry['path']}")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="verify results/ against MANIFEST.json and data/processed/")
    args = parser.parse_args()
    return check() if args.check else publish()


if __name__ == "__main__":
    raise SystemExit(main())
