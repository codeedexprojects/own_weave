# Generated by Django 5.1.2 on 2024-11-26 11:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "orders",
            "0005_remove_order_razorpay_order_id_adminorder_updated_at_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="razorpay_order_id",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
