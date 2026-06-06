"""Shared helpers for margin_rank scripts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from eth_utils import keccak, to_hex

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "margin_config.yaml"
SQL_DIR = ROOT / "sql"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"


def _resolve_path(p: str | Path) -> Path:
    path = Path(p)
    return path if path.is_absolute() else ROOT / path


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or CONFIG_PATH
    with cfg_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    _enrich_config(cfg)
    for key, val in cfg.get("paths", {}).items():
        if isinstance(val, str):
            cfg["paths"][key] = str(_resolve_path(val))
    return cfg


def _enrich_config(cfg: dict[str, Any]) -> None:
    events = cfg.setdefault("events", {})
    if not events.get("event_log1_topic0"):
        events["event_log1_topic0"] = event_log1_topic0()
    for key in ("position_increase", "position_decrease"):
        name = events[key]
        events[f"{key}_hash"] = event_name_hash(name)


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
    if len(s) == 66:
        s = "0x" + s[-40:]
    return s


def parse_topic_address(topic: str | None) -> str | None:
    return normalize_address(topic)


def event_name_hash(name: str) -> str:
    """Indexed string topic = keccak256(bytes(name))."""
    return to_hex(keccak(text=name))


def event_log1_topic0() -> str:
    """Topic0 for EventLog1 — EventLogData tuple type from GMX EventUtils."""
    key_value = "(string,address)"
    array_kv = "(string,address[])"
    uint_kv = "(string,uint256)"
    uint_akv = "(string,uint256[])"
    int_kv = "(string,int256)"
    int_akv = "(string,int256[])"
    bool_kv = "(string,bool)"
    bool_akv = "(string,bool[])"
    b32_kv = "(string,bytes32)"
    b32_akv = "(string,bytes32[])"
    bytes_kv = "(string,bytes)"
    bytes_akv = "(string,bytes[])"
    str_kv = "(string,string)"
    str_akv = "(string,string[])"

    addr_items = f"(({key_value}[]),({array_kv}[]))"
    uint_items = f"(({uint_kv}[]),({uint_akv}[]))"
    int_items = f"(({int_kv}[]),({int_akv}[]))"
    bool_items = f"(({bool_kv}[]),({bool_akv}[]))"
    b32_items = f"(({b32_kv}[]),({b32_akv}[]))"
    bytes_items = f"(({bytes_kv}[]),({bytes_akv}[]))"
    str_items = f"(({str_kv}[]),({str_akv}[]))"
    event_log_data = (
        f"({addr_items},{uint_items},{int_items},{bool_items},"
        f"{b32_items},{bytes_items},{str_items})"
    )
    sig = f"EventLog1(address,string,string,bytes32,{event_log_data})"
    return to_hex(keccak(text=sig))


def format_bytes(n: int) -> str:
    if n >= 1024**3:
        return f"{n / 1024**3:.2f} GiB"
    if n >= 1024**2:
        return f"{n / 1024**2:.2f} MiB"
    return f"{n} B"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def bq_table_fqn(cfg: dict[str, Any], table: str) -> str:
    bq = cfg["bigquery"]
    return f"`{bq['dataset']}.{table}`"
