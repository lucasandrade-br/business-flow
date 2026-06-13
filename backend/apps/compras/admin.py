from django.contrib import admin

from apps.compras.models import Compra, ItemCompra, STG_Compra, STG_ItemCompra


@admin.register(STG_Compra)
class STGCompraAdmin(admin.ModelAdmin):
    list_display = (
        "id_stg_compra",
        "id_compra_legado",
        "nota",
        "id_fornecedor_legado",
        "data_emissao",
        "valor_total",
        "status_validacao",
        "status_tratamento",
    )
    search_fields = ("id_compra_legado", "nota", "nome_fornecedor_legado")
    list_filter = ("status_validacao", "status_tratamento", "data_emissao")


@admin.register(STG_ItemCompra)
class STGItemCompraAdmin(admin.ModelAdmin):
    list_display = (
        "id_stg_item_compra",
        "id_compra_legado",
        "id_produto_legado",
        "unidade_legado",
        "quantidade",
        "valor_custo",
        "valor_total_calculado",
    )
    search_fields = ("id_compra_legado", "id_produto_legado", "nome_produto_legado")


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = (
        "id_compra",
        "id_legado",
        "nota",
        "fornecedor",
        "data_emissao",
        "valor_total_documento",
        "momento_consolidacao",
    )
    search_fields = ("id_legado", "nota", "fornecedor__nome_fornecedor")
    list_filter = ("data_emissao",)


@admin.register(ItemCompra)
class ItemCompraAdmin(admin.ModelAdmin):
    list_display = (
        "id_item_compra",
        "compra",
        "produto",
        "quantidade",
        "valor_custo",
        "valor_total_item",
    )
    search_fields = ("compra__id_legado", "produto__produto")
