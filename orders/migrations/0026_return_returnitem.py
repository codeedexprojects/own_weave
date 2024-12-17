# Generated by Django 5.1.2 on 2024-12-13 10:15

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0025_alter_adminorder_payment_method"),
        ("products", "0014_alter_product_description"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Return",
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
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, help_text="Return request created at"
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "order",
                    models.ForeignKey(
                        help_text="Associated order",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="returns",
                        to="orders.order",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="User who placed the order",
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ReturnItem",
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
                (
                    "returned_length",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Returned length (if applicable)",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "refund_price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Refunded price (if applicable)",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "restocked",
                    models.BooleanField(
                        default=False,
                        help_text="Has the stock been updated for this return item?",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "product",
                    models.ForeignKey(
                        help_text="Product being returned",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="products.product",
                    ),
                ),
                (
                    "return_request",
                    models.ForeignKey(
                        help_text="Associated return request",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="orders.return",
                    ),
                ),
            ],
        ),
    ]