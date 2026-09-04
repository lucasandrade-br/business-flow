from django.db import models


class DashboardKpiVenda(models.Model):
    # YTD — acumulado 01/Jan até última data do ano atual
    ytd_receita_atual = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    ytd_receita_anterior_equivalente = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    ytd_volume_atual = models.IntegerField(default=0)
    ytd_volume_anterior_equivalente = models.IntegerField(default=0)
    ticket_medio_atual = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    ticket_medio_anterior_equivalente = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # MTD — acumulado 01/mês até dia da última data (corte justo)
    mtd_receita_atual = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    mtd_receita_anterior_equivalente = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # Array de 12 itens: { mes, label, receita_atual, volume_atual, receita_anterior, volume_anterior }
    dados_mensais_grafico = models.JSONField(default=list)

    # Médias utilizam somente períodos calendário encerrados.
    faturamento_semanal_medio_atual = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    faturamento_semanal_medio_anterior_equivalente = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    faturamento_mensal_medio_atual = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    faturamento_mensal_medio_anterior_equivalente = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # Séries mensal/semanal usadas pelos gráficos expandidos do dashboard.
    dados_periodicos_grafico = models.JSONField(default=dict)
    volume_sem_horario_atual = models.IntegerField(default=0)
    faturamento_sem_horario_atual = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    ultima_data_processada = models.DateField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dashboard_kpi_venda"

    def __str__(self) -> str:
        return f"KPI Vendas — {self.ultima_data_processada}"


class DashboardKpiCompra(models.Model):
    ytd_custo_atual = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    ytd_custo_anterior_equivalente = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    mtd_custo_atual = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    mtd_custo_anterior_equivalente = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    fator_retorno_atual = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    fator_retorno_anterior = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    volume_itens_atual = models.IntegerField(default=0)
    volume_itens_anterior = models.IntegerField(default=0)
    dados_mensais_grafico = models.JSONField(default=list)
    ultima_data_processada = models.DateField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dashboard_kpi_compra"

    def __str__(self) -> str:
        return f"KPI Compras — {self.ultima_data_processada}"


class DreMensalConsolidada(models.Model):
    ano = models.IntegerField(db_index=True)
    mes = models.IntegerField()
    total_receita = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_custo   = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dre_mensal_consolidada"
        unique_together = ("ano", "mes")

    def __str__(self) -> str:
        return f"DRE {self.ano}/{self.mes:02d}"


class MovimentoDiario(models.Model):
    SEM_TIPO_ID = 0
    SEM_TIPO_NOME = "Sem Tipo / Balcão"

    data = models.DateField(db_index=True)
    # Sentinela 0 em vez de FK nulável: unique_together com NULL não barra duplicidade.
    tipo_venda_id = models.IntegerField(db_index=True)
    tipo_venda_nome = models.CharField(max_length=80)
    qtd_vendas = models.IntegerField(default=0)
    valor_total = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "movimento_diario"
        unique_together = ("data", "tipo_venda_id")

    def __str__(self) -> str:
        return f"{self.data} — {self.tipo_venda_nome}: {self.qtd_vendas}"


