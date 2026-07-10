from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0022_news"),
    ]

    operations = [
        migrations.CreateModel(
            name="CryptoPrice",
            fields=[
                ("id",         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("symbol",     models.CharField(max_length=20, unique=True)),
                ("price_usd",  models.DecimalField(decimal_places=8, default=0, max_digits=24)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["symbol"],
            },
        ),
    ]
