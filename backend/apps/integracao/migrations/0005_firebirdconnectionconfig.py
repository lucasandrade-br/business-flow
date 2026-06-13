from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("integracao", "0004_stgclientesnovos_hash_md5_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="FirebirdConnectionConfig",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "modo_localizacao",
                    models.CharField(
                        choices=[("FIXED", "Fixo"), ("DYNAMIC", "Dinamico")],
                        default="FIXED",
                        max_length=10,
                    ),
                ),
                ("caminho_fixo", models.CharField(blank=True, default="", max_length=1024)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "firebird_connection_config",
            },
        ),
    ]
