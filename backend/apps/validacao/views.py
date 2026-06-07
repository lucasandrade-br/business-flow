from __future__ import annotations

from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.integracao.models import StgClientesNovos, StgFornecedoresNovos, StgProdutosNovos
from .serializers import (
    AprovarClienteSerializer,
    AprovarFornecedorSerializer,
    AprovarProdutoSerializer,
    ClientePendenteSerializer,
    FornecedorPendenteSerializer,
    ProdutoPendenteSerializer,
)
from .services import (
    aprovar_cliente_novo,
    aprovar_fornecedor_novo,
    aprovar_produto_novo,
    listar_clientes_pendentes,
    listar_fornecedores_pendentes,
    listar_produtos_pendentes,
)


class ResumoPendenciasAPIView(APIView):
    def get(self, request: Request) -> Response:
        return Response(
            {
                "produtos": StgProdutosNovos.objects.count(),
                "clientes": StgClientesNovos.objects.count(),
                "fornecedores": StgFornecedoresNovos.objects.count(),
            }
        )


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
