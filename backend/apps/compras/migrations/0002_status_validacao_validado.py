from django.db import migrations, models


def forwards_normaliza_status_validacao(apps, schema_editor):
    STGCompra = apps.get_model("compras", "STG_Compra")
    STGItemCompra = apps.get_model("compras", "STG_ItemCompra")

    STGCompra.objects.filter(status_validacao="APROVADO").update(status_validacao="VALIDADO")
    STGItemCompra.objects.filter(status_validacao="APROVADO").update(status_validacao="VALIDADO")


def backwards_restaura_status_validacao(apps, schema_editor):
    STGCompra = apps.get_model("compras", "STG_Compra")
    STGItemCompra = apps.get_model("compras", "STG_ItemCompra")

    STGCompra.objects.filter(status_validacao="VALIDADO").update(status_validacao="APROVADO")
    STGItemCompra.objects.filter(status_validacao="VALIDADO").update(status_validacao="APROVADO")


class Migration(migrations.Migration):

    dependencies = [
        ("compras", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stg_compra",
            name="status_validacao",
            field=models.CharField(
                choices=[
                    ("PENDENTE", "Pendente"),
                    ("DIVERGENTE", "Divergente"),
                    ("VALIDADO", "Validado"),
                    ("APROVADO", "Aprovado (legado)"),
                ],
                db_index=True,
                default="PENDENTE",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="stg_itemcompra",
            name="status_validacao",
            field=models.CharField(
                choices=[
                    ("PENDENTE", "Pendente"),
                    ("DIVERGENTE", "Divergente"),
                    ("VALIDADO", "Validado"),
                    ("APROVADO", "Aprovado (legado)"),
                ],
                db_index=True,
                default="PENDENTE",
                max_length=20,
            ),
        ),
        migrations.RunPython(forwards_normaliza_status_validacao, backwards_restaura_status_validacao),
    ]
