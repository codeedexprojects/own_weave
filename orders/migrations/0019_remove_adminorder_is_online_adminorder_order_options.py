# Generated by Django 5.1.2 on 2024-12-10 05:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0018_adminorder_rejected_reason"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="adminorder",
            name="is_online",
        ),
        migrations.AddField(
            model_name="adminorder",
            name="Order_options",
            field=models.CharField(
                choices=[("True", "True"), ("False", "False")],
                default="True",
                max_length=20,
            ),
        ),
    ]