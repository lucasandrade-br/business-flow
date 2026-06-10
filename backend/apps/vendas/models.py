from django.db import models


class Venda(models.Model):
	TIPO_NFCE = "NFCE"
	TIPO_DAV = "DAV"
	TIPOS_DOCUMENTO = (
		(TIPO_NFCE, "NFCe"),
		(TIPO_DAV, "DAV"),
	)

	id_venda = models.BigAutoField(primary_key=True, db_column="id_venda")
	id_legado = models.BigIntegerField(db_index=True)
	tipo_documento = models.CharField(max_length=10, choices=TIPOS_DOCUMENTO, db_index=True)
	data_venda = models.DateField(db_index=True)
	hora_venda = models.TimeField(null=True, blank=True)
	status = models.CharField(max_length=40, blank=True, default="")
	cliente = models.ForeignKey(
		"cadastros.Cliente",
		null=True,
		blank=True,
		db_column="id_cliente",
		on_delete=models.SET_NULL,
		related_name="vendas",
	)
	usuario = models.ForeignKey(
		"cadastros.Usuario",
		db_column="id_usuario",
		on_delete=models.PROTECT,
		related_name="vendas",
	)
	valor_total_documento = models.DecimalField(max_digits=18, decimal_places=6)
	momento_consolidacao = models.DateTimeField(null=True, blank=True)

	class Meta:
		db_table = "venda"
		constraints = [
			models.UniqueConstraint(fields=["id_legado", "tipo_documento"], name="uniq_venda_legado_tipo")
		]

	def __str__(self) -> str:
		return f"{self.tipo_documento} #{self.id_legado}"


class ItemVenda(models.Model):
	id_item_venda = models.BigAutoField(primary_key=True, db_column="id_item_venda")
	venda = models.ForeignKey(
		Venda,
		db_column="id_venda",
		on_delete=models.CASCADE,
		related_name="itens",
	)
	produto = models.ForeignKey(
		"cadastros.Produto",
		db_column="id_produto",
		on_delete=models.PROTECT,
		related_name="itens_venda",
	)
	unidade_medida = models.ForeignKey(
		"cadastros.UnidadeMedida",
		null=True,
		blank=True,
		db_column="id_und_medida",
		on_delete=models.SET_NULL,
		related_name="itens_venda",
	)
	quantidade = models.DecimalField(max_digits=18, decimal_places=6)
	valor_unitario = models.DecimalField(max_digits=18, decimal_places=6)
	valor_total_item = models.DecimalField(max_digits=18, decimal_places=6)
	cancelado = models.BooleanField(default=False)

	class Meta:
		db_table = "item_venda"


class PagamentoVenda(models.Model):
	id_pagamento_venda = models.BigAutoField(primary_key=True, db_column="id_pagamento_venda")
	venda = models.ForeignKey(
		Venda,
		db_column="id_venda",
		on_delete=models.CASCADE,
		related_name="pagamentos",
	)
	forma_pagamento = models.ForeignKey(
		"cadastros.FormaPagamento",
		db_column="id_forma",
		on_delete=models.PROTECT,
		related_name="pagamentos_venda",
	)
	valor_pago = models.DecimalField(max_digits=18, decimal_places=6)
	estorno = models.BooleanField(default=False)

	class Meta:
		db_table = "pagamento_venda"
