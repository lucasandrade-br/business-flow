from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("despesas", "0003_categoriadespesa_caminho_255")]

    operations = [
        migrations.AddField(
            model_name="lotedespesa",
            name="chave_ativa",
            field=models.CharField(blank=True, default=None, max_length=12, null=True, unique=True),
        ),
    ]
