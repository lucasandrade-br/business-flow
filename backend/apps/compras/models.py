from django.db import models


class BaseSTGCompraModel(models.Model):
    STATUS_PENDENTE = "PENDENTE"
    STATUS_DIVERGENTE = "DIVERGENTE"
    STATUS_VALIDADO = "VALIDADO"
    STATUS_APROVADO_LEGADO = "APROVADO"
    STATUS_APROVADO = STATUS_VALIDADO
    STATUS_VALIDACAO_CHOICES = (
        (STATUS_PENDENTE, "Pendente"),
        (STATUS_DIVERGENTE, "Divergente"),
        (STATUS_VALIDADO, "Validado"),
        (STATUS_APROVADO_LEGADO, "Aprovado (legado)"),
    )

    status_validacao = models.CharField(
        max_length=20,
        choices=STATUS_VALIDACAO_CHOICES,
        default=STATUS_PENDENTE,
        db_index=True,
    )

    class Meta:
        abstract = True


class STG_Compra(BaseSTGCompraModel):
    TRATAMENTO_PENDENTE = "PENDENTE"
    TRATAMENTO_AJUSTADO = "AJUSTADO"
    TRATAMENTO_VALIDADO = "VALIDADO"
    TRATAMENTO_NEGLIGENCIADO = "NEGLIGENCIADO"
    STATUS_TRATAMENTO_CHOICES = (
        (TRATAMENTO_PENDENTE, "Pendente"),
        (TRATAMENTO_AJUSTADO, "Ajustado"),
        (TRATAMENTO_VALIDADO, "Validado"),
        (TRATAMENTO_NEGLIGENCIADO, "Negligenciado"),
    )

    id_stg_compra = models.BigAutoField(primary_key=True, db_column="id_stg_compra")
    id_compra_legado = models.BigIntegerField(db_index=True)
    nota = models.BigIntegerField(null=True, blank=True, db_index=True)
    id_fornecedor_legado = models.BigIntegerField(null=True, blank=True, db_index=True)
    nome_fornecedor_legado = models.CharField(max_length=160, blank=True, default="")
    data_emissao = models.DateField(db_index=True)
    data_lanc = models.DateField(null=True, blank=True, db_index=True)
    valor_produtos = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    valor_total = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    nfe_status = models.CharField(max_length=40, blank=True, default="")
    status_tratamento = models.CharField(
        max_length=20,
        choices=STATUS_TRATAMENTO_CHOICES,
        default=TRATAMENTO_PENDENTE,
        db_index=True,
    )
    validacao_override = models.BooleanField(default=False)
    snapshot_divergencia = models.JSONField(default=dict, blank=True)
    tratamento_atualizado_em = models.DateTimeField(null=True, blank=True)
    fornecedor_resolvido = models.ForeignKey(
        "cadastros.Fornecedor",
        null=True,
        blank=True,
        db_column="id_fornecedor_resolvido",
        on_delete=models.SET_NULL,
        related_name="stg_compras_resolvidas",
    )

    class Meta:
        db_table = "stg_compra"


class STG_ItemCompra(BaseSTGCompraModel):
    id_stg_item_compra = models.BigAutoField(primary_key=True, db_column="id_stg_item_compra")
    stg_compra = models.ForeignKey(
        "compras.STG_Compra",
        on_delete=models.CASCADE,
        related_name="itens",
        db_column="id_stg_compra",
        null=True,
        blank=True,
    )
    id_item_legado = models.BigIntegerField(null=True, blank=True, db_index=True)
    id_compra_legado = models.BigIntegerField(db_index=True)
    id_produto_legado = models.BigIntegerField(null=True, blank=True, db_index=True)
    nome_produto_legado = models.CharField(max_length=200, blank=True, default="")
    unidade_legado = models.CharField(max_length=20, blank=True, default="")
    descricao_legado = models.CharField(max_length=160, blank=True, default="")
    descricao_compra_legado = models.CharField(max_length=160, blank=True, default="")
    quantidade = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    valor_custo = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    valor_total_legado = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    valor_total_calculado = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    produto_resolvido = models.ForeignKey(
        "cadastros.Produto",
        null=True,
        blank=True,
        db_column="id_produto_resolvido",
        on_delete=models.SET_NULL,
        related_name="stg_itens_compra_resolvidos",
    )
    unidade_resolvida = models.ForeignKey(
        "cadastros.UnidadeMedida",
        null=True,
        blank=True,
        db_column="id_und_medida_resolvida",
        on_delete=models.SET_NULL,
        related_name="stg_itens_compra_resolvidos",
    )

    class Meta:
        db_table = "stg_item_compra"


class Compra(models.Model):
    id_compra = models.BigAutoField(primary_key=True, db_column="id_compra")
    id_legado = models.BigIntegerField(db_index=True)
    nota = models.BigIntegerField(null=True, blank=True, db_index=True)
    fornecedor = models.ForeignKey(
        "cadastros.Fornecedor",
        db_column="id_fornecedor",
        on_delete=models.PROTECT,
        related_name="compras",
    )
    data_emissao = models.DateField(db_index=True)
    data_lanc = models.DateField(null=True, blank=True, db_index=True)
    valor_produtos = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    valor_total_documento = models.DecimalField(max_digits=18, decimal_places=6)
    nfe_status = models.CharField(max_length=40, blank=True, default="")
    momento_consolidacao = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "compra"
        constraints = [
            models.UniqueConstraint(fields=["id_legado"], name="uniq_compra_id_legado"),
        ]

    def __str__(self) -> str:
        return f"Compra #{self.id_legado}"


class ItemCompra(models.Model):
    id_item_compra = models.BigAutoField(primary_key=True, db_column="id_item_compra")
    compra = models.ForeignKey(
        Compra,
        db_column="id_compra",
        on_delete=models.CASCADE,
        related_name="itens",
    )
    produto = models.ForeignKey(
        "cadastros.Produto",
        db_column="id_produto",
        on_delete=models.PROTECT,
        related_name="itens_compra",
    )
    unidade_medida = models.ForeignKey(
        "cadastros.UnidadeMedida",
        null=True,
        blank=True,
        db_column="id_und_medida",
        on_delete=models.SET_NULL,
        related_name="itens_compra",
    )
    quantidade = models.DecimalField(max_digits=18, decimal_places=6)
    valor_custo = models.DecimalField(max_digits=18, decimal_places=6)
    valor_total_item = models.DecimalField(max_digits=18, decimal_places=6)
    descricao_origem = models.CharField(max_length=160, blank=True, default="")
    descricao_compra_origem = models.CharField(max_length=160, blank=True, default="")

    class Meta:
        db_table = "item_compra"
