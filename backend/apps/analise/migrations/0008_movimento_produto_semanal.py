import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analise", "0007_dashboard_vendas_expandido"),
        ("cadastros", "0013_planoconta_codigo_ordenacao"),
    ]

    operations = [
        migrations.CreateModel(
            name="MovimentoProdutoDiario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data", models.DateField(db_index=True)),
                ("unidade_medida_id_origem", models.IntegerField(default=0)),
                ("unidade_sigla", models.CharField(default="SEM UN.", max_length=20)),
                ("receita_bruta", models.DecimalField(decimal_places=6, default=0, max_digits=24)),
                ("quantidade", models.DecimalField(decimal_places=6, default=0, max_digits=24)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("produto", models.ForeignKey(db_column="id_produto", on_delete=django.db.models.deletion.CASCADE, related_name="movimentos_diarios", to="cadastros.produto")),
            ],
            options={"db_table": "movimento_produto_diario"},
        ),
        migrations.CreateModel(
            name="MovimentoProdutoSemanal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("semana_inicio", models.DateField(db_index=True)),
                ("unidade_medida_id_origem", models.IntegerField(default=0)),
                ("unidade_sigla", models.CharField(default="SEM UN.", max_length=20)),
                ("receita_bruta", models.DecimalField(decimal_places=6, default=0, max_digits=24)),
                ("quantidade", models.DecimalField(decimal_places=6, default=0, max_digits=24)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("produto", models.ForeignKey(db_column="id_produto", on_delete=django.db.models.deletion.CASCADE, related_name="movimentos_semanais", to="cadastros.produto")),
            ],
            options={"db_table": "movimento_produto_semanal"},
        ),
        migrations.CreateModel(
            name="StatusMovimentoProdutoSemanal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("semana_inicio", models.DateField(unique=True)),
                ("status", models.CharField(choices=[("PROCESSANDO", "Processando"), ("PRONTO", "Pronto"), ("FALHA", "Falha")], default="PROCESSANDO", max_length=20)),
                ("erro", models.TextField(blank=True, default="")),
                ("ultimo_sucesso_em", models.DateTimeField(blank=True, null=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "status_movimento_produto_semanal"},
        ),
        migrations.AddConstraint(
            model_name="movimentoprodutodiario",
            constraint=models.UniqueConstraint(fields=("data", "produto", "unidade_medida_id_origem"), name="uniq_mov_prod_dia_unidade"),
        ),
        migrations.AddIndex(
            model_name="movimentoprodutodiario",
            index=models.Index(fields=["produto", "data"], name="idx_mov_prod_diario_periodo"),
        ),
        migrations.AddConstraint(
            model_name="movimentoprodutosemanal",
            constraint=models.UniqueConstraint(fields=("semana_inicio", "produto", "unidade_medida_id_origem"), name="uniq_mov_prod_sem_unidade"),
        ),
        migrations.AddIndex(
            model_name="movimentoprodutosemanal",
            index=models.Index(fields=["produto", "semana_inicio"], name="idx_mov_prod_sem_periodo"),
        ),
    ]
