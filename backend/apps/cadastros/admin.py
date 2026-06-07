from django.contrib import admin

from .models import FormaPagamento, Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
	list_display = ("id_usuario", "nome")
	search_fields = ("id_usuario", "nome")


@admin.register(FormaPagamento)
class FormaPagamentoAdmin(admin.ModelAdmin):
	list_display = ("id_forma", "descricao")
	search_fields = ("id_forma", "descricao")
