# Generated by Django 5.1.2 on 2024-11-28 05:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0006_order_razorpay_order_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="barcode_image",
            field=models.ImageField(blank=True, null=True, upload_to="barcodes/"),
        ),
    ]
