# Generated by Django 5.1.2 on 2024-12-16 04:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_address_created_at_address_updated_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="permissions",
            field=models.JSONField(blank=True, default=list, null=True),
        ),
    ]