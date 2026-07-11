from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0025_rename_news_published_idx_core_news_publish_ff08d5_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="copytrade",
            name="asset_logo",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
    ]
