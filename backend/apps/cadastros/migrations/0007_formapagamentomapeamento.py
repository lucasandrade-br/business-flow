from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cadastros", "0006_formapagamento_usuario"),
    ]

    operations = [
        migrations.CreateModel(
            name="FormaPagamentoMapeamento",
            fields=[
                ("id_mapeamento", models.BigAutoField(db_column="id_mapeamento", primary_key=True, serialize=False)),
                ("tipo_documento", models.CharField(db_index=True, max_length=10)),
                ("id_forma_origem", models.BigIntegerField(db_index=True)),
                ("descricao_origem", models.CharField(blank=True, default="", max_length=120)),
                ("ativo", models.BooleanField(default=True)),
                (
                    "forma_pagamento",
                    models.ForeignKey(
                        db_column="id_forma",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mapeamentos_origem",
                        to="cadastros.formapagamento",
                    ),
                ),
            ],
            options={
                "db_table": "forma_pagamento_mapeamento",
            },
        ),
        migrations.AddConstraint(
            model_name="formapagamentomapeamento",
            constraint=models.UniqueConstraint(
                fields=("tipo_documento", "id_forma_origem"),
                name="uniq_forma_pagamento_mapeamento_origem",
            ),
        ),
    ]
