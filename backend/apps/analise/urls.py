from django.urls import path
from . import views

urlpatterns = [
    path("categorias/vendas/", views.vendas_por_categorias, name="analise-vendas-categorias"),
    path("categorias/produtos/vendas/", views.vendas_por_produtos, name="analise-vendas-produtos"),
    path("categorias/compras/", views.compras_por_categorias, name="analise-compras-categorias"),
    path("categorias/produtos/compras/", views.compras_por_produtos, name="analise-compras-produtos"),
    path("dashboard/kpis/", views.dashboard_kpis, name="dashboard-kpis"),
    path("dashboard/kpis-compras/", views.dashboard_kpis_compras, name="dashboard-kpis-compras"),
    path("dashboard/dre/", views.dre_dashboard, name="dashboard-dre"),
    path("dashboard/movimento-clientes/", views.movimento_clientes, name="dashboard-movimento-clientes"),
]
