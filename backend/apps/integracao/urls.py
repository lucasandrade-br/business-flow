from django.urls import path

from .views import FirebirdConnectionConfigAPIView, FirebirdFilePickerAPIView, SincronizarERPAPIView

urlpatterns = [
    path("api/integracao/firebird-config", FirebirdConnectionConfigAPIView.as_view(), name="integracao-firebird-config"),
    path("api/integracao/firebird-picker", FirebirdFilePickerAPIView.as_view(), name="integracao-firebird-picker"),
    path("api/integracao/sincronizar", SincronizarERPAPIView.as_view(), name="integracao-sincronizar"),
]
