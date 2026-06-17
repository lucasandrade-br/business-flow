from __future__ import annotations

from rest_framework import serializers

from apps.vendas.models import ItemVenda, PagamentoVenda, Venda


class VendaListSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.SerializerMethodField()
    usuario_nome = serializers.CharField(source="usuario.nome", read_only=True)

    class Meta:
        model = Venda
        fields = [
            "id_venda",
            "id_legado",
            "tipo_documento",
            "data_venda",
            "hora_venda",
            "status",
            "cliente",
            "cliente_nome",
            "usuario",
            "usuario_nome",
            "valor_total_documento",
            "momento_consolidacao",
        ]

    def get_cliente_nome(self, obj: Venda) -> str:
        if obj.cliente is None:
            return ""
        return obj.cliente.nome_gerencial or obj.cliente.nome_cliente


class ItemVendaDetalheSerializer(serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField()
    unidade_sigla = serializers.CharField(source="unidade_medida.sigla", read_only=True)

    class Meta:
        model = ItemVenda
        fields = [
            "id_item_venda",
            "produto",
            "produto_nome",
            "unidade_medida",
            "unidade_sigla",
            "quantidade",
            "valor_unitario",
            "valor_total_item",
            "cancelado",
        ]

    def get_produto_nome(self, obj: ItemVenda) -> str:
        if obj.produto is None:
            return ""
        return obj.produto.nome_gerencial or obj.produto.produto


class PagamentoVendaDetalheSerializer(serializers.ModelSerializer):
    forma_pagamento_descricao = serializers.CharField(source="forma_pagamento.descricao", read_only=True)

    class Meta:
        model = PagamentoVenda
        fields = [
            "id_pagamento_venda",
            "forma_pagamento",
            "forma_pagamento_descricao",
            "valor_pago",
            "estorno",
        ]


class VendaDetailSerializer(VendaListSerializer):
    itens = ItemVendaDetalheSerializer(many=True, read_only=True)
    pagamentos = PagamentoVendaDetalheSerializer(many=True, read_only=True)

    class Meta(VendaListSerializer.Meta):
        fields = [
            *VendaListSerializer.Meta.fields,
            "itens",
            "pagamentos",
        ]


class ItemVendaListSerializer(serializers.ModelSerializer):
    id_legado_venda = serializers.IntegerField(source="venda.id_legado", read_only=True)
    tipo_documento = serializers.CharField(source="venda.tipo_documento", read_only=True)
    data_venda = serializers.DateField(source="venda.data_venda", read_only=True)
    cliente = serializers.IntegerField(source="venda.cliente_id", read_only=True, allow_null=True)
    cliente_nome = serializers.SerializerMethodField()
    produto_nome = serializers.SerializerMethodField()
    unidade_sigla = serializers.CharField(source="unidade_medida.sigla", read_only=True)

    class Meta:
        model = ItemVenda
        fields = [
            "id_item_venda",
            "venda",
            "id_legado_venda",
            "tipo_documento",
            "data_venda",
            "cliente",
            "cliente_nome",
            "produto",
            "produto_nome",
            "unidade_medida",
            "unidade_sigla",
            "quantidade",
            "valor_unitario",
            "valor_total_item",
            "cancelado",
        ]

    def get_produto_nome(self, obj: ItemVenda) -> str:
        if obj.produto is None:
            return ""
        return obj.produto.nome_gerencial or obj.produto.produto

    def get_cliente_nome(self, obj: ItemVenda) -> str:
        if obj.venda is None or obj.venda.cliente is None:
            return ""
        return obj.venda.cliente.nome_gerencial or obj.venda.cliente.nome_cliente


class PagamentoVendaListSerializer(serializers.ModelSerializer):
    id_legado_venda = serializers.IntegerField(source="venda.id_legado", read_only=True)
    tipo_documento = serializers.CharField(source="venda.tipo_documento", read_only=True)
    data_venda = serializers.DateField(source="venda.data_venda", read_only=True)
    cliente = serializers.IntegerField(source="venda.cliente_id", read_only=True, allow_null=True)
    cliente_nome = serializers.SerializerMethodField()
    forma_pagamento_descricao = serializers.CharField(source="forma_pagamento.descricao", read_only=True)

    class Meta:
        model = PagamentoVenda
        fields = [
            "id_pagamento_venda",
            "venda",
            "id_legado_venda",
            "tipo_documento",
            "data_venda",
            "cliente",
            "cliente_nome",
            "forma_pagamento",
            "forma_pagamento_descricao",
            "valor_pago",
            "estorno",
        ]

    def get_cliente_nome(self, obj: PagamentoVenda) -> str:
        if obj.venda is None or obj.venda.cliente is None:
            return ""
        return obj.venda.cliente.nome_gerencial or obj.venda.cliente.nome_cliente
