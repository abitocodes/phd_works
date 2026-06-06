"""Import wallet_rankings.parquet into SQLite (full replace)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from rankings.models import DatasetMeta, WalletRanking


class Command(BaseCommand):
    help = "Import wallet rankings from parquet (truncates existing rows)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=str,
            required=True,
            help="Path to wallet_rankings.parquet",
        )
        parser.add_argument(
            "--manifest",
            type=str,
            default="",
            help="Optional extraction_manifest.json for synthetic flag",
        )

    def handle(self, *args, **options):
        source = Path(options["source"]).resolve()
        if not source.exists():
            raise CommandError(f"File not found: {source}")

        df = pd.read_parquet(source)
        if df.empty:
            self.stdout.write(self.style.WARNING("Parquet is empty; clearing tables."))

        manifest_path = Path(options["manifest"]) if options["manifest"] else None
        if not manifest_path:
            candidate = source.parent / "extraction_manifest.json"
            if candidate.exists():
                manifest_path = candidate

        synthetic = False
        if manifest_path and manifest_path.exists():
            with manifest_path.open(encoding="utf-8") as f:
                manifest = json.load(f)
            synthetic = bool(manifest.get("synthetic", False))

        WalletRanking.objects.all().delete()
        DatasetMeta.objects.all().delete()

        rows = []
        for _, r in df.iterrows():
            rows.append(
                WalletRanking(
                    rank=int(r["rank"]),
                    wallet=str(r["wallet"]).lower(),
                    success_rate=float(r["success_rate"]),
                    total_closes=int(r["total_closes"]),
                    wins=int(r["wins"]),
                    losses=int(r["losses"]),
                    period_start=_to_date(r["period_start"]),
                    period_end=_to_date(r["period_end"]),
                    protocol=str(r["protocol"]),
                    endorserank_rank=_optional_int(r, "endorserank_rank"),
                    awp_rank=_optional_int(r, "awp_rank"),
                    endorserank_score=_optional_float(r, "endorserank_score"),
                    awp_score=_optional_float(r, "awp_score"),
                )
            )
        WalletRanking.objects.bulk_create(rows)

        protocol = str(df.iloc[0]["protocol"]) if len(df) else "gmx_v2_arbitrum"
        period_start = _to_date(df.iloc[0]["period_start"]) if len(df) else date(2026, 5, 25)
        period_end = _to_date(df.iloc[0]["period_end"]) if len(df) else date(2026, 5, 31)

        DatasetMeta.objects.create(
            protocol=protocol,
            period_start=period_start,
            period_end=period_end,
            synthetic=synthetic,
            source_path=str(source),
            wallet_count=len(rows),
        )

        self.stdout.write(
            self.style.SUCCESS(f"Imported {len(rows)} wallet rankings from {source}")
        )


def _to_date(val) -> date:
    if isinstance(val, date):
        return val
    return pd.to_datetime(val).date()


def _optional_int(row, col: str):
    if col not in row.index or pd.isna(row[col]):
        return None
    return int(row[col])


def _optional_float(row, col: str):
    if col not in row.index or pd.isna(row[col]):
        return None
    return float(row[col])
