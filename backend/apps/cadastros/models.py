from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.integracao.hash_engine import (
	gerar_hash_cliente,
	gerar_hash_fornecedor,
	gerar_hash_produto,
)


class UnidadeMedida(models.Model):
	id_und_medida = models.AutoField(primary_key=True, db_column="id_und_medida")
	sigla = models.CharField(max_length=10, unique=True)
	descricao = models.CharField(max_length=60, blank=True, default="")

	class Meta:
		db_table = "unidade_medida"

	def __str__(self) -> str:
		return self.sigla


class PlanoConta(models.Model):
	id_conta = models.AutoField(primary_key=True, db_column="id_conta")
	codigo_hierarquico = models.CharField(max_length=30)
	nome_conta = models.CharField(max_length=120)
	conta_pai = models.ForeignKey(
		"self",
		null=True,
		blank=True,
		db_column="id_conta_pai",
		db_constraint=False,
		on_delete=models.SET_NULL,
		related_name="filhas",
	)

	class Meta:
		db_table = "plano_conta"
		unique_together = ("codigo_hierarquico", "nome_conta")

	def __str__(self) -> str:
		return f"{self.codigo_hierarquico} - {self.nome_conta}"

	@staticmethod
	def _parse_root_code(codigo: str) -> int | None:
		if not codigo or not codigo.endswith("."):
			return None
		head = codigo[:-1]
		return int(head) if head.isdigit() else None

	@staticmethod
	def _parse_child_code(parent_code: str, codigo: str) -> int | None:
		if not parent_code or not codigo or not codigo.startswith(parent_code):
			return None
		suffix = codigo[len(parent_code) :]
		if not suffix.endswith("."):
			return None
		number = suffix[:-1]
		return int(number) if number.isdigit() else None

	def _build_next_code(self) -> str:
		parent = self.conta_pai
		siblings = PlanoConta.objects.select_for_update().filter(conta_pai=parent)
		if self.pk:
			siblings = siblings.exclude(pk=self.pk)

		codes = siblings.values_list("codigo_hierarquico", flat=True)

		if parent is None:
			indexes = [
				idx
				for idx in (self._parse_root_code(code) for code in codes)
				if idx is not None
			]
			next_index = (max(indexes) if indexes else 0) + 1
			return f"{next_index}."

		if parent.pk is None:
			raise ValidationError("conta_pai precisa estar salva antes de criar filhas.")

		parent_code = parent.codigo_hierarquico
		if not parent_code:
			raise ValidationError("conta_pai sem codigo_hierarquico valido.")

		indexes = [
			idx
			for idx in (self._parse_child_code(parent_code, code) for code in codes)
			if idx is not None
		]
		next_index = (max(indexes) if indexes else 0) + 1
		return f"{parent_code}{next_index}."

	def save(self, *args, **kwargs):
		if not self.codigo_hierarquico:
			with transaction.atomic():
				self.codigo_hierarquico = self._build_next_code()
				return super().save(*args, **kwargs)
		return super().save(*args, **kwargs)

	@property
	def linha_sucessoria(self) -> str:
		if self.conta_pai is None:
			return ""

		partes: list[str] = []
		atual = self.conta_pai
		while atual is not None:
			partes.append(f"{atual.codigo_hierarquico} {atual.nome_conta}".strip())
			atual = atual.conta_pai

		partes.reverse()
		return " | ".join(partes)


class Produto(models.Model):
	id_produto = models.BigIntegerField(primary_key=True)
	gtin = models.CharField(max_length=32, blank=True, default="")
	barras = models.CharField(max_length=64, blank=True, default="")
	produto = models.CharField(max_length=120)
	hash_md5 = models.CharField(max_length=32, blank=True, null=True)
	id_und_medida = models.ForeignKey(
		UnidadeMedida,
		null=True,
		blank=True,
		db_column="id_und_medida",
		db_constraint=False,
		on_delete=models.SET_NULL,
		related_name="produtos",
	)
	custo = models.DecimalField(max_digits=18, decimal_places=6)
	venda = models.DecimalField(max_digits=18, decimal_places=6)
	status = models.CharField(max_length=30, blank=True, default="")
	markup = models.DecimalField(max_digits=10, decimal_places=4)
	markup_inv = models.DecimalField(max_digits=10, decimal_places=4)
	perda = models.DecimalField(max_digits=10, decimal_places=4)
	categorias = models.ManyToManyField(
		PlanoConta,
		related_name="produtos_vinculados",
		blank=True,
	)
	ult_mov = models.DateField(null=True, blank=True)
	fisico = models.DecimalField(max_digits=10, decimal_places=4)
	aliqefc = models.CharField(max_length=20)
	cod_g3n = models.IntegerField()
	cod_rel = models.IntegerField()
	usuario = models.CharField(max_length=100, blank=True, default="")

	class Meta:
		db_table = "produtos"

	def save(self, *args, **kwargs):
		self.hash_md5 = gerar_hash_produto(
			id_produto=self.id_produto,
			gtin=self.gtin,
			barras=self.barras,
			nome=self.produto,
			custo=self.custo,
			venda=self.venda,
			status=self.status,
		)
		return super().save(*args, **kwargs)


