from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers


class ProdutoPendenteSerializer(serializers.Serializer):
    id_produto = serializers.IntegerField()
    nome = serializers.CharField()
    gtin = serializers.CharField(required=False, allow_blank=True)
    barras = serializers.CharField(required=False, allow_blank=True)
    unidade_comercial = serializers.CharField(source="unidade_comecial", required=False, allow_blank=True)
    custo = serializers.DecimalField(max_digits=18, decimal_places=6)
    valor_venda = serializers.DecimalField(max_digits=18, decimal_places=6)
    dt_ultimo_movimento = serializers.DateField(required=False, allow_null=True)
    status = serializers.CharField(required=False, allow_blank=True)
    unidade_sugerida_id = serializers.IntegerField(required=False, allow_null=True)
    tipo_pendencia = serializers.ChoiceField(choices=["NOVO", "ATUALIZACAO"], required=False)
    dados_sot = serializers.JSONField(required=False, allow_null=True)


class AprovarProdutoSerializer(serializers.Serializer):
    id_produto = serializers.IntegerField()
    nome = serializers.CharField(max_length=120)
    gtin = serializers.CharField(max_length=32, required=False, allow_blank=True)
    barras = serializers.CharField(max_length=64, required=False, allow_blank=True)
    status = serializers.CharField(max_length=30, required=True, allow_blank=False)
    ult_mov = serializers.DateField(required=False, allow_null=True)
    custo = serializers.DecimalField(max_digits=18, decimal_places=6)
    valor_venda = serializers.DecimalField(max_digits=18, decimal_places=6)

    id_und_medida = serializers.IntegerField()

    markup = serializers.DecimalField(max_digits=10, decimal_places=4, required=False, default=Decimal("0.0000"))
    markup_inv = serializers.DecimalField(max_digits=10, decimal_places=4, required=False, default=Decimal("0.0000"))
    perda = serializers.DecimalField(max_digits=10, decimal_places=4, required=False, default=Decimal("0.0000"))

    categorias_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
    )

    fisico = serializers.DecimalField(max_digits=10, decimal_places=4, required=False, default=Decimal("0.0000"))
    aliqefc = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    cod_g3n = serializers.IntegerField(required=False, default=0)
    cod_rel = serializers.IntegerField(required=False, default=0)

    usuario = serializers.CharField(max_length=100, required=False, allow_blank=True)

    codigo = serializers.CharField(max_length=5, required=False, allow_blank=True)

    def validate_codigo(self, value: str) -> str:
        if value == "":
            return value

        if not value.isdigit():
            raise serializers.ValidationError("codigo deve conter apenas numeros.")

        padded = value.zfill(5)
        if len(padded) != 5:
            raise serializers.ValidationError("codigo deve ter exatamente 5 caracteres.")

        return padded


class ClientePendenteSerializer(serializers.Serializer):
    id_cliente = serializers.IntegerField()
    nome_cliente = serializers.CharField()
    raz_social = serializers.CharField(required=False, allow_blank=True)
    tipo_pendencia = serializers.ChoiceField(choices=["NOVO", "ATUALIZACAO"], required=False)
    dados_sot = serializers.JSONField(required=False, allow_null=True)


class AprovarClienteSerializer(serializers.Serializer):
    id_cliente = serializers.IntegerField()
    nome_cliente = serializers.CharField(max_length=120)
    raz_social = serializers.CharField(max_length=160, required=False, allow_blank=True)
    prazo_cob = serializers.IntegerField(min_value=0, required=False, default=0)
    id_grupo = serializers.IntegerField(required=False, allow_null=True)
    id_tipo_venda = serializers.IntegerField(required=False, allow_null=True)


class FornecedorPendenteSerializer(serializers.Serializer):
    id_fornecedor = serializers.IntegerField()
    nome_fornecedor = serializers.CharField()
    raz_social = serializers.CharField(required=False, allow_blank=True)
    dt_cadastro = serializers.DateField(required=False, allow_null=True)
    tipo_pendencia = serializers.ChoiceField(choices=["NOVO", "ATUALIZACAO"], required=False)
    dados_sot = serializers.JSONField(required=False, allow_null=True)


class AprovarFornecedorSerializer(serializers.Serializer):
    id_fornecedor = serializers.IntegerField()
    nome_fornecedor = serializers.CharField(max_length=120)
    raz_social = serializers.CharField(max_length=160, required=False, allow_blank=True)
    dt_cadastro = serializers.DateField(required=False, allow_null=True)
    id_codsis = serializers.IntegerField(required=False, allow_null=True)
    codigo = serializers.CharField(max_length=5, required=False, allow_blank=True)
    operador = serializers.IntegerField(required=False, default=0)
    usuario = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_codigo(self, value: str) -> str:
        if value == "":
            return value

        if not value.isdigit():
            raise serializers.ValidationError("codigo deve conter apenas numeros.")

        return value.zfill(5)
