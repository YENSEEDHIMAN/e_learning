# Generated by Django 5.1.7 on 2025-04-16 05:07

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_auto_20250415_0434'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='score',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=5),
        ),
    ]
