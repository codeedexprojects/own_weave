# Generated by Django 5.1.2 on 2024-12-02 04:27

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0008_remove_order_barcode_image"),
        ("products", "0013_category_created_at_category_updated_at_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="adminorder",
            name="custom_length",
        ),
        migrations.RemoveField(
            model_name="adminorder",
            name="discount_amount",
        ),
        migrations.RemoveField(
            model_name="adminorder",
            name="free_product",
        ),
        migrations.RemoveField(
            model_name="adminorder",
            name="length",
        ),
        migrations.RemoveField(
            model_name="adminorder",
            name="offer_type",
        ),
        migrations.RemoveField(
            model_name="adminorder",
            name="product",
        ),
        migrations.RemoveField(
            model_name="adminorder",
            name="quantity",
        ),
        migrations.RemoveField(
            model_name="adminorder",
            name="size",
        ),
        migrations.RemoveField(
            model_name="adminorder",
            name="sleeve",
        ),
        migrations.CreateModel(
            name="AdminOrderProduct",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("quantity", models.PositiveIntegerField()),
                (
                    "size",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("L", "Large"),
                            ("XL", "Extra Large"),
                            ("XXL", "Double Extra Large"),
                            ("XXXL", "Triple Extra Large"),
                        ],
                        max_length=6,
                        null=True,
                    ),
                ),
                (
                    "sleeve",
                    models.CharField(
                        blank=True,
                        choices=[("full", "Full Sleeve"), ("half", "Half Sleeve")],
                        max_length=10,
                        null=True,
                    ),
                ),
                (
                    "custom_length",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "length",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                ("offer_type", models.CharField(blank=True, max_length=20, null=True)),
                (
                    "discount_amount",
                    models.DecimalField(decimal_places=2, default=0, max_digits=10),
                ),
                ("total_price", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "admin_order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="order_products",
                        to="orders.adminorder",
                    ),
                ),
                (
                    "free_product",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="admin_order_free_product",
                        to="products.product",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="products.product",
                    ),
                ),
            ],
        ),
    ]
