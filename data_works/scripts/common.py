"""Shared helpers for data_works scripts."""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "extraction_config.yaml"
SQL_DIR = ROOT / "sql"
RAW_DIR = ROOT / "raw"
PROCESSED_DIR = ROOT / "processed"
SAMPLES_DIR = ROOT / "samples"


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or CONFIG_PATH
    with cfg_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def normalize_address(addr: str | None) -> str | None:
    if addr is None:
        return None
    s = str(addr).strip().lower()
    if not s:
        return None
    if not s.startswith("0x"):
        s = "0x" + s
    # BigQuery topics are 32-byte padded; trim to 20-byte address
    if len(s) == 66:
        s = "0x" + s[-40:]
    return s


def parse_topic_address(topic: str | None) -> str | None:
    return normalize_address(topic)


def block_for_date(
    d: date,
    *,
    earliest_date: date,
    end_date: date,
    earliest_block: int,
    end_block: int,
) -> int:
    """Linear block estimate between anchor dates."""
    total_days = (end_date - earliest_date).days
    if total_days <= 0:
        return end_block
    day_offset = (d - earliest_date).days
    ratio = max(0.0, min(1.0, day_offset / total_days))
    return int(earliest_block + ratio * (end_block - earliest_block))


def month_label(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def iter_months_backward(end: date, earliest: date) -> list[dict[str, Any]]:
    """Return calendar months from end month down to earliest month (inclusive)."""
    months: list[dict[str, Any]] = []
    y, m = end.year, end.month
    while (y, m) >= (earliest.year, earliest.month):
        last_day = calendar.monthrange(y, m)[1]
        start = date(y, m, 1)
        end_day = date(y, m, last_day)
        # exclusive end timestamp = first day of next month
        if m == 12:
            next_start = date(y + 1, 1, 1)
        else:
            next_start = date(y, m + 1, 1)
        months.append(
            {
                "label": month_label(y, m),
                "start_date": start,
                "end_date": end_day,
                "start_ts": f"{start.isoformat()} 00:00:00 UTC",
                "end_ts": f"{next_start.isoformat()} 00:00:00 UTC",
            }
        )
        if m == 1:
            y -= 1
            m = 12
        else:
            m -= 1
    return months


def attach_block_ranges(
    months: list[dict[str, Any]],
    *,
    earliest_date: date,
    end_date: date,
    earliest_block: int,
    end_block: int,
) -> None:
    for mo in months:
        mo["start_block"] = block_for_date(
            mo["start_date"],
            earliest_date=earliest_date,
            end_date=end_date,
            earliest_block=earliest_block,
            end_block=end_block,
        )
        mo["end_block"] = block_for_date(
            mo["end_date"],
            earliest_date=earliest_date,
            end_date=end_date,
            earliest_block=earliest_block,
            end_block=end_block,
        )


def format_bytes(n: int) -> str:
    if n >= 1024**3:
        return f"{n / 1024**3:.2f} GiB"
    if n >= 1024**2:
        return f"{n / 1024**2:.2f} MiB"
    return f"{n} B"


def load_json(path: Path) -> dict[str, Any]:
    import json

    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict[str, Any]) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def list_parquet_glob(directory: Path, pattern: str) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(directory.glob(pattern))
