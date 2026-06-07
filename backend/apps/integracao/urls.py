from django.urls import path

from .views import SincronizarERPAPIView

urlpatterns = [
    path("api/integracao/sincronizar", SincronizarERPAPIView.as_view(), name="integracao-sincronizar"),
]
