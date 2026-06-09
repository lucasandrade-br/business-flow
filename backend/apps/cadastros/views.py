from __future__ import annotations

import pandas as pd
from django.db import connection
from django.db.models import Count, Q
from django.http import HttpResponse
from rest_framework import status
from rest_framework import filters, generics, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aliquota, Cliente, FormaPagamento, Fornecedor, GrupoCliente, PlanoConta, Produto, TemplateExportacao, TipoVenda, UnidadeMedida
from .serializers import (
	AliquotaSerializer,
	ClienteSerializer,
	ExportacaoRequestSerializer,
	FormaPagamentoSerializer,
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
	search_fields = ["produto", "id_produto"]

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
	search_fields = ["nome_fornecedor", "raz_social", "codigo"]


class FornecedorDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
	queryset = Fornecedor.objects.select_related("id_codsis").all()
	serializer_class = FornecedorSerializer
	lookup_field = "id_fornecedor"


class ClienteListCreateAPIView(generics.ListCreateAPIView):
	queryset = Cliente.objects.select_related("id_grupo", "id_tipo_venda").all().order_by("id_cliente")
	serializer_class = ClienteSerializer
	filter_backends = [filters.SearchFilter]
	search_fields = ["nome_cliente", "raz_social"]


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
	TABLE_CONFIG = {
		"produtos": {
			"queryset": Produto.objects.select_related("id_und_medida").prefetch_related("categorias").all(),
			"search_fields": ["produto"],
			"allowed_columns": {field.name for field in Produto._meta.fields},
		},
		"clientes": {
			"queryset": Cliente.objects.select_related("id_grupo", "id_tipo_venda").all(),
			"search_fields": ["nome_cliente", "raz_social"],
			"allowed_columns": {field.name for field in Cliente._meta.fields},
		},
		"fornecedores": {
			"queryset": Fornecedor.objects.select_related("id_codsis").all(),
			"search_fields": ["nome_fornecedor", "raz_social", "codigo"],
			"allowed_columns": {field.name for field in Fornecedor._meta.fields},
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

		config = self.TABLE_CONFIG[tabela]

		if tipo == "BASICO":
			allowed_columns = config["allowed_columns"]
			invalid_columns = [column for column in colunas if column not in allowed_columns]
			if invalid_columns:
				return Response({"detail": f"Colunas invalidas: {', '.join(invalid_columns)}"}, status=400)

			queryset = config["queryset"]
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
