from __future__ import annotations

import pandas as pd
from django.db import connection, transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from rest_framework import status
from rest_framework import filters, generics, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aliquota, Cliente, FormaPagamento, FormaPagamentoMapeamento, FormaPagamentoOrigem, Fornecedor, GrupoCliente, PlanoConta, Produto, TemplateExportacao, TipoVenda, UnidadeMedida
from apps.compras.models import Compra, ItemCompra
from apps.vendas.models import ItemVenda, PagamentoVenda, Venda
from .serializers import (
	AliquotaSerializer,
	ClienteSerializer,
	ExportacaoRequestSerializer,
	FormaPagamentoSerializer,
	FormaPagamentoOrigemSerializer,
	FormaPagamentoMapeamentoLoteSerializer,
	FormaPagamentoMapeamentoSerializer,
	GrupoClienteSerializer,
	PlanoContaLoteSerializer,
	PlanoContaSerializer,
	PlanoContaVincularProdutosSerializer,
	PlanoContaTreeSerializer,
	FornecedorSerializer,
	ProdutoSerializer,
	TemplateExportacaoSerializer,
	TipoVendaSerializer,
	UnidadeMedidaSerializer,
)
from .services import EXPORT_CONTENT_TYPES, export_dataframe, export_queryset_data, validate_safe_select_sql


class UnidadeMedidaListCreateAPIView(generics.ListCreateAPIView):
	queryset = UnidadeMedida.objects.all().order_by("id_und_medida")
	serializer_class = UnidadeMedidaSerializer
	filter_backends = [filters.SearchFilter]
	search_fields = ["sigla", "descricao"]


class UnidadeMedidaDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
	queryset = UnidadeMedida.objects.all()
	serializer_class = UnidadeMedidaSerializer
	lookup_field = "id_und_medida"


class PlanoContaListCreateAPIView(generics.ListCreateAPIView):
	queryset = PlanoConta.objects.select_related("conta_pai").all().order_by("codigo_hierarquico")
	serializer_class = PlanoContaSerializer
	filter_backends = [filters.SearchFilter]
	search_fields = ["nome_conta", "codigo_hierarquico"]

	def get_queryset(self):
		queryset = super().get_queryset().annotate(qtd_produtos=Count("produtos_vinculados", distinct=True))
		raiz_id_raw = self.request.query_params.get("raiz_id")
		if not raiz_id_raw:
			return queryset

		try:
			raiz_id = int(raiz_id_raw)
		except (TypeError, ValueError):
			return queryset.none()

		raiz = queryset.filter(id_conta=raiz_id, conta_pai__isnull=True).first()
		if raiz is None:
			return queryset.none()

		ids = {raiz.id_conta}
		fronteira = [raiz.id_conta]
		while fronteira:
			filhas = list(
				PlanoConta.objects.filter(conta_pai_id__in=fronteira).values_list("id_conta", flat=True)
			)
			novas = [item_id for item_id in filhas if item_id not in ids]
			if not novas:
				break
			ids.update(novas)
			fronteira = novas

		return queryset.filter(id_conta__in=ids)


