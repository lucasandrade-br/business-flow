from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("integracao", "0006_stgprodutosnovos_ncm"),
    ]

    operations = [
        migrations.AddField(
            model_name="firebirdconnectionconfig",
            name="forma_macro_pix_id",
            field=models.PositiveIntegerField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="firebirdconnectionconfig",
            name="forma_macro_transferencia_id",
            field=models.PositiveIntegerField(blank=True, default=None, null=True),
        ),
    ]
