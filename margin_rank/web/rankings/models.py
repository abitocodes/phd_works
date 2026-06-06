from django.db import models


class DatasetMeta(models.Model):
    """Metadata for the imported ranking snapshot."""

    protocol = models.CharField(max_length=64)
    period_start = models.DateField()
    period_end = models.DateField()
    synthetic = models.BooleanField(default=False)
    imported_at = models.DateTimeField(auto_now=True)
    source_path = models.CharField(max_length=512, blank=True)
    wallet_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "dataset meta"


class WalletRanking(models.Model):
    rank = models.PositiveIntegerField()
    wallet = models.CharField(max_length=42, db_index=True)
    success_rate = models.FloatField()
    total_closes = models.PositiveIntegerField()
    wins = models.PositiveIntegerField()
    losses = models.PositiveIntegerField()
    period_start = models.DateField()
    period_end = models.DateField()
    protocol = models.CharField(max_length=64)
    endorserank_rank = models.PositiveIntegerField(null=True, blank=True)
    awp_rank = models.PositiveIntegerField(null=True, blank=True)
    endorserank_score = models.FloatField(null=True, blank=True)
    awp_score = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["rank"]

    @property
    def success_rate_pct(self) -> str:
        return f"{self.success_rate * 100:.1f}%"

    @property
    def wallet_short(self) -> str:
        if len(self.wallet) < 12:
            return self.wallet
        return f"{self.wallet[:6]}…{self.wallet[-4:]}"

    @property
    def arbiscan_url(self) -> str:
        return f"https://arbiscan.io/address/{self.wallet}"
