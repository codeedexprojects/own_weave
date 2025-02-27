# Generated by Django 5.1.2 on 2024-11-14 09:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cart", "0007_cart_category_size_cart_length_alter_cart_size_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="cart",
            name="free_product_size",
            field=models.CharField(
                blank=True,
                choices=[
                    ("L", "Large"),
                    ("XL", "Extra Large"),
                    ("XXL", "Double Extra Large"),
                    ("XXXL", "Triple Extra Large"),
                ],
                help_text="Size for free product (L, XL, etc.)",
                max_length=6,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="cart",
            name="free_product_sleeve",
            field=models.CharField(
                blank=True,
                choices=[("full", "Full Sleeve"), ("half", "Half Sleeve")],
                help_text="Sleeve type for free product (full, half, etc.)",
                max_length=10,
                null=True,
            ),
        ),
    ]
