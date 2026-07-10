from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0023_cryptoprice"),
    ]

    operations = [
        migrations.CreateModel(
            name="StockProfile",
            fields=[
                ("id",          models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("symbol",      models.CharField(max_length=20, unique=True)),
                ("name",        models.CharField(max_length=200, default="")),
                ("sector",      models.CharField(max_length=100, default="")),
                ("exchange",    models.CharField(max_length=50, default="")),
                ("domain",      models.CharField(max_length=200, default="")),
                ("logo_url",    models.URLField(max_length=500, blank=True, default="")),
                ("description", models.TextField(default="")),
                ("high_52w",    models.DecimalField(max_digits=18, decimal_places=4, default=0)),
                ("low_52w",     models.DecimalField(max_digits=18, decimal_places=4, default=0)),
                ("div_yield",   models.DecimalField(max_digits=10, decimal_places=4, default=0)),
                ("beta",        models.DecimalField(max_digits=8,  decimal_places=4, default=0)),
                ("avg_vol",     models.BigIntegerField(default=0)),
                ("updated_at",  models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["symbol"]},
        ),
        migrations.CreateModel(
            name="StockQuote",
            fields=[
                ("id",         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("symbol",     models.CharField(max_length=20, unique=True)),
                ("price",      models.DecimalField(max_digits=18, decimal_places=4, default=0)),
                ("change",     models.DecimalField(max_digits=18, decimal_places=4, default=0)),
                ("change_pct", models.DecimalField(max_digits=10, decimal_places=4, default=0)),
                ("volume",     models.BigIntegerField(default=0)),
                ("market_cap", models.BigIntegerField(default=0)),
                ("pe",         models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)),
                ("eps",        models.DecimalField(max_digits=12, decimal_places=4, default=0)),
                ("is_index",   models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["symbol"]},
        ),
        migrations.CreateModel(
            name="StockHistory",
            fields=[
                ("id",         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("symbol",     models.CharField(max_length=20, unique=True)),
                ("prices",     models.JSONField(default=list)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["symbol"]},
        ),
    ]
