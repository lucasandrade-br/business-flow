from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/kpis/", views.dashboard_kpis, name="dashboard-kpis"),
    path("dashboard/kpis-compras/", views.dashboard_kpis_compras, name="dashboard-kpis-compras"),
    path("dashboard/dre/", views.dre_dashboard, name="dashboard-dre"),
    path("dashboard/movimento-clientes/", views.movimento_clientes, name="dashboard-movimento-clientes"),
]
