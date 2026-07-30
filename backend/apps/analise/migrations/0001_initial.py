from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DashboardKpiVenda",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ytd_receita_atual", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("ytd_receita_anterior_equivalente", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("ytd_volume_atual", models.IntegerField(default=0)),
                ("ytd_volume_anterior_equivalente", models.IntegerField(default=0)),
                ("ticket_medio_atual", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("ticket_medio_anterior_equivalente", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("mtd_receita_atual", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("mtd_receita_anterior_equivalente", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("dados_mensais_grafico", models.JSONField(default=list)),
                ("ultima_data_processada", models.DateField(blank=True, null=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "dashboard_kpi_venda",
            },
        ),
    ]
