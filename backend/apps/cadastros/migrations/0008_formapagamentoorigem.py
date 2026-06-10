from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cadastros", "0007_formapagamentomapeamento"),
    ]

    operations = [
        migrations.CreateModel(
            name="FormaPagamentoOrigem",
            fields=[
                ("id_origem", models.BigAutoField(db_column="id_origem", primary_key=True, serialize=False)),
                ("tipo_documento", models.CharField(db_index=True, max_length=10)),
                ("id_forma_origem", models.BigIntegerField(db_index=True)),
                ("descricao_origem", models.CharField(max_length=120)),
                ("ativo", models.BooleanField(default=True)),
            ],
            options={
                "db_table": "forma_pagamento_origem",
            },
        ),
        migrations.AddConstraint(
            model_name="formapagamentoorigem",
            constraint=models.UniqueConstraint(
                fields=("tipo_documento", "id_forma_origem"),
                name="uniq_forma_pagamento_origem_tipo_id",
            ),
        ),
    ]
