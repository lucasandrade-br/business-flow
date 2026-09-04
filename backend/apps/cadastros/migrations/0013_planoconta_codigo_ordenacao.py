from django.db import migrations, models
import django.db.models.deletion


def _build_codigo_ordenacao(codigo: str) -> str:
    segmentos = [parte for parte in str(codigo or "").split(".") if parte != ""]
    if not segmentos:
        return ""
    normalizados = [parte.zfill(6) if parte.isdigit() else parte for parte in segmentos]
    return ".".join(normalizados) + "."


def backfill_codigo_ordenacao(apps, schema_editor):
    PlanoConta = apps.get_model("cadastros", "PlanoConta")
    lote = []
    for conta in PlanoConta.objects.all().only("id_conta", "codigo_hierarquico").iterator(chunk_size=1000):
        conta.codigo_ordenacao = _build_codigo_ordenacao(conta.codigo_hierarquico)
        lote.append(conta)
        if len(lote) >= 1000:
            PlanoConta.objects.bulk_update(lote, ["codigo_ordenacao"])
            lote = []
    if lote:
        PlanoConta.objects.bulk_update(lote, ["codigo_ordenacao"])


class Migration(migrations.Migration):

    dependencies = [
        ("cadastros", "0012_cliente_fornecedor_nome_gerencial"),
    ]

    operations = [
        migrations.AddField(
            model_name="planoconta",
            name="codigo_ordenacao",
            field=models.CharField(blank=True, db_index=True, default="", max_length=60),
        ),
        migrations.AlterField(
            model_name="planoconta",
            name="conta_pai",
            field=models.ForeignKey(
                blank=True,
                db_column="id_conta_pai",
                db_constraint=False,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="filhas",
                to="cadastros.planoconta",
            ),
        ),
        migrations.RunPython(backfill_codigo_ordenacao, migrations.RunPython.noop),
    ]
