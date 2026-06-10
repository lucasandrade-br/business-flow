from __future__ import annotations

from datetime import datetime

from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    AprovarClienteSerializer,
    AprovarFornecedorSerializer,
    AprovarProdutoSerializer,
    ClientePendenteSerializer,
    FornecedorPendenteSerializer,
    ProdutoPendenteSerializer,
)
from .services import (
    aplicar_tratamento_pendencias_lote,
    aplicar_tratamento_divergencia,
    aplicar_tratamento_divergencias_lote,
    aprovar_cliente_novo,
    aprovar_fornecedor_novo,
    aprovar_produto_novo,
    consolidar_stg_para_sot,
    contar_pendencias_validacao,
    get_importacao_job,
    listar_divergencias_reconciliacao,
    listar_formas_pagamento,
    listar_clientes_pendentes,
    listar_fornecedores_pendentes,
    listar_produtos_pendentes,
    obter_kpis_reconciliacao,
    start_importacao_planilhas_auditoria,
    sincronizar_vendas_legado,
)


class ResumoPendenciasAPIView(APIView):
    def get(self, request: Request) -> Response:
        return Response(contar_pendencias_validacao())


class ProdutosPendentesAPIView(generics.ListAPIView):
    serializer_class = ProdutoPendenteSerializer

    def list(self, request: Request, *args, **kwargs) -> Response:
        search = request.query_params.get("search", "").strip()
        data = listar_produtos_pendentes(search=search)
        paginator = PageNumberPagination()
        paginator.page_size = 50
        page = paginator.paginate_queryset(data, request, view=self)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AprovarProdutoAPIView(APIView):
    def post(self, request: Request) -> Response:
        serializer = AprovarProdutoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        aprovar_produto_novo(serializer.validated_data)
        return Response(
            {"detail": "Produto aprovado com sucesso."},
            status=status.HTTP_201_CREATED,
        )


class ClientesPendentesAPIView(generics.ListAPIView):
    serializer_class = ClientePendenteSerializer

    def list(self, request: Request, *args, **kwargs) -> Response:
        search = request.query_params.get("search", "").strip()
        data = listar_clientes_pendentes(search=search)
        paginator = PageNumberPagination()
        paginator.page_size = 50
        page = paginator.paginate_queryset(data, request, view=self)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AprovarClienteAPIView(APIView):
    def post(self, request: Request) -> Response:
        serializer = AprovarClienteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        aprovar_cliente_novo(serializer.validated_data)
        return Response({"detail": "Cliente aprovado com sucesso."}, status=status.HTTP_201_CREATED)


class FornecedoresPendentesAPIView(generics.ListAPIView):
    serializer_class = FornecedorPendenteSerializer

    def list(self, request: Request, *args, **kwargs) -> Response:
        search = request.query_params.get("search", "").strip()
        data = listar_fornecedores_pendentes(search=search)
        paginator = PageNumberPagination()
        paginator.page_size = 50
        page = paginator.paginate_queryset(data, request, view=self)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AprovarFornecedorAPIView(APIView):
    def post(self, request: Request) -> Response:
        serializer = AprovarFornecedorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        aprovar_fornecedor_novo(serializer.validated_data)
        return Response({"detail": "Fornecedor aprovado com sucesso."}, status=status.HTTP_201_CREATED)


