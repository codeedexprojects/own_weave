# Generated by Django 5.1.2 on 2024-12-02 13:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0013_category_created_at_category_updated_at_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
    ]
