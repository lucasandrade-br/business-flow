from __future__ import annotations

from datetime import datetime

from rest_framework import filters, generics
from rest_framework.exceptions import ValidationError

from apps.vendas.models import ItemVenda, PagamentoVenda, Venda
from apps.vendas.serializers import (
	ItemVendaListSerializer,
	PagamentoVendaListSerializer,
	VendaDetailSerializer,
	VendaListSerializer,
)


class _FiltroDataMixin:
	def _parse_date_param(self, key: str):
		value = str(self.request.query_params.get(key) or "").strip()
		if not value:
			return None
		try:
			return datetime.strptime(value, "%Y-%m-%d").date()
		except ValueError as exc:
			raise ValidationError({key: "Formato invalido. Use YYYY-MM-DD."}) from exc

	def _validate_date_range(self, field_name: str):
		data_inicial = self._parse_date_param("data_inicial")
		data_final = self._parse_date_param("data_final")
		if data_inicial and data_final and data_inicial > data_final:
			raise ValidationError({"data_inicial": "data_inicial nao pode ser maior que data_final."})
		filters_map = {}
		if data_inicial:
			filters_map[f"{field_name}__gte"] = data_inicial
		if data_final:
			filters_map[f"{field_name}__lte"] = data_final
		return filters_map

	def _get_int_param(self, key: str):
		value = self.request.query_params.get(key)
		if value in (None, ""):
			return None
		try:
			return int(value)
		except (TypeError, ValueError) as exc:
			raise ValidationError({key: "Valor numerico invalido."}) from exc


class VendaListAPIView(_FiltroDataMixin, generics.ListAPIView):
	serializer_class = VendaListSerializer
	filter_backends = [filters.SearchFilter]
	search_fields = ["id_legado", "tipo_documento", "status", "cliente__nome_cliente", "usuario__nome"]

	def get_queryset(self):
		queryset = Venda.objects.select_related("cliente", "usuario").all().order_by("-data_venda", "-id_venda")

		date_filters = self._validate_date_range("data_venda")
		if date_filters:
			queryset = queryset.filter(**date_filters)

		tipo_documento = str(self.request.query_params.get("tipo_documento") or "").strip().upper()
		if tipo_documento:
			queryset = queryset.filter(tipo_documento=tipo_documento)

		cliente_id = self._get_int_param("cliente_id")
		if cliente_id is not None:
			queryset = queryset.filter(cliente_id=cliente_id)

		produto_id = self._get_int_param("produto_id")
		if produto_id is not None:
			queryset = queryset.filter(itens__produto_id=produto_id)

		forma_pagamento_id = self._get_int_param("forma_pagamento_id")
		if forma_pagamento_id is not None:
			queryset = queryset.filter(pagamentos__forma_pagamento_id=forma_pagamento_id)

		if produto_id is not None or forma_pagamento_id is not None:
			queryset = queryset.distinct()

		return queryset


class VendaDetailAPIView(generics.RetrieveAPIView):
	queryset = Venda.objects.select_related("cliente", "usuario").prefetch_related(
		"itens__produto",
		"itens__unidade_medida",
		"pagamentos__forma_pagamento",
	)
	serializer_class = VendaDetailSerializer
	lookup_field = "id_venda"


class ItemVendaListAPIView(_FiltroDataMixin, generics.ListAPIView):
	serializer_class = ItemVendaListSerializer
	filter_backends = [filters.SearchFilter]
	search_fields = ["venda__id_legado", "produto__produto", "venda__cliente__nome_cliente", "venda__tipo_documento"]

	def get_queryset(self):
		queryset = ItemVenda.objects.select_related(
			"venda",
			"venda__cliente",
			"produto",
			"unidade_medida",
		).all().order_by("-venda__data_venda", "-id_item_venda")

		date_filters = self._validate_date_range("venda__data_venda")
		if date_filters:
			queryset = queryset.filter(**date_filters)

		tipo_documento = str(self.request.query_params.get("tipo_documento") or "").strip().upper()
		if tipo_documento:
			queryset = queryset.filter(venda__tipo_documento=tipo_documento)

		cliente_id = self._get_int_param("cliente_id")
		if cliente_id is not None:
			queryset = queryset.filter(venda__cliente_id=cliente_id)

		produto_id = self._get_int_param("produto_id")
		if produto_id is not None:
			queryset = queryset.filter(produto_id=produto_id)

		forma_pagamento_id = self._get_int_param("forma_pagamento_id")
		if forma_pagamento_id is not None:
			queryset = queryset.filter(venda__pagamentos__forma_pagamento_id=forma_pagamento_id).distinct()

		return queryset


class PagamentoVendaListAPIView(_FiltroDataMixin, generics.ListAPIView):
	serializer_class = PagamentoVendaListSerializer
	filter_backends = [filters.SearchFilter]
	search_fields = ["venda__id_legado", "forma_pagamento__descricao", "venda__cliente__nome_cliente", "venda__tipo_documento"]

	def get_queryset(self):
		queryset = PagamentoVenda.objects.select_related(
			"venda",
			"venda__cliente",
			"forma_pagamento",
		).all().order_by("-venda__data_venda", "-id_pagamento_venda")

		date_filters = self._validate_date_range("venda__data_venda")
		if date_filters:
			queryset = queryset.filter(**date_filters)

		tipo_documento = str(self.request.query_params.get("tipo_documento") or "").strip().upper()
		if tipo_documento:
			queryset = queryset.filter(venda__tipo_documento=tipo_documento)

		cliente_id = self._get_int_param("cliente_id")
		if cliente_id is not None:
			queryset = queryset.filter(venda__cliente_id=cliente_id)

		forma_pagamento_id = self._get_int_param("forma_pagamento_id")
		if forma_pagamento_id is not None:
			queryset = queryset.filter(forma_pagamento_id=forma_pagamento_id)

		produto_id = self._get_int_param("produto_id")
		if produto_id is not None:
			queryset = queryset.filter(venda__itens__produto_id=produto_id).distinct()

		return queryset
