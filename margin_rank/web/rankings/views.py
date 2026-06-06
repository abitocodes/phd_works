from django.shortcuts import render

from .models import DatasetMeta, WalletRanking


def index(request):
    meta = DatasetMeta.objects.order_by("-imported_at").first()
    rankings = WalletRanking.objects.all()
    return render(
        request,
        "rankings/index.html",
        {
            "meta": meta,
            "rankings": rankings,
        },
    )
