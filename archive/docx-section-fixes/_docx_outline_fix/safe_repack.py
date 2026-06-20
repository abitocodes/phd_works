"""Repack docx preserving ZipInfo metadata (compression, timestamps)."""
from __future__ import annotations

import zipfile
from pathlib import Path


def repack_docx(src_dir: Path, out_docx: Path, modified: dict[str, bytes] | None = None) -> None:
    """Copy all entries from unpacked folder; override paths in modified dict."""
    modified = modified or {}
    # Build from a template zip to get ZipInfo - use backup docx as template
    template = out_docx.with_suffix(".template.docx")
    if not template.exists():
        raise FileNotFoundError(template)

    with zipfile.ZipFile(template, "r") as zin:
        infos = {i.filename: i for i in zin.infolist()}
        with zipfile.ZipFile(out_docx, "w") as zout:
            for name, info in infos.items():
                file_path = src_dir / name.replace("/", "\\") if "\\" in str(src_dir) else src_dir / name
                # normalize path
                file_path = src_dir / name
                if name in modified:
                    data = modified[name]
                elif file_path.is_file():
                    data = file_path.read_bytes()
                else:
                    data = zin.read(name)
                new_info = zipfile.ZipInfo(filename=name, date_time=info.date_time)
                new_info.compress_type = info.compress_type
                new_info.external_attr = info.external_attr
                new_info.create_system = info.create_system
                new_info.flag_bits = info.flag_bits
                zout.writestr(new_info, data, compress_type=info.compress_type)


def repack_from_folder(unpacked: Path, template_docx: Path, out_docx: Path) -> None:
    with zipfile.ZipFile(template_docx, "r") as zin:
        with zipfile.ZipFile(out_docx, "w") as zout:
            for info in zin.infolist():
                fp = unpacked / info.filename
                if fp.is_file():
                    data = fp.read_bytes()
                else:
                    data = zin.read(info.filename)
                new_info = zipfile.ZipInfo(filename=info.filename, date_time=info.date_time)
                new_info.compress_type = info.compress_type
                new_info.external_attr = info.external_attr
                zout.writestr(new_info, data, compress_type=info.compress_type)
