# Generated by Django 5.1.2 on 2024-12-07 10:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0012_adminorder_custom_return_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="adminorder",
            name="is_online",
            field=models.BooleanField(default=True),
        ),
    ]
