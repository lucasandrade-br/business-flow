from django.core.exceptions import ValidationError
from django.db import models


class CategoriaDespesa(models.Model):
    nome = models.CharField(max_length=180)
    caminho = models.CharField(max_length=255, unique=True)
    nivel = models.PositiveSmallIntegerField()
    pai = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="filhas")
    codigo_origem = models.CharField(max_length=60, blank=True, default="")

    class Meta:
        ordering = ["caminho"]

    def clean(self):
        if len(self.caminho) > 255:
            raise ValidationError({"caminho": "O caminho da categoria excede 255 caracteres."})
        if self.pai_id and self.pai_id == self.pk:
            raise ValidationError({"pai": "Uma categoria não pode ser sua própria mãe."})
        if self.pai_id and self.pai.nivel + 1 != self.nivel:
            raise ValidationError({"nivel": "O nível deve seguir o nó pai."})
        if not self.pai_id and self.nivel != 0:
            raise ValidationError({"nivel": "A família deve ter nível zero."})

    def __str__(self):
        return self.caminho


class TipoDespesa(models.Model):
    nome = models.CharField(max_length=220)
    chave = models.CharField(max_length=220, unique=True)
    ativo = models.BooleanField(default=True)
    codigo_origem = models.CharField(max_length=60, blank=True, default="")

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class VinculoTipoDespesa(models.Model):
    tipo = models.ForeignKey(TipoDespesa, on_delete=models.CASCADE, related_name="vinculos")
    familia = models.ForeignKey(CategoriaDespesa, on_delete=models.PROTECT, related_name="vinculos_familia")
    folha = models.ForeignKey(CategoriaDespesa, on_delete=models.PROTECT, related_name="tipos_vinculados")
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tipo", "familia"], name="despesa_tipo_familia_unica")]

    def clean(self):
        if not self.familia_id or self.familia.pai_id is not None:
            raise ValidationError({"familia": "Selecione uma família raiz."})
        if not self.folha_id or self.folha.filhas.exists():
            raise ValidationError({"folha": "Selecione uma categoria folha."})
        atual = self.folha
        visitados = set()
        while atual.pai_id:
            if atual.pk in visitados:
                raise ValidationError("Ciclo na árvore de despesas.")
            visitados.add(atual.pk)
            atual = atual.pai
        if atual.pk != self.familia_id:
            raise ValidationError({"folha": "A folha não pertence à família selecionada."})


class MovimentoDespesa(models.Model):
    ORIGENS = [("MANUAL", "Manual"), ("XLSX", "Planilha")]
    id_origem = models.CharField(max_length=120, unique=True, null=True, blank=True)
    chave_base = models.CharField(max_length=64, blank=True, default="", db_index=True)
    origem = models.CharField(max_length=12, choices=ORIGENS, default="MANUAL")
    tipo = models.ForeignKey(TipoDespesa, on_delete=models.PROTECT, related_name="movimentacoes")
    fornecedor = models.ForeignKey("cadastros.Fornecedor", null=True, blank=True, on_delete=models.SET_NULL)
    fornecedor_texto = models.CharField(max_length=220, blank=True, default="")
    documento = models.CharField(max_length=120, blank=True, default="")
    observacoes = models.TextField(blank=True, default="")
    emissao = models.DateField(null=True, blank=True)
    vencimento = models.DateField()
    valor = models.DecimalField(max_digits=18, decimal_places=2)
    campos_manuais = models.JSONField(default=list, blank=True)
    dados_origem = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.valor is None or self.valor < 0:
            raise ValidationError({"valor": "O valor não pode ser negativo."})


