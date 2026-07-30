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
