from django.urls import path
from . import views

urlpatterns = [
    path("categorias/vendas/quarentena/", views.QuarentenaCategoriasView.as_view(), name="analise-vendas-quarentena"),
    path("categorias/vendas/quarentena/matriz/", views.matriz_quarentena_categorias, name="analise-vendas-quarentena-matriz"),
    path("categorias/vendas/quarentena/<int:categoria_id>/", views.QuarentenaCategoriaDetailView.as_view(), name="analise-vendas-quarentena-detail"),
    path("categorias/vendas/", views.vendas_por_categorias, name="analise-vendas-categorias"),
    path("categorias/vendas/semanal/", views.vendas_por_categorias_semanal, name="analise-vendas-categorias-semanal"),
    path("categorias/vendas/anual/", views.vendas_por_categorias_anual, name="analise-vendas-categorias-anual"),
    path("categorias/vendas/oscilacoes/", views.oscilacoes_vendas_categorias, name="analise-vendas-categorias-oscilacoes"),
    path("categorias/produtos/vendas/", views.vendas_por_produtos, name="analise-vendas-produtos"),
    path("categorias/produtos/vendas/semanal/", views.vendas_por_produtos_semanal, name="analise-vendas-produtos-semanal"),
    path("categorias/produtos/vendas/anual/", views.vendas_por_produtos_anual, name="analise-vendas-produtos-anual"),
    path("categorias/compras/", views.compras_por_categorias, name="analise-compras-categorias"),
    path("categorias/compras/semanal/", views.compras_por_categorias_semanal, name="analise-compras-categorias-semanal"),
    path("categorias/compras/anual/", views.compras_por_categorias_anual, name="analise-compras-categorias-anual"),
    path("categorias/produtos/compras/", views.compras_por_produtos, name="analise-compras-produtos"),
    path("categorias/produtos/compras/semanal/", views.compras_por_produtos_semanal, name="analise-compras-produtos-semanal"),
    path("categorias/produtos/compras/anual/", views.compras_por_produtos_anual, name="analise-compras-produtos-anual"),
    path("dashboard/kpis/", views.dashboard_kpis, name="dashboard-kpis"),
    path("dashboard/kpis-compras/", views.dashboard_kpis_compras, name="dashboard-kpis-compras"),
    path("dashboard/dre/", views.dre_dashboard, name="dashboard-dre"),
    path("dashboard/dre/anual/", views.dre_anual, name="dashboard-dre-anual"),
    path("dashboard/dre/mensal/", views.dre_mensal, name="dashboard-dre-mensal"),
    path("dashboard/movimento-clientes/", views.movimento_clientes, name="dashboard-movimento-clientes"),
]
