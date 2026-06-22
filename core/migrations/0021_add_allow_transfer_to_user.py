from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_remove_target_from_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="allow_transfer",
            field=models.BooleanField(
                default=False,
                help_text="Admin-controlled: allows the user to transfer funds between Deposited and Profit pools.",
            ),
        ),
    ]
