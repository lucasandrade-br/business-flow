from django.urls import path

from apps.compras.views import (
    CompraDetailAPIView,
    CompraListAPIView,
    ConsolidarComprasSOTAPIView,
    ItemCompraListAPIView,
    ReconciliacaoComprasDivergenciasAPIView,
    ReconciliacaoComprasKPIsAPIView,
    ReconciliacaoComprasLimparFluxoAPIView,
    ReconciliacaoComprasTratarDivergenciaAPIView,
    ReconciliacaoComprasTratarDivergenciaLoteAPIView,
    SincronizarComprasFirebirdAPIView,
)

urlpatterns = [
    path("compras", CompraListAPIView.as_view(), name="compras-list"),
    path("compras/<int:id_compra>", CompraDetailAPIView.as_view(), name="compras-detail"),
    path("itens", ItemCompraListAPIView.as_view(), name="itens-compra-list"),
    path("sincronizar-firebird", SincronizarComprasFirebirdAPIView.as_view(), name="compras-sincronizar-firebird"),
    path("reconciliacao/kpis", ReconciliacaoComprasKPIsAPIView.as_view(), name="compras-reconciliacao-kpis"),
    path("reconciliacao/divergencias", ReconciliacaoComprasDivergenciasAPIView.as_view(), name="compras-reconciliacao-divergencias"),
    path("reconciliacao/divergencias/tratar", ReconciliacaoComprasTratarDivergenciaAPIView.as_view(), name="compras-reconciliacao-divergencias-tratar"),
    path("reconciliacao/divergencias/tratar-lote", ReconciliacaoComprasTratarDivergenciaLoteAPIView.as_view(), name="compras-reconciliacao-divergencias-tratar-lote"),
    path("reconciliacao/limpar-fluxo", ReconciliacaoComprasLimparFluxoAPIView.as_view(), name="compras-reconciliacao-limpar-fluxo"),
    path("consolidar-sot", ConsolidarComprasSOTAPIView.as_view(), name="compras-consolidar-sot"),
]
