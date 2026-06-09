from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AliquotaDetailAPIView,
    AliquotaListCreateAPIView,
    ClienteDetailAPIView,
    ClienteListCreateAPIView,
    ExportacaoUniversalAPIView,
    FormaPagamentoDetailAPIView,
    FormaPagamentoListCreateAPIView,
    FornecedorDetailAPIView,
    FornecedorListCreateAPIView,
    GrupoClienteDetailAPIView,
    GrupoClienteListCreateAPIView,
    PlanoContaDetailAPIView,
    PlanoContaArvoreAPIView,
    PlanoContaListCreateAPIView,
    PlanoContaViewSet,
    ProdutoDetailAPIView,
    ProdutoListCreateAPIView,
    TemplateExportacaoViewSet,
    TipoVendaDetailAPIView,
    TipoVendaListCreateAPIView,
    UnidadeMedidaDetailAPIView,
    UnidadeMedidaListCreateAPIView,
)

router = DefaultRouter()
router.register(r"templates-exportacao", TemplateExportacaoViewSet, basename="templates-exportacao")

urlpatterns = [
    path("unidades-medida", UnidadeMedidaListCreateAPIView.as_view(), name="cadastros-unidades-medida"),
    path("unidades-medida/<int:id_und_medida>", UnidadeMedidaDetailAPIView.as_view(), name="cadastros-unidades-medida-detail"),
    path("plano-contas", PlanoContaListCreateAPIView.as_view(), name="cadastros-plano-contas"),
    path("plano-contas/<int:id_conta>", PlanoContaDetailAPIView.as_view(), name="cadastros-plano-contas-detail"),
    path("plano-contas/lote", PlanoContaViewSet.as_view({"post": "lote"}), name="cadastros-plano-contas-lote"),
    path("plano-contas/lote/", PlanoContaViewSet.as_view({"post": "lote"}), name="cadastros-plano-contas-lote-slash"),
    path(
        "plano-contas/<int:id_conta>/vincular-produtos",
        PlanoContaViewSet.as_view({"post": "vincular_produtos"}),
        name="cadastros-plano-contas-vincular-produtos",
    ),
    path(
        "plano-contas/<int:id_conta>/vincular-produtos/",
        PlanoContaViewSet.as_view({"post": "vincular_produtos"}),
        name="cadastros-plano-contas-vincular-produtos-slash",
    ),
    path("plano-contas/arvore", PlanoContaArvoreAPIView.as_view(), name="cadastros-plano-contas-arvore"),
    path("produtos", ProdutoListCreateAPIView.as_view(), name="cadastros-produtos"),
    path("produtos/<int:id_produto>", ProdutoDetailAPIView.as_view(), name="cadastros-produtos-detail"),
    path("clientes", ClienteListCreateAPIView.as_view(), name="cadastros-clientes"),
    path("clientes/<int:id_cliente>", ClienteDetailAPIView.as_view(), name="cadastros-clientes-detail"),
    path("grupos-cliente", GrupoClienteListCreateAPIView.as_view(), name="cadastros-grupos-cliente"),
    path("grupos-cliente/<int:id_grupo>", GrupoClienteDetailAPIView.as_view(), name="cadastros-grupos-cliente-detail"),
    path("tipos-venda", TipoVendaListCreateAPIView.as_view(), name="cadastros-tipos-venda"),
    path("tipos-venda/<int:id_tipo_venda>", TipoVendaDetailAPIView.as_view(), name="cadastros-tipos-venda-detail"),
    path("aliquotas", AliquotaListCreateAPIView.as_view(), name="cadastros-aliquotas"),
    path("aliquotas/<int:id_aliquota>", AliquotaDetailAPIView.as_view(), name="cadastros-aliquotas-detail"),
    path("formas-pagamento", FormaPagamentoListCreateAPIView.as_view(), name="cadastros-formas-pagamento"),
    path("formas-pagamento/<int:id_forma>", FormaPagamentoDetailAPIView.as_view(), name="cadastros-formas-pagamento-detail"),
    path("fornecedores", FornecedorListCreateAPIView.as_view(), name="cadastros-fornecedores"),
    path("fornecedores/<int:id_fornecedor>", FornecedorDetailAPIView.as_view(), name="cadastros-fornecedores-detail"),
    path("exportar", ExportacaoUniversalAPIView.as_view(), name="cadastros-exportar"),
    path("", include(router.urls)),
]
