# Generated by Django 5.1.2 on 2024-12-06 14:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0010_adminorder_track_id_alter_adminorder_city_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="rejected_reason",
            field=models.TextField(blank=True, null=True),
        ),
    ]
