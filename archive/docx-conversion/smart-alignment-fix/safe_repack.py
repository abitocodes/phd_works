"""Repack docx preserving ZipInfo metadata."""
from __future__ import annotations

import zipfile
from pathlib import Path


def repack_from_folder(unpacked: Path, template_docx: Path, out_docx: Path) -> None:
    with zipfile.ZipFile(template_docx, "r") as zin:
        with zipfile.ZipFile(out_docx, "w") as zout:
            for info in zin.infolist():
                fp = unpacked / info.filename
                data = fp.read_bytes() if fp.is_file() else zin.read(info.filename)
                new_info = zipfile.ZipInfo(filename=info.filename, date_time=info.date_time)
                new_info.compress_type = info.compress_type
                new_info.external_attr = info.external_attr
                zout.writestr(new_info, data, compress_type=info.compress_type)
