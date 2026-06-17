from __future__ import annotations

from datetime import datetime

from rest_framework import filters
from rest_framework import status
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.integracao.firebird_config import resolve_firebird_path_for_request
from apps.compras.models import Compra, ItemCompra
from apps.compras.serializers import (
    CompraDetailSerializer,
    CompraListSerializer,
    ItemCompraListSerializer,
    SincronizarComprasFirebirdRequestSerializer,
    TratarDivergenciaCompraRequestSerializer,
    TratarDivergenciasCompraLoteRequestSerializer,
)
from apps.compras.services import (
    ReconciliacaoCompraBloqueioError,
    aplicar_tratamento_divergencia_compra,
    aplicar_tratamento_divergencias_compra_lote,
    consolidar_compras_stg_para_sot,
    executar_validacao_compras,
    limpar_fluxo_reconciliacao_compras,
    obter_queryset_divergencias_reconciliacao_compras,
    obter_kpis_reconciliacao_compras,
    serializar_divergencia_reconciliacao_compra,
    sincronizar_compras_legado,
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


class CompraListAPIView(_FiltroDataMixin, generics.ListAPIView):
    serializer_class = CompraListSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["id_legado", "nota", "nfe_status", "fornecedor__nome_fornecedor", "fornecedor__nome_gerencial"]

    def get_queryset(self):
        queryset = Compra.objects.select_related("fornecedor").all().order_by("-data_emissao", "-id_compra")

        date_filters = self._validate_date_range("data_emissao")
        if date_filters:
            queryset = queryset.filter(**date_filters)

        fornecedor_id = self._get_int_param("fornecedor_id")
        if fornecedor_id is not None:
            queryset = queryset.filter(fornecedor_id=fornecedor_id)

        produto_id = self._get_int_param("produto_id")
        if produto_id is not None:
            queryset = queryset.filter(itens__produto_id=produto_id).distinct()

        nfe_status = str(self.request.query_params.get("nfe_status") or "").strip().upper()
        if nfe_status:
            queryset = queryset.filter(nfe_status=nfe_status)

        return queryset


class CompraDetailAPIView(generics.RetrieveAPIView):
    queryset = Compra.objects.select_related("fornecedor").prefetch_related("itens__produto", "itens__unidade_medida")
    serializer_class = CompraDetailSerializer
    lookup_field = "id_compra"


class ItemCompraListAPIView(_FiltroDataMixin, generics.ListAPIView):
    serializer_class = ItemCompraListSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = [
        "compra__id_legado",
        "compra__nota",
        "compra__nfe_status",
        "compra__fornecedor__nome_fornecedor",
        "compra__fornecedor__nome_gerencial",
        "produto__produto",
        "produto__nome_gerencial",
    ]

    def get_queryset(self):
        queryset = ItemCompra.objects.select_related(
            "compra",
            "compra__fornecedor",
            "produto",
            "unidade_medida",
        ).all().order_by("-compra__data_emissao", "-id_item_compra")

        date_filters = self._validate_date_range("compra__data_emissao")
        if date_filters:
            queryset = queryset.filter(**date_filters)

        fornecedor_id = self._get_int_param("fornecedor_id")
        if fornecedor_id is not None:
            queryset = queryset.filter(compra__fornecedor_id=fornecedor_id)

        produto_id = self._get_int_param("produto_id")
        if produto_id is not None:
            queryset = queryset.filter(produto_id=produto_id)

        nfe_status = str(self.request.query_params.get("nfe_status") or "").strip().upper()
        if nfe_status:
            queryset = queryset.filter(compra__nfe_status=nfe_status)

        return queryset


class SincronizarComprasFirebirdAPIView(APIView):
    def post(self, request: Request) -> Response:
        serializer = SincronizarComprasFirebirdRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with resolve_firebird_path_for_request(request) as firebird_path:
                resultado = sincronizar_compras_legado(
                    data_inicial=serializer.validated_data["data_inicial"],
                    data_final=serializer.validated_data["data_final"],
                    firebird_path=firebird_path,
                )
            validacao = executar_validacao_compras(reset_tracking=True)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"detail": "Falha ao sincronizar compras do legado."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "detail": "Sincronizacao de compras legado concluida com sucesso.",
                "resultado": resultado,
                "kpis": validacao.kpis,
            },
            status=status.HTTP_200_OK,
        )


class ReconciliacaoComprasKPIsAPIView(APIView):
    def get(self, request: Request) -> Response:
        return Response(obter_kpis_reconciliacao_compras(), status=status.HTTP_200_OK)


class ReconciliacaoComprasDivergenciasAPIView(APIView):
    def get(self, request: Request) -> Response:
        motivo = request.query_params.get("motivo", "")
        tratamento = request.query_params.get("tratamento", "")
        nfe_status = request.query_params.get("nfe_status", "")
        id_compra_legado = request.query_params.get("id_compra_legado", "")

        compras = obter_queryset_divergencias_reconciliacao_compras(
            motivo=motivo,
            status_tratamento=tratamento,
            nfe_status=nfe_status,
            id_compra_legado=id_compra_legado,
        )

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(compras, request, view=self)
        rows = [serializar_divergencia_reconciliacao_compra(compra) for compra in page]

        return paginator.get_paginated_response(
            {
                "rows": rows,
                "kpis": obter_kpis_reconciliacao_compras(),
            }
        )


class ReconciliacaoComprasTratarDivergenciaAPIView(APIView):
    def post(self, request: Request) -> Response:
        serializer = TratarDivergenciaCompraRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            resultado = aplicar_tratamento_divergencia_compra(
                id_compra_legado=serializer.validated_data["id_compra_legado"],
                acao=serializer.validated_data["acao"],
                payload=serializer.validated_data.get("payload") or {},
            )
        except ReconciliacaoCompraBloqueioError as exc:
            return Response(exc.to_payload(), status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"detail": "Falha ao aplicar tratamento da divergencia de compra."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(resultado, status=status.HTTP_200_OK)


class ReconciliacaoComprasTratarDivergenciaLoteAPIView(APIView):
    def post(self, request: Request) -> Response:
        serializer = TratarDivergenciasCompraLoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            resultado = aplicar_tratamento_divergencias_compra_lote(
                compras=serializer.validated_data["compras"],
                acao=serializer.validated_data["acao"],
            )
        except ReconciliacaoCompraBloqueioError as exc:
            return Response(exc.to_payload(), status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"detail": "Falha ao aplicar tratamento em lote das divergencias de compra."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(resultado, status=status.HTTP_200_OK)


class ConsolidarComprasSOTAPIView(APIView):
    def post(self, request: Request) -> Response:
        try:
            resultado = consolidar_compras_stg_para_sot()
        except ReconciliacaoCompraBloqueioError as exc:
            return Response(exc.to_payload(), status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"detail": "Falha ao consolidar compras da STG para o SOT."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "detail": "Consolidacao STG->SOT de compras concluida.",
                "resultado": resultado,
            },
            status=status.HTTP_200_OK,
        )


class ReconciliacaoComprasLimparFluxoAPIView(APIView):
    def post(self, request: Request) -> Response:
        try:
            resultado = limpar_fluxo_reconciliacao_compras()
        except Exception:
            return Response(
                {"detail": "Falha ao limpar dados temporarios de reconciliacao de compras."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "detail": "Fluxo de reconciliacao de compras reiniciado com sucesso.",
                "resultado": resultado,
            },
            status=status.HTTP_200_OK,
        )