class PlanoContaViewSet(viewsets.ModelViewSet):
	queryset = PlanoConta.objects.select_related("conta_pai").all().order_by("codigo_hierarquico")
	serializer_class = PlanoContaSerializer
	lookup_field = "id_conta"
	filter_backends = [filters.SearchFilter]
	search_fields = ["nome_conta", "codigo_hierarquico"]

	def get_queryset(self):
		return (
			super()
			.get_queryset()
			.annotate(qtd_produtos=Count("produtos_vinculados", distinct=True))
		)

	@action(detail=False, methods=["post"], url_path="lote")
	def lote(self, request):
		payload = PlanoContaLoteSerializer(data=request.data)
		payload.is_valid(raise_exception=True)
		validated = payload.validated_data

		conta_pai_id = validated.get("conta_pai_id")
		nomes_filhas = validated["filhas"]

		conta_pai = None
		if conta_pai_id is not None:
			conta_pai = PlanoConta.objects.filter(id_conta=conta_pai_id).first()
			if conta_pai is None:
				return Response({"detail": "Conta pai nao encontrada."}, status=status.HTTP_400_BAD_REQUEST)

		criadas = []
		for nome_conta in nomes_filhas:
			conta = PlanoConta(nome_conta=nome_conta, conta_pai=conta_pai)
			# Save sequencial e obrigatorio para manter o calculo hierarquico no model.
			conta.save()
			criadas.append(conta)

		serialized = self.get_serializer(criadas, many=True)
		return Response(serialized.data, status=status.HTTP_201_CREATED)

	@action(detail=True, methods=["post"], url_path="vincular-produtos")
	def vincular_produtos(self, request, id_conta=None):
		categoria = self.get_object()
		payload = PlanoContaVincularProdutosSerializer(data=request.data)
		payload.is_valid(raise_exception=True)
		adicionar_ids = payload.validated_data.get("adicionar_ids", [])
		remover_ids = payload.validated_data.get("remover_ids", [])

		ids_existentes = set(
			Produto.objects.filter(id_produto__in=[*adicionar_ids, *remover_ids]).values_list("id_produto", flat=True)
		)
		adicionar_ids = [item for item in adicionar_ids if item in ids_existentes]
		remover_ids = [item for item in remover_ids if item in ids_existentes]

		if adicionar_ids:
			categoria.produtos_vinculados.add(*adicionar_ids)
		if remover_ids:
			categoria.produtos_vinculados.remove(*remover_ids)

		return Response(
			{
				"detail": "Vinculos aplicados com sucesso.",
				"categoria_id": categoria.id_conta,
				"adicionados": len(adicionar_ids),
				"removidos": len(remover_ids),
			},
			status=status.HTTP_200_OK,
		)


class PlanoContaDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
	queryset = PlanoConta.objects.select_related("conta_pai").all()
	serializer_class = PlanoContaSerializer
	lookup_field = "id_conta"


class PlanoContaArvoreAPIView(generics.ListAPIView):
	queryset = (
		PlanoConta.objects.select_related("conta_pai")
		.prefetch_related("filhas")
		.filter(conta_pai__isnull=True)
		.order_by("codigo_hierarquico")
	)
	serializer_class = PlanoContaTreeSerializer
	pagination_class = None


class ProdutoListCreateAPIView(generics.ListCreateAPIView):
	queryset = Produto.objects.select_related("id_und_medida").prefetch_related("categorias").all().order_by("id_produto")
	serializer_class = ProdutoSerializer
	filter_backends = [filters.SearchFilter]
	search_fields = ["produto", "nome_gerencial", "id_produto"]

	def get_queryset(self):
		queryset = super().get_queryset()
		categoria_id = (self.request.query_params.get("categoria_id") or "").strip()
		if categoria_id:
			try:
				categoria_id_int = int(categoria_id)
			except (TypeError, ValueError):
				return queryset.none()
			queryset = queryset.filter(categorias__id_conta=categoria_id_int)
		return queryset.distinct()


class ProdutoDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
	queryset = Produto.objects.select_related("id_und_medida").prefetch_related("categorias").all()
	serializer_class = ProdutoSerializer
	lookup_field = "id_produto"


class FornecedorListCreateAPIView(generics.ListCreateAPIView):
	queryset = Fornecedor.objects.select_related("id_codsis").all().order_by("id_fornecedor")
	serializer_class = FornecedorSerializer
	filter_backends = [filters.SearchFilter]
	search_fields = ["nome_fornecedor", "nome_gerencial", "raz_social", "codigo"]


class FornecedorDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
	queryset = Fornecedor.objects.select_related("id_codsis").all()
	serializer_class = FornecedorSerializer
	lookup_field = "id_fornecedor"


class ClienteListCreateAPIView(generics.ListCreateAPIView):
	queryset = Cliente.objects.select_related("id_grupo", "id_tipo_venda").all().order_by("id_cliente")
	serializer_class = ClienteSerializer
	filter_backends = [filters.SearchFilter]
	search_fields = ["nome_cliente", "nome_gerencial", "raz_social"]


class ClienteDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
	queryset = Cliente.objects.select_related("id_grupo", "id_tipo_venda").all()
	serializer_class = ClienteSerializer
	lookup_field = "id_cliente"


class GrupoClienteListCreateAPIView(generics.ListCreateAPIView):
	queryset = GrupoCliente.objects.all().order_by("id_grupo")
	serializer_class = GrupoClienteSerializer
	filter_backends = [filters.SearchFilter]
	search_fields = ["descricao"]


class GrupoClienteDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
	queryset = GrupoCliente.objects.all()
	serializer_class = GrupoClienteSerializer
	lookup_field = "id_grupo"


class TipoVendaListCreateAPIView(generics.ListCreateAPIView):
	queryset = TipoVenda.objects.all().order_by("id_tipo_venda")
	serializer_class = TipoVendaSerializer
	filter_backends = [filters.SearchFilter]
	search_fields = ["descricao"]


class TipoVendaDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
	queryset = TipoVenda.objects.all()
	serializer_class = TipoVendaSerializer
	lookup_field = "id_tipo_venda"


class AliquotaListCreateAPIView(generics.ListCreateAPIView):
	queryset = Aliquota.objects.all().order_by("id_aliquota")
	serializer_class = AliquotaSerializer
	filter_backends = [filters.SearchFilter]
	search_fields = ["descricao"]


class AliquotaDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
	queryset = Aliquota.objects.all()
	serializer_class = AliquotaSerializer
	lookup_field = "id_aliquota"


class FormaPagamentoListCreateAPIView(generics.ListCreateAPIView):
	queryset = FormaPagamento.objects.all().order_by("id_forma")
	serializer_class = FormaPagamentoSerializer
	filter_backends = [filters.SearchFilter]
	search_fields = ["descricao", "id_forma"]


class FormaPagamentoDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
	queryset = FormaPagamento.objects.all()
	serializer_class = FormaPagamentoSerializer
	lookup_field = "id_forma"


class FormaPagamentoOrigemListCreateAPIView(generics.ListCreateAPIView):
	queryset = FormaPagamentoOrigem.objects.all().order_by("tipo_documento", "id_forma_origem")
	serializer_class = FormaPagamentoOrigemSerializer
	filter_backends = [filters.SearchFilter]
	search_fields = ["tipo_documento", "id_forma_origem", "descricao_origem"]


class FormaPagamentoOrigemDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
	queryset = FormaPagamentoOrigem.objects.all()
	serializer_class = FormaPagamentoOrigemSerializer
	lookup_field = "id_origem"


class FormaPagamentoMapeamentoOpcoesAPIView(APIView):
	def get(self, request):
		forma_id_raw = request.query_params.get("forma_id")
		search = (request.query_params.get("search") or "").strip().upper()
		somente_vinculados = str(request.query_params.get("somente_vinculados") or "").strip().lower() in {"1", "true", "on", "sim", "yes"}

		forma_id = None
		if forma_id_raw not in (None, ""):
			try:
				forma_id = int(forma_id_raw)
			except (TypeError, ValueError):
				return Response({"detail": "forma_id invalido."}, status=status.HTTP_400_BAD_REQUEST)

		mapeamentos_qs = FormaPagamentoMapeamento.objects.all()
		mapeamento_por_chave = {
			(f"{item.tipo_documento}:{int(item.id_forma_origem)}"): item
			for item in mapeamentos_qs
		}

		origens = set()
		for item in FormaPagamentoOrigem.objects.filter(ativo=True).values("tipo_documento", "id_forma_origem", "descricao_origem"):
			origens.add(
				(
					str(item["tipo_documento"] or "").strip().upper(),
					int(item["id_forma_origem"]),
					str(item.get("descricao_origem") or "").strip(),
				)
			)

		for item in mapeamentos_qs.values("tipo_documento", "id_forma_origem", "descricao_origem"):
			origens.add(
				(
					str(item["tipo_documento"] or "").strip().upper(),
					int(item["id_forma_origem"]),
					str(item.get("descricao_origem") or "").strip(),
				)
			)

		rows = []
		for tipo_documento, id_origem, descricao_origem in sorted(origens, key=lambda x: (x[0], x[1])):
			chave = f"{tipo_documento}:{id_origem}"
			mapeamento = mapeamento_por_chave.get(chave)
			is_vinculado = bool(mapeamento and (forma_id is not None and int(mapeamento.forma_pagamento_id) == int(forma_id)))

			if somente_vinculados and not is_vinculado:
				continue

			search_blob = f"{tipo_documento} {id_origem} {descricao_origem}".upper()
			if search and search not in search_blob:
				continue

			rows.append(
				{
					"tipo_documento": tipo_documento,
					"id_forma_origem": id_origem,
					"descricao_origem": descricao_origem,
					"forma_pagamento_id": int(mapeamento.forma_pagamento_id) if mapeamento else None,
					"vinculado": is_vinculado,
				}
			)

		return Response({"rows": rows}, status=status.HTTP_200_OK)


