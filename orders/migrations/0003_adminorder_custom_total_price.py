# Generated by Django 5.1.2 on 2024-11-23 07:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0002_remove_adminorder_customsize_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="adminorder",
            name="custom_total_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
