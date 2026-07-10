from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0021_add_allow_transfer_to_user"),
    ]

    operations = [
        migrations.CreateModel(
            name="News",
            fields=[
                ("id",           models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title",        models.CharField(max_length=500)),
                ("summary",      models.TextField(blank=True, default="")),
                ("content",      models.TextField(blank=True, default="")),
                ("category",     models.CharField(
                    choices=[
                        ("Crypto",      "Crypto"),
                        ("Stocks",      "Stocks"),
                        ("Forex",       "Forex"),
                        ("Commodities", "Commodities"),
                        ("Tech",        "Tech"),
                        ("ETF",         "ETF"),
                        ("Macro",       "Macro"),
                    ],
                    default="Macro",
                    max_length=20,
                )),
                ("source",       models.CharField(blank=True, default="", max_length=200)),
                ("symbol",       models.CharField(blank=True, default="", max_length=50)),
                ("image_url",    models.URLField(blank=True, default="", max_length=1000)),
                ("source_url",   models.URLField(blank=True, default="", max_length=1000, unique=True)),
                ("published_at", models.DateTimeField()),
                ("created_at",   models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-published_at"],
            },
        ),
        migrations.AddIndex(
            model_name="news",
            index=models.Index(fields=["-published_at"], name="news_published_idx"),
        ),
        migrations.AddIndex(
            model_name="news",
            index=models.Index(fields=["category"], name="news_category_idx"),
        ),
    ]
