from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("analise", "0008_movimento_produto_semanal")]

    operations = [
        migrations.CreateModel(
            name="DreDiarioConsolidada",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data", models.DateField(unique=True)),
                ("total_receita", models.DecimalField(decimal_places=6, default=0, max_digits=24)),
                ("total_custo", models.DecimalField(decimal_places=6, default=0, max_digits=24)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "dre_diario_consolidada"},
        ),
        migrations.CreateModel(
            name="StatusDreConsolidada",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ano", models.IntegerField()),
                ("mes", models.PositiveSmallIntegerField()),
                ("status", models.CharField(choices=[("PROCESSANDO", "Processando"), ("PRONTO", "Pronto"), ("FALHA", "Falha")], default="PROCESSANDO", max_length=20)),
                ("erro", models.TextField(blank=True, default="")),
                ("ultimo_sucesso_em", models.DateTimeField(blank=True, null=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "status_dre_consolidada"},
        ),
        migrations.AddConstraint(
            model_name="statusdreconsolidada",
            constraint=models.UniqueConstraint(fields=("ano", "mes"), name="uniq_status_dre_ano_mes"),
        ),
    ]