class CodSis(models.Model):
	id_codsis = models.AutoField(primary_key=True, db_column="id_codsis")
	nome = models.CharField(max_length=80)

	class Meta:
		db_table = "cod_sis"


class GrupoCliente(models.Model):
	id_grupo = models.AutoField(primary_key=True, db_column="id_grupo")
	descricao = models.CharField(max_length=80)

	class Meta:
		db_table = "grupo_cliente"


class TipoVenda(models.Model):
	id_tipo_venda = models.AutoField(primary_key=True, db_column="id_tipo_venda")
	descricao = models.CharField(max_length=80)

	class Meta:
		db_table = "tipo_venda"


class Aliquota(models.Model):
	id_aliquota = models.AutoField(primary_key=True, db_column="id_aliquota")
	valor_percentual = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
	descricao = models.CharField(max_length=80, blank=True, default="")

	class Meta:
		db_table = "aliquota"

	def __str__(self) -> str:
		if self.descricao:
			return self.descricao
		if self.valor_percentual is not None:
			return str(self.valor_percentual)
		return f"Aliquota {self.id_aliquota}"


class Usuario(models.Model):
	id_usuario = models.BigIntegerField(primary_key=True, db_column="id_usuario")
	nome = models.CharField(max_length=120)

	class Meta:
		db_table = "usuario"

	def __str__(self) -> str:
		return self.nome


class FormaPagamento(models.Model):
	id_forma = models.BigIntegerField(primary_key=True, db_column="id_forma")
	descricao = models.CharField(max_length=120)

	class Meta:
		db_table = "forma_pagamento"

	def __str__(self) -> str:
		return self.descricao


class Fornecedor(models.Model):
	id_fornecedor = models.BigIntegerField(primary_key=True)
	nome_fornecedor = models.CharField(max_length=120)
	raz_social = models.CharField(max_length=160, blank=True, default="")
	hash_md5 = models.CharField(max_length=32, blank=True, null=True)
	dt_cadastro = models.DateField(null=True, blank=True)
	id_codsis = models.ForeignKey(
		CodSis,
		null=True,
		blank=True,
		db_column="id_codsis",
		db_constraint=False,
		on_delete=models.SET_NULL,
		related_name="fornecedores",
	)
	codigo = models.CharField(max_length=5, blank=True, default="")
	operador = models.IntegerField(default=0)
	usuario = models.CharField(max_length=100, blank=True, default="")

	class Meta:
		db_table = "fornecedores"

	def save(self, *args, **kwargs):
		self.hash_md5 = gerar_hash_fornecedor(
			id_fornecedor=self.id_fornecedor,
			nome_fornecedor=self.nome_fornecedor,
			raz_social=self.raz_social,
			dt_cadastro=self.dt_cadastro,
		)
		return super().save(*args, **kwargs)


class Cliente(models.Model):
	id_cliente = models.BigIntegerField(primary_key=True)
	nome_cliente = models.CharField(max_length=120)
	raz_social = models.CharField(max_length=160, blank=True, default="")
	hash_md5 = models.CharField(max_length=32, blank=True, null=True)
	prazo_cob = models.IntegerField(default=0)
	id_grupo = models.ForeignKey(
		GrupoCliente,
		null=True,
		blank=True,
		db_column="id_grupo",
		db_constraint=False,
		on_delete=models.SET_NULL,
		related_name="clientes",
	)
	id_tipo_venda = models.ForeignKey(
		TipoVenda,
		null=True,
		blank=True,
		db_column="id_tipo_venda",
		db_constraint=False,
		on_delete=models.SET_NULL,
		related_name="clientes",
	)

	class Meta:
		db_table = "clientes"

	def save(self, *args, **kwargs):
		self.hash_md5 = gerar_hash_cliente(
			id_cliente=self.id_cliente,
			nome_cliente=self.nome_cliente,
			raz_social=self.raz_social,
		)
		return super().save(*args, **kwargs)


class TemplateExportacao(models.Model):
	TIPO_BASICO = "BASICO"
	TIPO_SQL = "SQL"
	TIPOS = (
		(TIPO_BASICO, "BASICO"),
		(TIPO_SQL, "SQL"),
	)

	nome = models.CharField(max_length=120)
	tabela = models.CharField(max_length=40)
	tipo = models.CharField(max_length=10, choices=TIPOS)
	colunas_selecionadas = models.JSONField(null=True, blank=True)
	query_sql = models.TextField(null=True, blank=True)

	class Meta:
		db_table = "template_exportacao"
		ordering = ["nome"]

	def __str__(self) -> str:
		return f"{self.nome} ({self.tabela})"
