from django.urls import path

from apps.vendas.views import (
    ItemVendaListAPIView,
    PagamentoVendaListAPIView,
    VendaDetailAPIView,
    VendaListAPIView,
)

urlpatterns = [
    path("vendas", VendaListAPIView.as_view(), name="vendas-list"),
    path("vendas/<int:id_venda>", VendaDetailAPIView.as_view(), name="vendas-detail"),
    path("itens", ItemVendaListAPIView.as_view(), name="itens-venda-list"),
    path("pagamentos", PagamentoVendaListAPIView.as_view(), name="pagamentos-venda-list"),
]
