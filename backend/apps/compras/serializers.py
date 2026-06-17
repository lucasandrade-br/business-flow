from __future__ import annotations

from rest_framework import serializers

from apps.compras.models import Compra, ItemCompra


class SincronizarComprasFirebirdRequestSerializer(serializers.Serializer):
    data_inicial = serializers.DateField()
    data_final = serializers.DateField()

    def validate(self, attrs: dict) -> dict:
        data_inicial = attrs["data_inicial"]
        data_final = attrs["data_final"]
        if data_inicial > data_final:
            raise serializers.ValidationError(
                {"data_inicial": "data_inicial nao pode ser maior que data_final."}
            )
        return attrs


class TratarDivergenciaCompraRequestSerializer(serializers.Serializer):
    id_compra_legado = serializers.IntegerField()
    acao = serializers.ChoiceField(choices=["ajustar"])
    payload = serializers.JSONField(required=False, default=dict)


class TratarDivergenciasCompraLoteRequestSerializer(serializers.Serializer):
    acao = serializers.ChoiceField(choices=["validar", "negligenciar"])
    compras = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )


class CompraListSerializer(serializers.ModelSerializer):
    fornecedor_nome = serializers.SerializerMethodField()

    class Meta:
        model = Compra
        fields = [
            "id_compra",
            "id_legado",
            "nota",
            "fornecedor",
            "fornecedor_nome",
            "data_emissao",
            "data_lanc",
            "valor_produtos",
            "valor_total_documento",
            "nfe_status",
            "momento_consolidacao",
        ]

    def get_fornecedor_nome(self, obj: Compra) -> str:
        if obj.fornecedor is None:
            return ""
        return obj.fornecedor.nome_gerencial or obj.fornecedor.nome_fornecedor


class ItemCompraDetalheSerializer(serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField()
    unidade_sigla = serializers.CharField(source="unidade_medida.sigla", read_only=True)

    class Meta:
        model = ItemCompra
        fields = [
            "id_item_compra",
            "produto",
            "produto_nome",
            "unidade_medida",
            "unidade_sigla",
            "quantidade",
            "valor_custo",
            "valor_total_item",
            "descricao_origem",
            "descricao_compra_origem",
        ]

    def get_produto_nome(self, obj: ItemCompra) -> str:
        if obj.produto is None:
            return ""
        return obj.produto.nome_gerencial or obj.produto.produto


class CompraDetailSerializer(CompraListSerializer):
    itens = ItemCompraDetalheSerializer(many=True, read_only=True)

    class Meta(CompraListSerializer.Meta):
        fields = [
            *CompraListSerializer.Meta.fields,
            "itens",
        ]


class ItemCompraListSerializer(serializers.ModelSerializer):
    id_legado_compra = serializers.IntegerField(source="compra.id_legado", read_only=True)
    nota_compra = serializers.IntegerField(source="compra.nota", read_only=True, allow_null=True)
    data_emissao = serializers.DateField(source="compra.data_emissao", read_only=True)
    fornecedor = serializers.IntegerField(source="compra.fornecedor_id", read_only=True)
    fornecedor_nome = serializers.SerializerMethodField()
    nfe_status = serializers.CharField(source="compra.nfe_status", read_only=True)
    produto_nome = serializers.SerializerMethodField()
    unidade_sigla = serializers.CharField(source="unidade_medida.sigla", read_only=True)

    class Meta:
        model = ItemCompra
        fields = [
            "id_item_compra",
            "compra",
            "id_legado_compra",
            "nota_compra",
            "data_emissao",
            "fornecedor",
            "fornecedor_nome",
            "nfe_status",
            "produto",
            "produto_nome",
            "unidade_medida",
            "unidade_sigla",
            "quantidade",
            "valor_custo",
            "valor_total_item",
            "descricao_origem",
            "descricao_compra_origem",
        ]

    def get_produto_nome(self, obj: ItemCompra) -> str:
        if obj.produto is None:
            return ""
        return obj.produto.nome_gerencial or obj.produto.produto

    def get_fornecedor_nome(self, obj: ItemCompra) -> str:
        if obj.compra is None or obj.compra.fornecedor is None:
            return ""
        return obj.compra.fornecedor.nome_gerencial or obj.compra.fornecedor.nome_fornecedor
