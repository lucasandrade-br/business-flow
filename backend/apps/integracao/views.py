from __future__ import annotations

from asgiref.sync import async_to_sync
from django.conf import settings
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.integracao.firebird_config import (
	get_firebird_connection_config,
	pick_firebird_file_via_os_dialog,
	resolve_firebird_path_for_request,
	serialize_firebird_connection_config,
	validate_firebird_path,
)
from apps.integracao.models import FirebirdConnectionConfig
from .services import executar_extracao_completa


class FirebirdConnectionConfigAPIView(APIView):
	def get(self, request: Request) -> Response:
		config = get_firebird_connection_config()
		return Response(serialize_firebird_connection_config(config), status=status.HTTP_200_OK)

	def put(self, request: Request) -> Response:
		modo_localizacao = str(request.data.get("modo_localizacao") or "").strip().upper()
		if modo_localizacao not in {
			FirebirdConnectionConfig.MODO_FIXO,
			FirebirdConnectionConfig.MODO_DINAMICO,
		}:
			return Response(
				{
					"detail": (
						"modo_localizacao invalido. Use FIXED ou DYNAMIC."
					)
				},
				status=status.HTTP_400_BAD_REQUEST,
			)

		caminho_fixo = str(request.data.get("caminho_fixo") or "").strip()
		config = get_firebird_connection_config()

		config.modo_localizacao = modo_localizacao
		config.caminho_fixo = caminho_fixo

		fallback_env = str(getattr(settings, "FDB_PATH", "") or "").strip()
		caminho_resolvido = caminho_fixo or fallback_env

		if modo_localizacao == FirebirdConnectionConfig.MODO_FIXO and not caminho_resolvido:
			return Response(
				{
					"detail": (
						"Informe um caminho fixo valido para o Firebird "
						"ou configure FDB_PATH no ambiente."
					)
				},
				status=status.HTTP_400_BAD_REQUEST,
			)

		config.save(update_fields=["modo_localizacao", "caminho_fixo", "atualizado_em"])
		return Response(serialize_firebird_connection_config(config), status=status.HTTP_200_OK)


class FirebirdFilePickerAPIView(APIView):
	def post(self, request: Request) -> Response:
		try:
			selected_path = pick_firebird_file_via_os_dialog()
		except RuntimeError as exc:
			return Response({"detail": str(exc)}, status=status.HTTP_501_NOT_IMPLEMENTED)

		if not selected_path:
			return Response(
				{"detail": "Selecao de arquivo Firebird cancelada."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		try:
			firebird_path = validate_firebird_path(selected_path)
		except ValueError as exc:
			return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

		return Response(
			{"firebird_path": firebird_path},
			status=status.HTTP_200_OK,
		)


class SincronizarERPAPIView(APIView):
	def post(self, request: Request) -> Response:
		try:
			with resolve_firebird_path_for_request(request) as firebird_path:
				resultado = async_to_sync(executar_extracao_completa)(firebird_path=firebird_path)
		except ValueError as exc:
			return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
		except Exception:
			return Response(
				{"detail": "Falha ao sincronizar dados do ERP."},
				status=status.HTTP_500_INTERNAL_SERVER_ERROR,
			)

		return Response(
			{
				"detail": "Sincronizacao concluida com sucesso.",
				"resultado": resultado,
			},
			status=status.HTTP_200_OK,
		)
