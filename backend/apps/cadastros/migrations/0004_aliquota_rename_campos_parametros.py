from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cadastros", "0003_remove_produto_operador_cliente_hash_md5_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="grupocliente",
            old_name="nome",
            new_name="descricao",
        ),
        migrations.RenameField(
            model_name="tipovenda",
            old_name="nome",
            new_name="descricao",
        ),
        migrations.CreateModel(
            name="Aliquota",
            fields=[
                (
                    "id_aliquota",
                    models.AutoField(db_column="id_aliquota", primary_key=True, serialize=False),
                ),
                (
                    "valor_percentual",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
                ),
                (
                    "descricao",
                    models.CharField(blank=True, default="", max_length=80),
                ),
            ],
            options={
                "db_table": "aliquota",
            },
        ),
    ]
