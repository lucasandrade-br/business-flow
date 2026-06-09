from django.urls import path

from .views import (
    AprovarClienteAPIView,
    AprovarFornecedorAPIView,
    AprovarProdutoAPIView,
    ClientesPendentesAPIView,
    FornecedoresPendentesAPIView,
    ImportarAuditoriaPlanilhaAPIView,
    ImportarAuditoriaPlanilhaStatusAPIView,
    ProdutosPendentesAPIView,
    ReconciliacaoDivergenciasAPIView,
    ReconciliacaoFormasPagamentoAPIView,
    ReconciliacaoTratarDivergenciaAPIView,
    ReconciliacaoTratarDivergenciaLoteAPIView,
    ResumoPendenciasAPIView,
    ConsolidarVendasSOTAPIView,
    SincronizarVendasFirebirdAPIView,
)

urlpatterns = [
    path("api/validacao/resumo", ResumoPendenciasAPIView.as_view(), name="validacao-resumo"),
    path("api/validacao/produtos/pendentes", ProdutosPendentesAPIView.as_view(), name="produtos-pendentes"),
    path("api/validacao/produtos/aprovar", AprovarProdutoAPIView.as_view(), name="aprovar-produto"),
    path("api/validacao/clientes/pendentes", ClientesPendentesAPIView.as_view(), name="validacao-clientes-pendentes"),
    path("api/validacao/clientes/aprovar", AprovarClienteAPIView.as_view(), name="validacao-clientes-aprovar"),
    path("api/validacao/fornecedores/pendentes", FornecedoresPendentesAPIView.as_view(), name="validacao-fornecedores-pendentes"),
    path("api/validacao/fornecedores/aprovar", AprovarFornecedorAPIView.as_view(), name="validacao-fornecedores-aprovar"),
    path("api/validacao/sincronizar-vendas-firebird", SincronizarVendasFirebirdAPIView.as_view(), name="validacao-sincronizar-vendas-firebird"),
    path("api/validacao/importar-auditoria-planilhas", ImportarAuditoriaPlanilhaAPIView.as_view(), name="validacao-importar-auditoria-planilhas"),
    path("api/validacao/importar-auditoria-planilhas/status/<str:job_id>", ImportarAuditoriaPlanilhaStatusAPIView.as_view(), name="validacao-importar-auditoria-planilhas-status"),
    path("api/validacao/reconciliacao/divergencias", ReconciliacaoDivergenciasAPIView.as_view(), name="validacao-reconciliacao-divergencias"),
    path("api/validacao/reconciliacao/formas-pagamento", ReconciliacaoFormasPagamentoAPIView.as_view(), name="validacao-reconciliacao-formas-pagamento"),
    path("api/validacao/reconciliacao/divergencias/tratar", ReconciliacaoTratarDivergenciaAPIView.as_view(), name="validacao-reconciliacao-divergencias-tratar"),
    path("api/validacao/reconciliacao/divergencias/tratar-lote", ReconciliacaoTratarDivergenciaLoteAPIView.as_view(), name="validacao-reconciliacao-divergencias-tratar-lote"),
    path("api/validacao/consolidar-vendas-sot", ConsolidarVendasSOTAPIView.as_view(), name="validacao-consolidar-vendas-sot"),
]
