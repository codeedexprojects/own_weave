# Generated by Django 5.1.2 on 2024-12-10 12:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0022_alter_adminorder_order_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="adminorder",
            name="Order_options",
            field=models.CharField(
                choices=[("True", "Online"), ("False", "Shop")],
                default="True",
                max_length=10,
            ),
        ),
    ]
