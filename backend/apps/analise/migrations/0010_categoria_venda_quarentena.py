from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("analise", "0009_dre_diario_consolidada"),
        ("cadastros", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CategoriaVendaQuarentena",
            fields=[
                (
                    "categoria",
                    models.OneToOneField(
                        db_column="id_conta",
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="quarentena_vendas",
                        serialize=False,
                        to="cadastros.planoconta",
                    ),
                ),
            ],
            options={"db_table": "categoria_venda_quarentena"},
        ),
    ]