class MovimentoProdutoMensal(models.Model):
    """Resumo mensal de vendas por produto e unidade para consultas analiticas."""

    SEM_UNIDADE_ID = 0
    SEM_UNIDADE_SIGLA = "SEM UN."

    ano = models.IntegerField(db_index=True)
    mes = models.PositiveSmallIntegerField()
    produto = models.ForeignKey(
        "cadastros.Produto",
        db_column="id_produto",
        on_delete=models.CASCADE,
        related_name="movimentos_mensais",
    )
    # A sentinela zero evita duplicidades permitidas por UNIQUE com NULL no MySQL.
    unidade_medida_id_origem = models.IntegerField(default=SEM_UNIDADE_ID)
    unidade_sigla = models.CharField(max_length=20, default=SEM_UNIDADE_SIGLA)
    receita_bruta = models.DecimalField(max_digits=24, decimal_places=6, default=0)
    quantidade = models.DecimalField(max_digits=24, decimal_places=6, default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "movimento_produto_mensal"
        constraints = [
            models.UniqueConstraint(
                fields=["ano", "mes", "produto", "unidade_medida_id_origem"],
                name="uniq_mov_produto_mes_unidade",
            ),
        ]
        indexes = [
            models.Index(fields=["ano", "mes"], name="idx_mov_prod_ano_mes"),
            models.Index(fields=["produto", "ano", "mes"], name="idx_mov_produto_periodo"),
        ]


class StatusMovimentoProdutoMensal(models.Model):
    STATUS_PROCESSANDO = "PROCESSANDO"
    STATUS_PRONTO = "PRONTO"
    STATUS_FALHA = "FALHA"
    STATUS_CHOICES = (
        (STATUS_PROCESSANDO, "Processando"),
        (STATUS_PRONTO, "Pronto"),
        (STATUS_FALHA, "Falha"),
    )

    ano = models.IntegerField(db_index=True)
    mes = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PROCESSANDO)
    erro = models.TextField(blank=True, default="")
    ultimo_sucesso_em = models.DateTimeField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "status_movimento_produto_mensal"
        constraints = [
            models.UniqueConstraint(fields=["ano", "mes"], name="uniq_status_mov_prod_periodo"),
        ]
        indexes = [models.Index(fields=["ano", "status"], name="idx_status_mov_prod_ano")]


class MovimentoCompraProdutoMensal(models.Model):
    """Resumo mensal de compras por produto, fornecedor e unidade."""

    SEM_UNIDADE_ID = 0
    SEM_UNIDADE_SIGLA = "SEM UN."

    ano = models.IntegerField(db_index=True)
    mes = models.PositiveSmallIntegerField()
    produto = models.ForeignKey(
        "cadastros.Produto",
        db_column="id_produto",
        on_delete=models.CASCADE,
        related_name="movimentos_compra_mensais",
    )
    fornecedor = models.ForeignKey(
        "cadastros.Fornecedor",
        db_column="id_fornecedor",
        on_delete=models.CASCADE,
        related_name="movimentos_compra_mensais",
    )
    unidade_medida_id_origem = models.IntegerField(default=SEM_UNIDADE_ID)
    unidade_sigla = models.CharField(max_length=20, default=SEM_UNIDADE_SIGLA)
    valor_comprado = models.DecimalField(max_digits=24, decimal_places=6, default=0)
    quantidade = models.DecimalField(max_digits=24, decimal_places=6, default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "movimento_compra_produto_mensal"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "ano",
                    "mes",
                    "produto",
                    "fornecedor",
                    "unidade_medida_id_origem",
                ],
                name="uniq_mov_compra_prod_mes_fornec_un",
            ),
        ]
        indexes = [
            models.Index(fields=["ano", "mes"], name="idx_mov_compra_ano_mes"),
            models.Index(fields=["produto", "ano", "mes"], name="idx_mov_compra_prod_periodo"),
            models.Index(fields=["fornecedor", "ano", "mes"], name="idx_mov_compra_forn_periodo"),
        ]


class StatusMovimentoCompraProdutoMensal(models.Model):
    STATUS_PROCESSANDO = "PROCESSANDO"
    STATUS_PRONTO = "PRONTO"
    STATUS_FALHA = "FALHA"
    STATUS_CHOICES = (
        (STATUS_PROCESSANDO, "Processando"),
        (STATUS_PRONTO, "Pronto"),
        (STATUS_FALHA, "Falha"),
    )

    ano = models.IntegerField(db_index=True)
    mes = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PROCESSANDO)
    erro = models.TextField(blank=True, default="")
    ultimo_sucesso_em = models.DateTimeField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "status_movimento_compra_produto_mensal"
        constraints = [
            models.UniqueConstraint(
                fields=["ano", "mes"],
                name="uniq_status_mov_compra_prod_periodo",
            ),
        ]
        indexes = [models.Index(fields=["ano", "status"], name="idx_status_mov_compra_ano")]
