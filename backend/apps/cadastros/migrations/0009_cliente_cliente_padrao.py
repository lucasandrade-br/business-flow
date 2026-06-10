from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cadastros", "0008_formapagamentoorigem"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="cliente_padrao",
            field=models.BooleanField(default=False),
        ),
    ]
