from django.urls import path

from .views import (
    AprovarClienteAPIView,
    AprovarFornecedorAPIView,
    AprovarProdutoAPIView,
    ClientesPendentesAPIView,
    FornecedoresPendentesAPIView,
    ProdutosPendentesAPIView,
    ResumoPendenciasAPIView,
)

urlpatterns = [
    path("api/validacao/resumo", ResumoPendenciasAPIView.as_view(), name="validacao-resumo"),
    path("api/validacao/produtos/pendentes", ProdutosPendentesAPIView.as_view(), name="produtos-pendentes"),
    path("api/validacao/produtos/aprovar", AprovarProdutoAPIView.as_view(), name="aprovar-produto"),
    path("api/validacao/clientes/pendentes", ClientesPendentesAPIView.as_view(), name="validacao-clientes-pendentes"),
    path("api/validacao/clientes/aprovar", AprovarClienteAPIView.as_view(), name="validacao-clientes-aprovar"),
    path("api/validacao/fornecedores/pendentes", FornecedoresPendentesAPIView.as_view(), name="validacao-fornecedores-pendentes"),
    path("api/validacao/fornecedores/aprovar", AprovarFornecedorAPIView.as_view(), name="validacao-fornecedores-aprovar"),
]
