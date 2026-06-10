from __future__ import annotations

from rest_framework import serializers

from apps.vendas.models import ItemVenda, PagamentoVenda, Venda


class VendaListSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.CharField(source="cliente.nome_cliente", read_only=True)
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


class ItemVendaDetalheSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source="produto.produto", read_only=True)
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
    cliente_nome = serializers.CharField(source="venda.cliente.nome_cliente", read_only=True)
    produto_nome = serializers.CharField(source="produto.produto", read_only=True)
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


class PagamentoVendaListSerializer(serializers.ModelSerializer):
    id_legado_venda = serializers.IntegerField(source="venda.id_legado", read_only=True)
    tipo_documento = serializers.CharField(source="venda.tipo_documento", read_only=True)
    data_venda = serializers.DateField(source="venda.data_venda", read_only=True)
    cliente = serializers.IntegerField(source="venda.cliente_id", read_only=True, allow_null=True)
    cliente_nome = serializers.CharField(source="venda.cliente.nome_cliente", read_only=True)
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