class FormaPagamentoMapeamentoLoteAPIView(APIView):
	def post(self, request, id_forma: int):
		forma = FormaPagamento.objects.filter(id_forma=id_forma).first()
		if forma is None:
			return Response({"detail": "Forma de pagamento nao encontrada."}, status=status.HTTP_404_NOT_FOUND)

		serializer = FormaPagamentoMapeamentoLoteSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		adicionar = serializer.validated_data.get("adicionar", [])
		remover = serializer.validated_data.get("remover", [])

		adicionados = 0
		removidos = 0
		with transaction.atomic():
			for item in adicionar:
				origem_defaults = {
					"descricao_origem": item.get("descricao_origem") or f"Forma {item['id_forma_origem']}",
					"ativo": True,
				}
				FormaPagamentoOrigem.objects.update_or_create(
					tipo_documento=item["tipo_documento"],
					id_forma_origem=item["id_forma_origem"],
					defaults=origem_defaults,
				)

				obj, created = FormaPagamentoMapeamento.objects.update_or_create(
					tipo_documento=item["tipo_documento"],
					id_forma_origem=item["id_forma_origem"],
					defaults={
						"forma_pagamento": forma,
						"descricao_origem": item.get("descricao_origem") or "",
						"ativo": True,
					},
				)
				if created or obj.forma_pagamento_id == forma.id_forma:
					adicionados += 1

			for item in remover:
				deleted, _ = FormaPagamentoMapeamento.objects.filter(
					forma_pagamento=forma,
					tipo_documento=item["tipo_documento"],
					id_forma_origem=item["id_forma_origem"],
				).delete()
				if deleted:
					removidos += 1

		return Response(
			{
				"detail": "Mapeamentos aplicados com sucesso.",
				"id_forma": int(forma.id_forma),
				"adicionados": adicionados,
				"removidos": removidos,
			},
			status=status.HTTP_200_OK,
		)


class FormaPagamentoMapeamentoListAPIView(generics.ListAPIView):
	queryset = FormaPagamentoMapeamento.objects.select_related("forma_pagamento").order_by("tipo_documento", "id_forma_origem")
	serializer_class = FormaPagamentoMapeamentoSerializer


class TemplateExportacaoViewSet(viewsets.ModelViewSet):
	queryset = TemplateExportacao.objects.all().order_by("nome")
	serializer_class = TemplateExportacaoSerializer

	def get_queryset(self):
		queryset = super().get_queryset()
		tabela = (self.request.query_params.get("tabela") or "").strip()
		if tabela:
			queryset = queryset.filter(tabela=tabela)
		return queryset


