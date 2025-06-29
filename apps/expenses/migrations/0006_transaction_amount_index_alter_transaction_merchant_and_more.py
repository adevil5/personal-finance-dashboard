# Generated by Django 5.2.1 on 2025-06-06 22:50

from django.conf import settings
from django.db import migrations, models

import apps.core.security.fields


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0005_alter_transaction_merchant"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="amount_index",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Transaction amount for filtering/sorting (non-encrypted)",
                max_digits=10,
            ),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="merchant",
            field=apps.core.security.fields.EncryptedCharField(
                blank=True,
                help_text="Merchant or payee name (encrypted)",
                max_length=2295,
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(
                fields=["user", "amount_index"], name="expenses_tr_user_id_981be8_idx"
            ),
        ),
    ]