class PagamentoDespesa(models.Model):
    movimento = models.ForeignKey(MovimentoDespesa, on_delete=models.CASCADE, related_name="pagamentos")
    id_origem = models.CharField(max_length=145, unique=True, null=True, blank=True)
    data = models.DateField()
    valor = models.DecimalField(max_digits=18, decimal_places=2)
    forma = models.CharField(max_length=80, blank=True, default="")
    origem = models.CharField(max_length=12, choices=MovimentoDespesa.ORIGENS, default="MANUAL")
    campos_manuais = models.JSONField(default=list, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.valor is None or self.valor <= 0:
            raise ValidationError({"valor": "O pagamento deve ser positivo."})


class AuditoriaDespesa(models.Model):
    entidade = models.CharField(max_length=30)
    entidade_id = models.BigIntegerField()
    acao = models.CharField(max_length=40)
    antes = models.JSONField(default=dict)
    depois = models.JSONField(default=dict)
    operador = models.CharField(max_length=120, blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)


class LoteDespesa(models.Model):
    nome_arquivo = models.CharField(max_length=255)
    arquivo = models.FileField(upload_to="despesas/lotes/%Y/%m/")
    hash_sha256 = models.CharField(max_length=64)
    # Apenas a captura corrente usa esta chave; UNIQUE permite várias históricas nulas.
    chave_ativa = models.CharField(max_length=12, unique=True, null=True, blank=True, default=None)
    status = models.CharField(max_length=20, default="VALIDADO")
    total_linhas = models.PositiveIntegerField(default=0)
    prontas = models.PositiveIntegerField(default=0)
    pendentes = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)


class LinhaDespesa(models.Model):
    lote = models.ForeignKey(LoteDespesa, on_delete=models.CASCADE, related_name="linhas")
    numero = models.PositiveIntegerField()
    id_origem = models.CharField(max_length=120, blank=True, default="")
    tipo = models.ForeignKey(TipoDespesa, null=True, blank=True, on_delete=models.SET_NULL)
    dados = models.JSONField(default=dict)
    erros = models.JSONField(default=list)
    status = models.CharField(max_length=20, default="PENDENTE")
    movimento = models.ForeignKey(MovimentoDespesa, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["lote", "numero"], name="despesa_lote_linha_unica")]


class ConflitoDespesa(models.Model):
    movimento = models.ForeignKey(MovimentoDespesa, on_delete=models.CASCADE, related_name="conflitos")
    linha = models.ForeignKey(LinhaDespesa, on_delete=models.CASCADE)
    campo = models.CharField(max_length=50)
    valor_atual = models.JSONField(null=True, blank=True)
    valor_origem = models.JSONField(null=True, blank=True)
    resolvido = models.BooleanField(default=False)
    resolvido_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["linha", "campo"], name="despesa_conflito_linha_campo_unico")]


class AgregadoDespesaMensal(models.Model):
    BASES = [("VENCIMENTO", "Obrigações"), ("PAGAMENTO", "Saídas")]
    mes = models.DateField()
    tipo = models.ForeignKey(TipoDespesa, on_delete=models.CASCADE)
    base = models.CharField(max_length=12, choices=BASES)
    valor = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["mes", "tipo", "base"], name="despesa_agregado_mes_tipo_base")]


class AgregadoDespesaDiario(models.Model):
    dia = models.DateField()
    tipo = models.ForeignKey(TipoDespesa, on_delete=models.CASCADE)
    base = models.CharField(max_length=12, choices=AgregadoDespesaMensal.BASES)
    valor = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["dia", "tipo", "base"], name="despesa_agregado_dia_tipo_base")]
        indexes = [models.Index(fields=["base", "dia"], name="despesa_diario_base_dia")]


class SnapshotDespesaMensal(models.Model):
    mes = models.DateField()
    base = models.CharField(max_length=12, choices=AgregadoDespesaMensal.BASES)
    status = models.CharField(max_length=12, default="PENDENTE")
    atualizado_em = models.DateTimeField(null=True, blank=True)
    diario_atualizado_em = models.DateTimeField(null=True, blank=True)
    erro = models.TextField(blank=True, default="")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["mes", "base"], name="despesa_snapshot_mes_base")]