class ExportacaoUniversalAPIView(APIView):
	@staticmethod
	def _to_int_or_none(value):
		if value in (None, ""):
			return None
		try:
			return int(value)
		except (TypeError, ValueError):
			return None

	@staticmethod
	def _apply_date_range_filter(queryset, *, field_name: str, filtros: dict):
		data_inicial = str(filtros.get("data_inicial") or "").strip()
		data_final = str(filtros.get("data_final") or "").strip()
		if data_inicial:
			queryset = queryset.filter(**{f"{field_name}__gte": data_inicial})
		if data_final:
			queryset = queryset.filter(**{f"{field_name}__lte": data_final})
		return queryset

	def _apply_venda_filters(self, queryset, filtros: dict):
		queryset = self._apply_date_range_filter(queryset, field_name="data_venda", filtros=filtros)
		tipo_documento = str(filtros.get("tipo_documento") or "").strip().upper()
		if tipo_documento:
			queryset = queryset.filter(tipo_documento=tipo_documento)

		cliente_id = self._to_int_or_none(filtros.get("cliente_id"))
		if cliente_id is not None:
			queryset = queryset.filter(cliente_id=cliente_id)

		produto_id = self._to_int_or_none(filtros.get("produto_id"))
		if produto_id is not None:
			queryset = queryset.filter(itens__produto_id=produto_id)

		forma_pagamento_id = self._to_int_or_none(filtros.get("forma_pagamento_id"))
		if forma_pagamento_id is not None:
			queryset = queryset.filter(pagamentos__forma_pagamento_id=forma_pagamento_id)

		if produto_id is not None or forma_pagamento_id is not None:
			queryset = queryset.distinct()
		return queryset

	def _apply_item_filters(self, queryset, filtros: dict):
		queryset = self._apply_date_range_filter(queryset, field_name="venda__data_venda", filtros=filtros)
		tipo_documento = str(filtros.get("tipo_documento") or "").strip().upper()
		if tipo_documento:
			queryset = queryset.filter(venda__tipo_documento=tipo_documento)

		cliente_id = self._to_int_or_none(filtros.get("cliente_id"))
		if cliente_id is not None:
			queryset = queryset.filter(venda__cliente_id=cliente_id)

		produto_id = self._to_int_or_none(filtros.get("produto_id"))
		if produto_id is not None:
			queryset = queryset.filter(produto_id=produto_id)

		forma_pagamento_id = self._to_int_or_none(filtros.get("forma_pagamento_id"))
		if forma_pagamento_id is not None:
			queryset = queryset.filter(venda__pagamentos__forma_pagamento_id=forma_pagamento_id).distinct()
		return queryset

	def _apply_pagamento_filters(self, queryset, filtros: dict):
		queryset = self._apply_date_range_filter(queryset, field_name="venda__data_venda", filtros=filtros)
		tipo_documento = str(filtros.get("tipo_documento") or "").strip().upper()
		if tipo_documento:
			queryset = queryset.filter(venda__tipo_documento=tipo_documento)

		cliente_id = self._to_int_or_none(filtros.get("cliente_id"))
		if cliente_id is not None:
			queryset = queryset.filter(venda__cliente_id=cliente_id)

		forma_pagamento_id = self._to_int_or_none(filtros.get("forma_pagamento_id"))
		if forma_pagamento_id is not None:
			queryset = queryset.filter(forma_pagamento_id=forma_pagamento_id)

		produto_id = self._to_int_or_none(filtros.get("produto_id"))
		if produto_id is not None:
			queryset = queryset.filter(venda__itens__produto_id=produto_id).distinct()
		return queryset

	def _apply_compra_filters(self, queryset, filtros: dict):
		queryset = self._apply_date_range_filter(queryset, field_name="data_emissao", filtros=filtros)

		fornecedor_id = self._to_int_or_none(filtros.get("fornecedor_id"))
		if fornecedor_id is not None:
			queryset = queryset.filter(fornecedor_id=fornecedor_id)

		produto_id = self._to_int_or_none(filtros.get("produto_id"))
		if produto_id is not None:
			queryset = queryset.filter(itens__produto_id=produto_id).distinct()

		nfe_status = str(filtros.get("nfe_status") or "").strip().upper()
		if nfe_status:
			queryset = queryset.filter(nfe_status=nfe_status)

		return queryset

	def _apply_item_compra_filters(self, queryset, filtros: dict):
		queryset = self._apply_date_range_filter(queryset, field_name="compra__data_emissao", filtros=filtros)

		fornecedor_id = self._to_int_or_none(filtros.get("fornecedor_id"))
		if fornecedor_id is not None:
			queryset = queryset.filter(compra__fornecedor_id=fornecedor_id)

		produto_id = self._to_int_or_none(filtros.get("produto_id"))
		if produto_id is not None:
			queryset = queryset.filter(produto_id=produto_id)

		nfe_status = str(filtros.get("nfe_status") or "").strip().upper()
		if nfe_status:
			queryset = queryset.filter(compra__nfe_status=nfe_status)

		return queryset

	TABLE_CONFIG = {
		"produtos": {
			"queryset": Produto.objects.select_related("id_und_medida").prefetch_related("categorias").all(),
			"search_fields": ["produto", "nome_gerencial"],
			"allowed_columns": {field.name for field in Produto._meta.fields},
			"filter_fn": lambda self, queryset, filtros: queryset,
		},
		"clientes": {
			"queryset": Cliente.objects.select_related("id_grupo", "id_tipo_venda").all(),
			"search_fields": ["nome_cliente", "nome_gerencial", "raz_social"],
			"allowed_columns": {field.name for field in Cliente._meta.fields},
			"filter_fn": lambda self, queryset, filtros: queryset,
		},
		"fornecedores": {
			"queryset": Fornecedor.objects.select_related("id_codsis").all(),
			"search_fields": ["nome_fornecedor", "nome_gerencial", "raz_social", "codigo"],
			"allowed_columns": {field.name for field in Fornecedor._meta.fields},
			"filter_fn": lambda self, queryset, filtros: queryset,
		},
		"vendas": {
			"queryset": Venda.objects.select_related("cliente", "usuario").all(),
			"search_fields": ["id_legado", "tipo_documento", "status", "cliente__nome_cliente", "usuario__nome"],
			"allowed_columns": {field.name for field in Venda._meta.fields},
			"filter_fn": lambda self, queryset, filtros: self._apply_venda_filters(queryset, filtros),
		},
		"itens_venda": {
			"queryset": ItemVenda.objects.select_related("venda", "produto", "unidade_medida").all(),
			"search_fields": ["venda__id_legado", "venda__tipo_documento", "produto__produto", "venda__cliente__nome_cliente"],
			"allowed_columns": {field.name for field in ItemVenda._meta.fields},
			"filter_fn": lambda self, queryset, filtros: self._apply_item_filters(queryset, filtros),
		},
		"pagamentos_venda": {
			"queryset": PagamentoVenda.objects.select_related("venda", "forma_pagamento").all(),
			"search_fields": ["venda__id_legado", "venda__tipo_documento", "forma_pagamento__descricao", "venda__cliente__nome_cliente"],
			"allowed_columns": {field.name for field in PagamentoVenda._meta.fields},
			"filter_fn": lambda self, queryset, filtros: self._apply_pagamento_filters(queryset, filtros),
		},
		"compras": {
			"queryset": Compra.objects.select_related("fornecedor").all(),
			"search_fields": ["id_legado", "nota", "nfe_status", "fornecedor__nome_fornecedor"],
			"allowed_columns": {field.name for field in Compra._meta.fields},
			"filter_fn": lambda self, queryset, filtros: self._apply_compra_filters(queryset, filtros),
		},
		"itens_compra": {
			"queryset": ItemCompra.objects.select_related("compra", "produto", "unidade_medida").all(),
			"search_fields": ["compra__id_legado", "compra__nota", "compra__nfe_status", "compra__fornecedor__nome_fornecedor", "produto__produto"],
			"allowed_columns": {field.name for field in ItemCompra._meta.fields},
			"filter_fn": lambda self, queryset, filtros: self._apply_item_compra_filters(queryset, filtros),
		},
	}

	def post(self, request):
		serializer = ExportacaoRequestSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		validated = serializer.validated_data

		tabela = validated["tabela"]
		tipo = validated.get("tipo", "BASICO")
		colunas = validated.get("colunas") or []
		query_sql = validated.get("query_sql") or ""
		formato = validated["formato"]
		search = (validated.get("search") or request.query_params.get("search") or "").strip()
		filtros = validated.get("filtros") or {}

		config = self.TABLE_CONFIG[tabela]

		if tipo == "BASICO":
			allowed_columns = config["allowed_columns"]
			invalid_columns = [column for column in colunas if column not in allowed_columns]
			if invalid_columns:
				return Response({"detail": f"Colunas invalidas: {', '.join(invalid_columns)}"}, status=400)

			queryset = config["queryset"]
			queryset = config["filter_fn"](self, queryset, filtros)
			if search:
				query = Q()
				for field in config["search_fields"]:
					query |= Q(**{f"{field}__icontains": search})
				queryset = queryset.filter(query)

			queryset = queryset.order_by(queryset.model._meta.pk.name)
			content = export_queryset_data(queryset, colunas, formato)
		else:
			safe_query = validate_safe_select_sql(query_sql)
			with connection.cursor() as cursor:
				cursor.execute(safe_query)
				rows = cursor.fetchall()
				columns = [col[0] for col in (cursor.description or [])]

			dataframe = pd.DataFrame(rows, columns=columns)
			content = export_dataframe(dataframe, formato)

		filename = f"exportacao_{tabela}.{formato}"

		response = HttpResponse(content, content_type=EXPORT_CONTENT_TYPES[formato])
		response["Content-Disposition"] = f'attachment; filename="{filename}"'
		return response
