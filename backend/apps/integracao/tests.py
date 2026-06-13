from __future__ import annotations

import os
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.integracao.models import FirebirdConnectionConfig


@pytest.mark.django_db
def test_firebird_config_get_and_put() -> None:
	client = APIClient()

	response_get = client.get("/api/integracao/firebird-config", HTTP_HOST="localhost")
	assert response_get.status_code == 200
	payload_get = response_get.json()
	assert payload_get["modo_localizacao"] in {"FIXED", "DYNAMIC"}

	response_put = client.put(
		"/api/integracao/firebird-config",
		data={
			"modo_localizacao": "FIXED",
			"caminho_fixo": "C:/bases/teste.fdb",
		},
		format="json",
		HTTP_HOST="localhost",
	)
	assert response_put.status_code == 200

	config = FirebirdConnectionConfig.get_solo()
	assert config.modo_localizacao == "FIXED"
	assert config.caminho_fixo == "C:/bases/teste.fdb"


@pytest.mark.django_db
def test_sincronizar_erp_fixed_uses_saved_path(monkeypatch) -> None:
	config = FirebirdConnectionConfig.get_solo()
	config.modo_localizacao = FirebirdConnectionConfig.MODO_FIXO
	config.caminho_fixo = "C:/bases/fixo.fdb"
	config.save(update_fields=["modo_localizacao", "caminho_fixo", "atualizado_em"])

	captured = {"path": None}

	async def fake_execucao(*, firebird_path=None):
		captured["path"] = firebird_path
		return {"produtos": 0, "clientes": 0, "fornecedores": 0}

	monkeypatch.setattr("apps.integracao.views.executar_extracao_completa", fake_execucao)

	client = APIClient()
	response = client.post(
		"/api/integracao/sincronizar",
		data={},
		format="json",
		HTTP_HOST="localhost",
	)

	assert response.status_code == 200
	assert captured["path"] == "C:/bases/fixo.fdb"


@pytest.mark.django_db
def test_sincronizar_erp_dynamic_requires_file() -> None:
	config = FirebirdConnectionConfig.get_solo()
	config.modo_localizacao = FirebirdConnectionConfig.MODO_DINAMICO
	config.save(update_fields=["modo_localizacao", "atualizado_em"])

	client = APIClient()
	response = client.post(
		"/api/integracao/sincronizar",
		data={},
		format="multipart",
		HTTP_HOST="localhost",
	)

	assert response.status_code == 400
	assert "Modo dinamico" in str(response.json().get("detail", ""))


@pytest.mark.django_db
def test_sincronizar_erp_dynamic_uses_uploaded_file(monkeypatch) -> None:
	config = FirebirdConnectionConfig.get_solo()
	config.modo_localizacao = FirebirdConnectionConfig.MODO_DINAMICO
	config.save(update_fields=["modo_localizacao", "atualizado_em"])

	captured = {"path": None, "exists_during_call": False}

	async def fake_execucao(*, firebird_path=None):
		captured["path"] = firebird_path
		captured["exists_during_call"] = bool(firebird_path and os.path.exists(firebird_path))
		return {"produtos": 0, "clientes": 0, "fornecedores": 0}

	monkeypatch.setattr("apps.integracao.views.executar_extracao_completa", fake_execucao)

	arquivo = SimpleUploadedFile(
		"origem.fdb",
		b"FAKE-FIREBIRD-CONTENT",
		content_type="application/octet-stream",
	)

	client = APIClient()
	response = client.post(
		"/api/integracao/sincronizar",
		data={"firebird_file": arquivo},
		format="multipart",
		HTTP_HOST="localhost",
	)

	assert response.status_code == 200
	assert captured["path"]
	assert captured["exists_during_call"] is True


@pytest.mark.django_db
def test_sincronizar_erp_dynamic_uses_firebird_path(monkeypatch, tmp_path: Path) -> None:
	config = FirebirdConnectionConfig.get_solo()
	config.modo_localizacao = FirebirdConnectionConfig.MODO_DINAMICO
	config.save(update_fields=["modo_localizacao", "atualizado_em"])

	temp_firebird = tmp_path / "origem.fdb"
	temp_firebird.write_bytes(b"FAKE-FIREBIRD-CONTENT")

	captured = {"path": None}

	async def fake_execucao(*, firebird_path=None):
		captured["path"] = firebird_path
		return {"produtos": 0, "clientes": 0, "fornecedores": 0}

	monkeypatch.setattr("apps.integracao.views.executar_extracao_completa", fake_execucao)

	client = APIClient()
	response = client.post(
		"/api/integracao/sincronizar",
		data={"firebird_path": str(temp_firebird)},
		format="json",
		HTTP_HOST="localhost",
	)

	assert response.status_code == 200
	assert captured["path"] == str(temp_firebird.resolve())


@pytest.mark.django_db
def test_firebird_picker_endpoint_returns_selected_path(monkeypatch, tmp_path: Path) -> None:
	selected = tmp_path / "selecionado.fdb"
	selected.write_bytes(b"FAKE-FIREBIRD-CONTENT")

	monkeypatch.setattr(
		"apps.integracao.views.pick_firebird_file_via_os_dialog",
		lambda: str(selected),
	)

	client = APIClient()
	response = client.post(
		"/api/integracao/firebird-picker",
		data={},
		format="json",
		HTTP_HOST="localhost",
	)

	assert response.status_code == 200
	assert response.json().get("firebird_path") == str(selected.resolve())
