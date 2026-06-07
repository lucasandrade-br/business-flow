from django.db import models


class StgProdutosNovos(models.Model):
    id_produto = models.BigIntegerField(primary_key=True)
    gtin = models.CharField(max_length=32, blank=True, default="")
    barras = models.CharField(max_length=64, blank=True, default="")
    nome = models.CharField(max_length=120)
    unidade_comecial = models.CharField(max_length=10, blank=True, default="")
    custo = models.DecimalField(max_digits=18, decimal_places=6)
    valor_venda = models.DecimalField(max_digits=18, decimal_places=6)
    dt_ultimo_movimento = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, blank=True, default="")
    hash_md5 = models.CharField(max_length=32, blank=True, null=True)
    extraido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stg_produtos_novos"


class StgFornecedoresNovos(models.Model):
    id_fornecedor = models.BigIntegerField(primary_key=True)
    fantasia = models.CharField(max_length=120)
    raz_social = models.CharField(max_length=160, blank=True, default="")
    dt_cadastro = models.DateField(null=True, blank=True)
    hash_md5 = models.CharField(max_length=32, blank=True, null=True)
    extraido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stg_fornecedores_novos"


class StgClientesNovos(models.Model):
    id_cliente = models.BigIntegerField(primary_key=True)
    cliente = models.CharField(max_length=120)
    raz_social = models.CharField(max_length=160, blank=True, default="")
    hash_md5 = models.CharField(max_length=32, blank=True, null=True)
    extraido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stg_clientes_novos"
