# Generated by Django 5.1.2 on 2024-11-21 04:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0009_product_is_out_of_stock_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Testimonial",
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
                ("thumbnail", models.ImageField(upload_to="testimonial_thumbnails/")),
                ("youtube_link", models.URLField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