class PendenciasTratarLoteAPIView(APIView):
    def post(self, request: Request) -> Response:
        entidade = str(request.data.get("entidade") or "").strip().lower()
        acao = str(request.data.get("acao") or "").strip().lower()
        ids_raw = request.data.get("ids") or []

        if not entidade or not acao or not isinstance(ids_raw, list) or not ids_raw:
            return Response(
                {"detail": "Campos obrigatorios: entidade, acao e ids (lista)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ids = [int(item) for item in ids_raw]
        except (TypeError, ValueError):
            return Response(
                {"detail": "ids deve conter apenas valores numericos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            resultado = aplicar_tratamento_pendencias_lote(entidade=entidade, acao=acao, ids=ids)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"detail": "Falha ao aplicar tratamento em lote para pendencias."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(resultado, status=status.HTTP_200_OK)


class SincronizarVendasFirebirdAPIView(APIView):
    def post(self, request: Request) -> Response:
        data_inicial_raw = request.data.get("data_inicial")
        data_final_raw = request.data.get("data_final")

        if not data_inicial_raw or not data_final_raw:
            return Response(
                {"detail": "Campos obrigatorios: data_inicial e data_final."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data_inicial = datetime.strptime(str(data_inicial_raw), "%Y-%m-%d").date()
            data_final = datetime.strptime(str(data_final_raw), "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"detail": "Formato de data invalido. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if data_inicial > data_final:
            return Response(
                {"detail": "data_inicial nao pode ser maior que data_final."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resultado = sincronizar_vendas_legado(data_inicial=data_inicial, data_final=data_final)
        return Response(
            {
                "detail": "Sincronizacao de vendas legado concluida com sucesso.",
                "resultado": resultado,
            },
            status=status.HTTP_200_OK,
        )


class ImportarAuditoriaPlanilhaAPIView(APIView):
    def post(self, request: Request) -> Response:
        arquivos = request.FILES.getlist("files")
        if not arquivos:
            return Response(
                {"detail": "Envie ao menos um arquivo em 'files'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            job_id = start_importacao_planilhas_auditoria(arquivos)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            return Response(
                {"detail": "Falha ao importar planilhas de auditoria."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "detail": "Importacao de planilhas iniciada com sucesso.",
                "job_id": job_id,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ImportarAuditoriaPlanilhaStatusAPIView(APIView):
    def get(self, request: Request, job_id: str) -> Response:
        job = get_importacao_job(job_id)
        if not job:
            return Response(
                {"detail": "Job de importacao nao encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(job, status=status.HTTP_200_OK)


class ConsolidarVendasSOTAPIView(APIView):
    def post(self, request: Request) -> Response:
        try:
            resultado = consolidar_stg_para_sot()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"detail": "Falha ao consolidar vendas da STG para o SOT."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "detail": "Consolidacao STG->SOT concluida.",
                "resultado": resultado,
            },
            status=status.HTTP_200_OK,
        )


class ReconciliacaoDivergenciasAPIView(APIView):
    def get(self, request: Request) -> Response:
        motivo = request.query_params.get("motivo", "")
        tratamento = request.query_params.get("tratamento", "")
        somente_finalizados_raw = str(request.query_params.get("somente_finalizados", "")).strip().lower()
        somente_finalizados = somente_finalizados_raw in {"1", "true", "yes", "sim", "on"}
        status_venda = request.query_params.get("status_venda", "")

        rows = listar_divergencias_reconciliacao(
            motivo=motivo,
            status_tratamento=tratamento,
            somente_finalizados=somente_finalizados,
            status_venda=status_venda,
        )

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(rows, request, view=self)

        return paginator.get_paginated_response(
            {
                "rows": page,
                "kpis": obter_kpis_reconciliacao(),
            }
        )


class ReconciliacaoTratarDivergenciaAPIView(APIView):
    def post(self, request: Request) -> Response:
        tipo_documento = str(request.data.get("tipo_documento") or "").strip().upper()
        id_legado_raw = request.data.get("id_legado")
        acao = str(request.data.get("acao") or "").strip().lower()

        if not tipo_documento or id_legado_raw in (None, "") or not acao:
            return Response(
                {"detail": "Campos obrigatorios: tipo_documento, id_legado e acao."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            id_legado = int(id_legado_raw)
        except (TypeError, ValueError):
            return Response({"detail": "id_legado invalido."}, status=status.HTTP_400_BAD_REQUEST)

        payload = request.data.get("payload") or {}
        try:
            resultado = aplicar_tratamento_divergencia(
                tipo_documento=tipo_documento,
                id_legado=id_legado,
                acao=acao,
                payload=payload,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"detail": "Falha ao aplicar tratamento da divergencia."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(resultado, status=status.HTTP_200_OK)


class ReconciliacaoTratarDivergenciaLoteAPIView(APIView):
    def post(self, request: Request) -> Response:
        acao = str(request.data.get("acao") or "").strip().lower()
        vendas = request.data.get("vendas") or []

        if not acao or not isinstance(vendas, list) or not vendas:
            return Response(
                {"detail": "Campos obrigatorios: acao e vendas (lista)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = request.data.get("payload") or {}
            resultado = aplicar_tratamento_divergencias_lote(vendas=vendas, acao=acao, payload=payload)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"detail": "Falha ao aplicar tratamento em lote."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(resultado, status=status.HTTP_200_OK)


class ReconciliacaoFormasPagamentoAPIView(APIView):
    def get(self, request: Request) -> Response:
        return Response({"rows": listar_formas_pagamento()}, status=status.HTTP_200_OK)
