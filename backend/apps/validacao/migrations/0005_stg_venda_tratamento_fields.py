from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("validacao", "0004_remove_stg_itemvenda_id_usuario_legado"),
    ]

    operations = [
        migrations.AddField(
            model_name="stg_venda",
            name="snapshot_divergencia",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="stg_venda",
            name="status_tratamento",
            field=models.CharField(
                choices=[("PENDENTE", "Pendente"), ("AJUSTADO", "Ajustado"), ("VALIDADO", "Validado")],
                db_index=True,
                default="PENDENTE",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="stg_venda",
            name="tratamento_atualizado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="stg_venda",
            name="validacao_override",
            field=models.BooleanField(default=False),
        ),
    ]
