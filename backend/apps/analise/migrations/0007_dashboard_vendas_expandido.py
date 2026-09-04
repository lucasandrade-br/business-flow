from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analise", "0006_movimentocompraprodutomensal_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="dashboardkpivenda",
            name="dados_periodicos_grafico",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="dashboardkpivenda",
            name="faturamento_mensal_medio_anterior_equivalente",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="dashboardkpivenda",
            name="faturamento_mensal_medio_atual",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="dashboardkpivenda",
            name="faturamento_semanal_medio_anterior_equivalente",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="dashboardkpivenda",
            name="faturamento_semanal_medio_atual",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="dashboardkpivenda",
            name="faturamento_sem_horario_atual",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="dashboardkpivenda",
            name="volume_sem_horario_atual",
            field=models.IntegerField(default=0),
        ),
    ]
