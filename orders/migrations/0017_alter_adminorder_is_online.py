# Generated by Django 5.1.2 on 2024-12-09 09:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0016_alter_adminorder_is_online"),
    ]

    operations = [
        migrations.AlterField(
            model_name="adminorder",
            name="is_online",
            field=models.BooleanField(default=True),
        ),
    ]
