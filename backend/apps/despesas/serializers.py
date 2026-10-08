from rest_framework import serializers

from .models import CategoriaDespesa, TipoDespesa, MovimentoDespesa, PagamentoDespesa
from .services import chave


class CategoriaSerializer(serializers.ModelSerializer):
    tipos_vinculados_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CategoriaDespesa
        fields = ["id", "nome", "caminho", "nivel", "pai", "codigo_origem", "tipos_vinculados_count"]
        read_only_fields = ["caminho", "nivel", "codigo_origem"]

    def validate(self, attrs):
        nome = str(attrs.get("nome", self.instance.nome if self.instance else "") or "").strip()
        if not nome or "\x1f" in nome:
            raise serializers.ValidationError({"nome": "Nome obrigatório e sem separador reservado."})
        pai = attrs.get("pai", self.instance.pai if self.instance else None)
        caminho = (pai.caminho + "\x1f" if pai else "") + nome
        if len(caminho) > 255:
            raise serializers.ValidationError({"nome": "O caminho completo excede 255 caracteres."})
        if CategoriaDespesa.objects.filter(caminho=caminho).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError({"nome": "Esta categoria já existe no mesmo caminho."})
        attrs["nome"] = nome
        attrs["caminho"] = caminho
        attrs["nivel"] = pai.nivel + 1 if pai else 0
        return attrs


class TipoSerializer(serializers.ModelSerializer):
    vinculos = serializers.SerializerMethodField()

    class Meta:
        model = TipoDespesa
        fields = ["id", "nome", "ativo", "codigo_origem", "vinculos"]
        read_only_fields = ["codigo_origem", "vinculos"]

    def get_vinculos(self, obj):
        return [{"familia_id": v.familia_id, "folha_id": v.folha_id, "folha": v.folha.nome} for v in obj.vinculos.all()]

    def validate_nome(self, valor):
        nome = str(valor or "").strip()
        if not nome:
            raise serializers.ValidationError("Nome obrigatório.")
        if TipoDespesa.objects.filter(chave=chave(nome)).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError("Já existe um tipo com este nome.")
        return nome

    def create(self, validated_data):
        validated_data["chave"] = chave(validated_data["nome"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "nome" in validated_data:
            validated_data["chave"] = chave(validated_data["nome"])
        return super().update(instance, validated_data)


class MovimentoSerializer(serializers.ModelSerializer):
    tipo_nome = serializers.CharField(source="tipo.nome", read_only=True)
    pagamentos = serializers.SerializerMethodField()
    saldo = serializers.SerializerMethodField()

    class Meta:
        model = MovimentoDespesa
        fields = ["id", "id_origem", "origem", "tipo", "tipo_nome", "fornecedor", "fornecedor_texto", "documento", "observacoes", "emissao", "vencimento", "valor", "pagamentos", "saldo", "criado_em", "atualizado_em"]
        read_only_fields = ["id_origem", "origem", "pagamentos", "saldo", "criado_em", "atualizado_em"]

    def get_pagamentos(self, obj):
        return PagamentoSerializer(obj.pagamentos.all(), many=True).data

    def get_saldo(self, obj):
        return str(obj.valor - sum((p.valor for p in obj.pagamentos.all()), 0))

    def validate_valor(self, valor):
        if valor < 0:
            raise serializers.ValidationError("O valor não pode ser negativo.")
        if self.instance and valor < sum((p.valor for p in self.instance.pagamentos.all()), 0):
            raise serializers.ValidationError("O valor não pode ser menor que os pagamentos existentes.")
        return valor


class PagamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagamentoDespesa
        fields = ["id", "movimento", "id_origem", "data", "valor", "forma", "origem", "criado_em"]
        read_only_fields = ["id_origem", "origem", "criado_em"]

    def validate_valor(self, valor):
        if valor <= 0:
            raise serializers.ValidationError("O valor deve ser positivo.")
        return valor

    def validate(self, attrs):
        movimento = attrs.get("movimento") or (self.instance.movimento if self.instance else None)
        if not movimento:
            return attrs
        if self.instance and movimento.pk != self.instance.movimento_id:
            raise serializers.ValidationError({"movimento": "Não é permitido mover um pagamento para outro lançamento."})
        outros = movimento.pagamentos.exclude(pk=self.instance.pk if self.instance else None)
        total = sum((p.valor for p in outros), 0) + attrs.get("valor", self.instance.valor if self.instance else 0)
        if total > movimento.valor:
            raise serializers.ValidationError({"valor": "A soma dos pagamentos excede o valor da movimentação."})
        return attrs
