from django.contrib import admin

from .models import STG_AuditoriaPlanilha, STG_ItemVenda, STG_PagamentoVenda, STG_Venda


@admin.register(STG_Venda)
class STGVendaAdmin(admin.ModelAdmin):
	list_display = ("id_stg_venda", "tipo_documento", "id_legado", "data_venda", "status_validacao")
	list_filter = ("tipo_documento", "status_validacao", "data_venda")
	search_fields = ("id_legado", "nome_cliente_legado", "nome_usuario_legado")


@admin.register(STG_ItemVenda)
class STGItemVendaAdmin(admin.ModelAdmin):
	list_display = (
		"id_stg_item_venda",
		"tipo_documento",
		"id_venda_legado",
		"id_produto_legado",
		"data_venda",
		"status_validacao",
	)
	list_filter = ("tipo_documento", "status_validacao", "data_venda")
	search_fields = ("id_venda_legado", "id_produto_legado", "nome_produto_legado")


@admin.register(STG_PagamentoVenda)
class STGPagamentoVendaAdmin(admin.ModelAdmin):
	list_display = ("id_stg_pagamento_venda", "tipo_documento", "id_venda_legado", "valor_pago", "status_validacao")
	list_filter = ("tipo_documento", "status_validacao")
	search_fields = ("id_venda_legado", "tipo_pagamento_descricao_legado", "nsu")


@admin.register(STG_AuditoriaPlanilha)
class STGAuditoriaPlanilhaAdmin(admin.ModelAdmin):
	list_display = ("id_stg_auditoria_planilha", "tipo_documento", "id_legado", "data_venda", "valor_total", "status_validacao")
	list_filter = ("tipo_documento", "status_validacao", "data_venda")
	search_fields = ("id_legado", "usuario_nome", "cliente_nome", "tipo_pagamento_descricao")
