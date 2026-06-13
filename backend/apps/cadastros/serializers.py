from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from .models import (
    Aliquota,
    Cliente,
    CodSis,
    FormaPagamento,
    FormaPagamentoMapeamento,
    FormaPagamentoOrigem,
    Fornecedor,
    GrupoCliente,
    PlanoConta,
    Produto,
    TemplateExportacao,
    TipoVenda,
    UnidadeMedida,
)


class UnidadeMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadeMedida
        fields = ["id_und_medida", "sigla", "descricao"]


class PlanoContaSerializer(serializers.ModelSerializer):
    linha_sucessoria = serializers.CharField(read_only=True)
    qtd_produtos = serializers.IntegerField(read_only=True)

    class Meta:
        model = PlanoConta
        fields = ["id_conta", "codigo_hierarquico", "nome_conta", "conta_pai", "linha_sucessoria", "qtd_produtos"]
        read_only_fields = ["codigo_hierarquico"]


class PlanoContaTreeSerializer(serializers.ModelSerializer):
    filhas = serializers.SerializerMethodField()

    class Meta:
        model = PlanoConta
        fields = ["id_conta", "codigo_hierarquico", "nome_conta", "conta_pai", "filhas"]

    def get_filhas(self, obj: PlanoConta):
        children = obj.filhas.all().order_by("codigo_hierarquico")
        return PlanoContaTreeSerializer(children, many=True).data


class ProdutoSerializer(serializers.ModelSerializer):
    categorias = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=PlanoConta.objects.all(),
        required=False,
    )

    class Meta:
        model = Produto
        fields = [
            "id_produto",
            "gtin",
            "barras",
            "produto",
            "id_und_medida",
            "custo",
            "venda",
            "status",
            "markup",
            "markup_inv",
            "perda",
            "categorias",
            "ult_mov",
            "fisico",
            "aliqefc",
            "cod_g3n",
            "cod_rel",
            "usuario",
        ]
        extra_kwargs = {
            "status": {"required": True, "allow_blank": False},
            "id_und_medida": {"required": True, "allow_null": False},
            "markup": {"required": False, "default": Decimal("0.0000")},
            "markup_inv": {"required": False, "default": Decimal("0.0000")},
            "perda": {"required": False, "default": Decimal("0.0000")},
            "fisico": {"required": False, "default": Decimal("0.0000")},
            "aliqefc": {"required": False, "allow_blank": True, "default": ""},
            "cod_g3n": {"required": False, "default": 0},
            "cod_rel": {"required": False, "default": 0},
            "usuario": {"required": False, "allow_blank": True, "default": ""},
            "gtin": {"required": False, "allow_blank": True, "default": ""},
            "barras": {"required": False, "allow_blank": True, "default": ""},
            "ult_mov": {"required": False, "allow_null": True, "default": None},
        }


class CodSisSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodSis
        fields = ["id_codsis", "nome"]


class GrupoClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrupoCliente
        fields = ["id_grupo", "descricao"]


class TipoVendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoVenda
        fields = ["id_tipo_venda", "descricao"]


class AliquotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aliquota
        fields = ["id_aliquota", "valor_percentual", "descricao"]


class FormaPagamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormaPagamento
        fields = ["id_forma", "descricao"]


class FormaPagamentoOrigemSerializer(serializers.ModelSerializer):
    TIPOS_VALIDOS = {"NFCE", "DAV", "NFE"}

    class Meta:
        model = FormaPagamentoOrigem
        fields = [
            "id_origem",
            "tipo_documento",
            "id_forma_origem",
            "descricao_origem",
            "ativo",
        ]

    def validate_tipo_documento(self, value):
        normalized = str(value or "").strip().upper()
        if normalized not in self.TIPOS_VALIDOS:
            raise serializers.ValidationError("tipo_documento invalido. Use NFCE, DAV ou NFE.")
        return normalized


class FormaPagamentoMapeamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormaPagamentoMapeamento
        fields = [
            "id_mapeamento",
            "forma_pagamento",
            "tipo_documento",
            "id_forma_origem",
            "descricao_origem",
            "ativo",
        ]


class FormaPagamentoMapeamentoLoteSerializer(serializers.Serializer):
    adicionar = serializers.ListField(child=serializers.DictField(), required=False, allow_empty=True)
    remover = serializers.ListField(child=serializers.DictField(), required=False, allow_empty=True)

    def validate(self, attrs):
        def _normalize(items):
            normalized = []
            for item in items or []:
                tipo_documento = str(item.get("tipo_documento") or "").strip().upper()
                id_forma_origem_raw = item.get("id_forma_origem")
                if not tipo_documento or id_forma_origem_raw in (None, ""):
                    continue
                try:
                    id_forma_origem = int(id_forma_origem_raw)
                except (TypeError, ValueError):
                    continue

                normalized.append(
                    {
                        "tipo_documento": tipo_documento,
                        "id_forma_origem": id_forma_origem,
                        "descricao_origem": str(item.get("descricao_origem") or "").strip(),
                    }
                )
            return normalized

        adicionar = _normalize(attrs.get("adicionar") or [])
        remover = _normalize(attrs.get("remover") or [])

        if not adicionar and not remover:
            raise serializers.ValidationError("Informe ao menos um item para adicionar ou remover.")

        attrs["adicionar"] = adicionar
        attrs["remover"] = remover
        return attrs


