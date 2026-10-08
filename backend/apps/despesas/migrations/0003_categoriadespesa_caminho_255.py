from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("despesas", "0002_movimentodespesa_chave_base")]

    operations = [
        migrations.AlterField(
            model_name="categoriadespesa",
            name="caminho",
            field=models.CharField(max_length=255, unique=True),
        ),
    ]
