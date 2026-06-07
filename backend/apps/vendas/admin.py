from django.contrib import admin

from .models import ItemVenda, PagamentoVenda, Venda


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
	list_display = ("id_venda", "id_legado", "tipo_documento", "data_venda", "valor_total_documento")
	list_filter = ("tipo_documento", "data_venda")
	search_fields = ("id_venda", "id_legado")


@admin.register(ItemVenda)
class ItemVendaAdmin(admin.ModelAdmin):
	list_display = ("id_item_venda", "venda", "produto", "quantidade", "valor_total_item", "cancelado")
	list_filter = ("cancelado",)
	search_fields = ("id_item_venda", "venda__id_legado", "produto__id_produto")


@admin.register(PagamentoVenda)
class PagamentoVendaAdmin(admin.ModelAdmin):
	list_display = ("id_pagamento_venda", "venda", "forma_pagamento", "valor_pago")
	search_fields = ("id_pagamento_venda", "venda__id_legado", "forma_pagamento__descricao")
