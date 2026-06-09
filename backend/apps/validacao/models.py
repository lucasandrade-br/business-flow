from django.db import models


class BaseSTGModel(models.Model):
	STATUS_PENDENTE = "PENDENTE"
	STATUS_DIVERGENTE = "DIVERGENTE"
	STATUS_APROVADO = "APROVADO"
	STATUS_VALIDACAO_CHOICES = (
		(STATUS_PENDENTE, "Pendente"),
		(STATUS_DIVERGENTE, "Divergente"),
		(STATUS_APROVADO, "Aprovado"),
	)

	status_validacao = models.CharField(
		max_length=20,
		choices=STATUS_VALIDACAO_CHOICES,
		default=STATUS_PENDENTE,
		db_index=True,
	)

	class Meta:
		abstract = True


class STG_Venda(BaseSTGModel):
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

	TIPO_NFCE = "NFCE"
	TIPO_DAV = "DAV"
	TIPOS_DOCUMENTO = (
		(TIPO_NFCE, "NFCe"),
		(TIPO_DAV, "DAV"),
	)

	id_stg_venda = models.BigAutoField(primary_key=True, db_column="id_stg_venda")
	tipo_documento = models.CharField(max_length=10, choices=TIPOS_DOCUMENTO, db_index=True)
	id_legado = models.BigIntegerField(db_index=True)
	status_venda = models.CharField(max_length=40, blank=True, default="")
	nome_computador = models.CharField(max_length=120, blank=True, default="")
	data_venda = models.DateField(db_index=True)
	hora_venda = models.TimeField(null=True, blank=True)
	id_cliente_legado = models.BigIntegerField(null=True, blank=True)
	nome_cliente_legado = models.CharField(max_length=160, blank=True, default="")
	estorno = models.BooleanField(default=False)
	nsu = models.CharField(max_length=80, blank=True, default="")
	rede = models.CharField(max_length=80, blank=True, default="")
	nfce_status = models.CharField(max_length=40, blank=True, default="")
	nfce_numero = models.CharField(max_length=40, blank=True, default="")
	id_usuario_legado = models.BigIntegerField(null=True, blank=True)
	nome_usuario_legado = models.CharField(max_length=120, blank=True, default="")
	valor_final = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
	status_tratamento = models.CharField(
		max_length=20,
		choices=STATUS_TRATAMENTO_CHOICES,
		default=TRATAMENTO_PENDENTE,
		db_index=True,
	)
	validacao_override = models.BooleanField(default=False)
	snapshot_divergencia = models.JSONField(default=dict, blank=True)
	tratamento_atualizado_em = models.DateTimeField(null=True, blank=True)

	class Meta:
		db_table = "stg_venda"


class STG_ItemVenda(BaseSTGModel):
	TIPO_NFCE = "NFCE"
	TIPO_DAV = "DAV"
	TIPOS_DOCUMENTO = (
		(TIPO_NFCE, "NFCe"),
		(TIPO_DAV, "DAV"),
	)

	id_stg_item_venda = models.BigAutoField(primary_key=True, db_column="id_stg_item_venda")
	stg_venda = models.ForeignKey(
		"validacao.STG_Venda",
		on_delete=models.CASCADE,
		related_name="itens",
		null=True,
		blank=True,
	)
	tipo_documento = models.CharField(max_length=10, choices=TIPOS_DOCUMENTO, db_index=True)
	id_venda_legado = models.BigIntegerField(db_index=True)
	status_venda = models.CharField(max_length=40, blank=True, default="")
	data_venda = models.DateField(db_index=True)
	hora_venda = models.TimeField(null=True, blank=True)
	id_cliente_legado = models.BigIntegerField(null=True, blank=True)
	nome_cliente_legado = models.CharField(max_length=160, blank=True, default="")
	id_produto_legado = models.BigIntegerField(db_index=True)
	nome_produto_legado = models.CharField(max_length=200, blank=True, default="")
	unidade_comercial_legado = models.CharField(max_length=20, blank=True, default="")
	valor_unitario = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
	quantidade = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
	valor_total_calculado = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
	cancelado = models.BooleanField(default=False)
	ncm = models.CharField(max_length=20, blank=True, default="")

	class Meta:
		db_table = "stg_item_venda"


class STG_PagamentoVenda(BaseSTGModel):
	TIPO_NFCE = "NFCE"
	TIPO_DAV = "DAV"
	TIPOS_DOCUMENTO = (
		(TIPO_NFCE, "NFCe"),
		(TIPO_DAV, "DAV"),
	)

	id_stg_pagamento_venda = models.BigAutoField(primary_key=True, db_column="id_stg_pagamento_venda")
	stg_venda = models.ForeignKey(
		"validacao.STG_Venda",
		on_delete=models.CASCADE,
		related_name="pagamentos",
		null=True,
		blank=True,
	)
	tipo_documento = models.CharField(max_length=10, choices=TIPOS_DOCUMENTO, db_index=True)
	id_venda_legado = models.BigIntegerField(db_index=True)
	id_tipo_pagamento_legado = models.BigIntegerField(null=True, blank=True)
	tipo_pagamento_descricao_legado = models.CharField(max_length=120, blank=True, default="")
	valor_pago = models.DecimalField(max_digits=18, decimal_places=6)
	estorno = models.BooleanField(default=False)
	nsu = models.CharField(max_length=80, blank=True, default="")
	rede = models.CharField(max_length=80, blank=True, default="")

	class Meta:
		db_table = "stg_pagamento_venda"


class STG_AuditoriaPlanilha(BaseSTGModel):
	TIPO_NFCE = "NFCE"
	TIPO_DAV = "DAV"
	TIPOS_DOCUMENTO = (
		(TIPO_NFCE, "NFCe"),
		(TIPO_DAV, "DAV"),
	)

	id_stg_auditoria_planilha = models.BigAutoField(primary_key=True, db_column="id_stg_auditoria_planilha")
	data_venda = models.DateField(db_index=True)
	hora_venda = models.TimeField(null=True, blank=True)
	tipo_documento = models.CharField(max_length=10, choices=TIPOS_DOCUMENTO, db_index=True)
	id_legado = models.BigIntegerField(db_index=True)
	usuario_nome = models.CharField(max_length=120, blank=True, default="")
	cliente_nome = models.CharField(max_length=160, blank=True, default="")
	valor_total = models.DecimalField(max_digits=18, decimal_places=6)
	tipo_pagamento_descricao = models.CharField(max_length=120, blank=True, default="")

	class Meta:
		db_table = "stg_auditoria_planilha"
