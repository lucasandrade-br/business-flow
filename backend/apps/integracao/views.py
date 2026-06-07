from __future__ import annotations

from asgiref.sync import async_to_sync
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import executar_extracao_completa


class SincronizarERPAPIView(APIView):
	def post(self, request: Request) -> Response:
		resultado = async_to_sync(executar_extracao_completa)()
		return Response(
			{
				"detail": "Sincronizacao concluida com sucesso.",
				"resultado": resultado,
			},
			status=status.HTTP_200_OK,
		)
