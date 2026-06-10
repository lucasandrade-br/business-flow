import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cadastros", "0009_cliente_cliente_padrao"),
        ("vendas", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="venda",
            name="status",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="pagamentovenda",
            name="estorno",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="itemvenda",
            name="unidade_medida",
            field=models.ForeignKey(
                blank=True,
                db_column="id_und_medida",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="itens_venda",
                to="cadastros.unidademedida",
            ),
        ),
    ]
