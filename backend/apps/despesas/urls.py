from django.urls import path

from . import views

urlpatterns = [
    path("categorias/", views.CategoriasView.as_view()),
    path("categorias/lote/", views.CategoriasLoteView.as_view()),
    path("categorias/<int:pk>/vinculos/", views.CategoriaVinculosView.as_view()),
    path("categorias/<int:pk>/", views.CategoriaDetailView.as_view()),
    path("tipos/", views.TiposView.as_view()),
    path("tipos/<int:pk>/", views.TipoDetailView.as_view()),
    path("tipos/<int:pk>/vinculo/", views.VinculoView.as_view()),
    path("lotes/", views.LotesView.as_view()),
    path("lotes/<int:lote_id>/", views.LoteDetailView.as_view()),
    path("lotes/<int:lote_id>/linhas/", views.LinhasView.as_view()),
    path("lotes/<int:lote_id>/resumo/", views.ResumoLoteView.as_view()),
    path("lotes/<int:lote_id>/revalidar/", views.RevalidarLoteView.as_view()),
    path("lotes/<int:lote_id>/linhas/<int:linha_id>/", views.LinhaResolverView.as_view()),
    path("lotes/<int:lote_id>/consolidar/", views.ConsolidarLoteView.as_view()),
    path("movimentos/", views.MovimentosView.as_view()),
    path("movimentos/<int:pk>/", views.MovimentoDetailView.as_view()),
    path("pagamentos/", views.PagamentosView.as_view()),
    path("pagamentos/<int:pk>/", views.PagamentoDetailView.as_view()),
    path("conflitos/", views.ConflitosView.as_view()),
    path("conflitos/<int:pk>/resolver/", views.ResolverConflitoView.as_view()),
    path("auditoria/", views.AuditoriaView.as_view()),
    path("bi/", views.BIView.as_view()),
    path("bi/tipos/", views.BITiposView.as_view()),
    path("bi/movimentos/", views.BIMovimentosView.as_view()),
]
