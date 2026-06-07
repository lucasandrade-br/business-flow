from __future__ import annotations

import pytest
from rest_framework.test import APIClient


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