class FornecedorSerializer(serializers.ModelSerializer):
    id_codsis = serializers.IntegerField(required=False, allow_null=True, source="id_codsis_id")

    class Meta:
        model = Fornecedor
        fields = [
            "id_fornecedor",
            "nome_fornecedor",
            "raz_social",
            "dt_cadastro",
            "id_codsis",
            "codigo",
            "operador",
            "usuario",
        ]
        extra_kwargs = {
            "raz_social": {"required": False, "allow_blank": True},
            "dt_cadastro": {"required": False, "allow_null": True},
            "codigo": {"required": False, "allow_blank": True},
            "operador": {"required": False},
            "usuario": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data):
        id_codsis = validated_data.pop("id_codsis_id", None)
        if id_codsis is not None:
            codsis, _ = CodSis.objects.get_or_create(
                id_codsis=id_codsis,
                defaults={"nome": f"CodSis {id_codsis}"},
            )
            validated_data["id_codsis"] = codsis
        return super().create(validated_data)

    def update(self, instance, validated_data):
        id_codsis = validated_data.pop("id_codsis_id", serializers.empty)
        if id_codsis is not serializers.empty:
            if id_codsis is None:
                validated_data["id_codsis"] = None
            else:
                codsis, _ = CodSis.objects.get_or_create(
                    id_codsis=id_codsis,
                    defaults={"nome": f"CodSis {id_codsis}"},
                )
                validated_data["id_codsis"] = codsis
        return super().update(instance, validated_data)


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = [
            "id_cliente",
            "nome_cliente",
            "raz_social",
            "prazo_cob",
            "cliente_padrao",
            "id_grupo",
            "id_tipo_venda",
        ]


class TemplateExportacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateExportacao
        fields = ["id", "nome", "tabela", "tipo", "colunas_selecionadas", "query_sql"]

    def validate(self, attrs):
        tipo = attrs.get("tipo", getattr(self.instance, "tipo", None))
        colunas = attrs.get("colunas_selecionadas", getattr(self.instance, "colunas_selecionadas", None))
        query = attrs.get("query_sql", getattr(self.instance, "query_sql", None))

        if tipo == TemplateExportacao.TIPO_BASICO and not colunas:
            raise serializers.ValidationError({"colunas_selecionadas": "Obrigatorio para tipo BASICO."})
        if tipo == TemplateExportacao.TIPO_SQL and not str(query or "").strip():
            raise serializers.ValidationError({"query_sql": "Obrigatorio para tipo SQL."})
        return attrs


class ExportacaoRequestSerializer(serializers.Serializer):
    tabela = serializers.ChoiceField(
        choices=[
            "produtos",
            "clientes",
            "fornecedores",
            "vendas",
            "itens_venda",
            "pagamentos_venda",
            "compras",
            "itens_compra",
        ]
    )
    tipo = serializers.ChoiceField(choices=["BASICO", "SQL"], default="BASICO", required=False)
    colunas = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    query_sql = serializers.CharField(required=False, allow_blank=True)
    formato = serializers.ChoiceField(choices=["csv", "xlsx", "pdf"])
    search = serializers.CharField(required=False, allow_blank=True)
    filtros = serializers.JSONField(required=False)

    def validate(self, attrs):
        tipo = attrs.get("tipo", "BASICO")
        colunas = attrs.get("colunas") or []
        query_sql = str(attrs.get("query_sql") or "").strip()

        if tipo == "BASICO" and not colunas:
            raise serializers.ValidationError({"colunas": "Obrigatorio para exportacao BASICO."})
        if tipo == "SQL" and not query_sql:
            raise serializers.ValidationError({"query_sql": "Obrigatorio para exportacao SQL."})

        return attrs


class PlanoContaLoteSerializer(serializers.Serializer):
    conta_pai_id = serializers.IntegerField(required=False, allow_null=True)
    filhas = serializers.ListField(child=serializers.CharField(), allow_empty=False)

    def validate_filhas(self, value):
        cleaned = [str(item or "").strip() for item in value]
        cleaned = [item for item in cleaned if item]
        if not cleaned:
            raise serializers.ValidationError("Informe ao menos uma conta filha valida.")
        return cleaned


class PlanoContaVincularProdutosSerializer(serializers.Serializer):
    adicionar_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)
    remover_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)

    def validate(self, attrs):
        adicionar_ids = list(dict.fromkeys(int(item) for item in (attrs.get("adicionar_ids") or [])))
        remover_ids = list(dict.fromkeys(int(item) for item in (attrs.get("remover_ids") or [])))

        if not adicionar_ids and not remover_ids:
            raise serializers.ValidationError("Informe ao menos um produto para adicionar ou remover.")

        overlap = set(adicionar_ids) & set(remover_ids)
        if overlap:
            remover_ids = [item for item in remover_ids if item not in overlap]

        attrs["adicionar_ids"] = adicionar_ids
        attrs["remover_ids"] = remover_ids
        return attrs
