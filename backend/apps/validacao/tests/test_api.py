from __future__ import annotations

from contextlib import contextmanager

import pytest
from rest_framework.test import APIClient

from apps.validacao.services.firebird_etl import SincronizacaoVendasEmAndamentoError


@pytest.mark.django_db
def test_aprovar_produto_retorna_400_sem_status() -> None:
    client = APIClient()

    payload = {
        "id_produto": 101,
        "nome": "Produto de Teste",
        "custo": "10.000000",
        "valor_venda": "12.500000",
        "id_und_medida": 1,
    }

    response = client.post(
        "/api/validacao/produtos/aprovar",
        data=payload,
        format="json",
    )

    assert response.status_code == 400
    assert "status" in response.data


@pytest.mark.django_db
def test_sincronizar_vendas_retorna_409_quando_sync_ja_em_andamento(monkeypatch) -> None:
    client = APIClient()

    @contextmanager
    def fake_resolver(_request):
        yield "C:/base/firebird.fdb"

    def fake_sync(*_args, **_kwargs):
        raise SincronizacaoVendasEmAndamentoError("Sync em andamento")

    monkeypatch.setattr("apps.validacao.views.resolve_firebird_path_for_request", fake_resolver)
    monkeypatch.setattr("apps.validacao.views.sincronizar_vendas_legado", fake_sync)

    response = client.post(
        "/api/validacao/sincronizar-vendas-firebird",
        data={"data_inicial": "2026-03-23", "data_final": "2026-04-01"},
        format="json",
        HTTP_HOST="localhost",
    )

    assert response.status_code == 409
    assert "Sync em andamento" in str(response.data.get("detail", ""))


@pytest.mark.django_db
def test_reconciliacao_divergencias_retorna_409_durante_sync(monkeypatch) -> None:
    client = APIClient()

    monkeypatch.setattr("apps.validacao.views.sincronizacao_vendas_em_andamento", lambda: True)

    response = client.get(
        "/api/validacao/reconciliacao/divergencias",
        HTTP_HOST="localhost",
    )

    assert response.status_code == 409
    assert "Sincronizacao de vendas em andamento" in str(response.data.get("detail", ""))
