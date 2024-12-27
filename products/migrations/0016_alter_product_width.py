# Generated by Django 5.1.2 on 2024-12-26 05:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0015_alter_categorysize_width"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="width",
            field=models.CharField(
                help_text="Width in inches (e.g., 44, 60, 120)", max_length=5
            ),
        ),
    ]
