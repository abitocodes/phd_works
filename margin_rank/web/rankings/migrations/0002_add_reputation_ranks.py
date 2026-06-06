from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rankings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="walletranking",
            name="endorserank_rank",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="walletranking",
            name="awp_rank",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="walletranking",
            name="endorserank_score",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="walletranking",
            name="awp_score",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
