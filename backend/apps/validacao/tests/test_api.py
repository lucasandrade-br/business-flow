from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.cadastros.models import Cliente, Fornecedor, Produto
from apps.integracao.hash_engine import gerar_hash_cliente, gerar_hash_fornecedor, gerar_hash_produto
from apps.integracao.models import StgClientesNovos, StgFornecedoresNovos, StgProdutosNovos
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


@pytest.mark.django_db
def test_aprovar_produto_persiste_ncm() -> None:
    client = APIClient()

    payload = {
        "id_produto": 98701,
        "nome": "Produto com NCM",
        "status": "ATIVO",
        "custo": "10.000000",
        "valor_venda": "12.500000",
        "id_und_medida": 1,
        "ncm": "22030000",
    }

    response = client.post(
        "/api/validacao/produtos/aprovar",
        data=payload,
        format="json",
    )

    assert response.status_code == 201
    produto = Produto.objects.get(id_produto=98701)
    assert produto.ncm == "22030000"
    assert produto.nome_gerencial == "Produto com NCM"
    assert produto.hash_md5 == gerar_hash_produto(
        id_produto=98701,
        gtin="",
        barras="",
        nome="Produto com NCM",
        custo=Decimal("10.000000"),
        venda=Decimal("12.500000"),
        status="ATIVO",
    )


@pytest.mark.django_db
def test_aprovar_produto_persiste_nome_gerencial_customizado_sem_afetar_hash() -> None:
    client = APIClient()

    payload = {
        "id_produto": 98702,
        "nome_original": "PRODUTO TECNICO",
        "nome_gerencial": "Produto para Vitrine",
        "status": "ATIVO",
        "custo": "22.100000",
        "valor_venda": "30.990000",
        "id_und_medida": 1,
        "gtin": "789999",
        "barras": "789999",
    }

    response = client.post(
        "/api/validacao/produtos/aprovar",
        data=payload,
        format="json",
    )

    assert response.status_code == 201

    produto = Produto.objects.get(id_produto=98702)
    assert produto.produto == "PRODUTO TECNICO"
    assert produto.nome_gerencial == "Produto para Vitrine"
    assert produto.hash_md5 == gerar_hash_produto(
        id_produto=98702,
        gtin="789999",
        barras="789999",
        nome="PRODUTO TECNICO",
        custo=Decimal("22.100000"),
        venda=Decimal("30.990000"),
        status="ATIVO",
    )


@pytest.mark.django_db
def test_produtos_pendentes_retorna_ncm_da_staging() -> None:
    StgProdutosNovos.objects.create(
        id_produto=77123,
        gtin="",
        barras="",
        ncm="04022110",
        nome="Leite em Po",
        unidade_comecial="UN",
        custo="7.100000",
        valor_venda="9.200000",
        status="ATIVO",
    )

    client = APIClient()
    response = client.get("/api/validacao/produtos/pendentes", HTTP_HOST="localhost")

    assert response.status_code == 200
    payload = response.json()
    rows = payload.get("results") or []
    row = next((item for item in rows if int(item.get("id_produto")) == 77123), None)
    assert row is not None
    assert row.get("ncm") == "04022110"


@pytest.mark.django_db
def test_produtos_pendentes_retorna_nome_gerencial_sot_quando_existir() -> None:
    Produto.objects.create(
        id_produto=77124,
        produto="LEITE EM PO",
        nome_gerencial="Leite em Po Instantaneo",
        gtin="",
        barras="",
        ncm="04022110",
        custo=Decimal("7.100000"),
        venda=Decimal("9.200000"),
        status="ATIVO",
        markup=Decimal("0.0000"),
        markup_inv=Decimal("0.0000"),
        perda=Decimal("0.0000"),
        fisico=Decimal("0.0000"),
        aliqefc="",
        cod_g3n=0,
        cod_rel=0,
        usuario="",
    )

    StgProdutosNovos.objects.create(
        id_produto=77124,
        gtin="",
        barras="",
        ncm="04022110",
        nome="LEITE EM PO",
        unidade_comecial="UN",
        custo="8.000000",
        valor_venda="9.200000",
        status="ATIVO",
    )

    client = APIClient()
    response = client.get("/api/validacao/produtos/pendentes", HTTP_HOST="localhost")

    assert response.status_code == 200
    payload = response.json()
    rows = payload.get("results") or []
    row = next((item for item in rows if int(item.get("id_produto")) == 77124), None)
    assert row is not None
    assert row.get("nome_gerencial") == "Leite em Po Instantaneo"


@pytest.mark.django_db
def test_aprovar_cliente_persiste_nome_gerencial_customizado_sem_afetar_hash() -> None:
    client = APIClient()

    payload = {
        "id_cliente": 99801,
        "nome_original": "CLIENTE TECNICO LTDA",
        "nome_gerencial": "Cliente Varejo Sul",
        "raz_social": "CLIENTE TECNICO LTDA",
        "prazo_cob": 15,
    }

    response = client.post(
        "/api/validacao/clientes/aprovar",
        data=payload,
        format="json",
    )

    assert response.status_code == 201
    cliente = Cliente.objects.get(id_cliente=99801)
    assert cliente.nome_cliente == "CLIENTE TECNICO LTDA"
    assert cliente.nome_gerencial == "Cliente Varejo Sul"
    assert cliente.hash_md5 == gerar_hash_cliente(
        id_cliente=99801,
        nome_cliente="CLIENTE TECNICO LTDA",
        raz_social="CLIENTE TECNICO LTDA",
    )


@pytest.mark.django_db
def test_aprovar_fornecedor_persiste_nome_gerencial_customizado_sem_afetar_hash() -> None:
    client = APIClient()

    payload = {
        "id_fornecedor": 99802,
        "nome_original": "FORNECEDOR TECNICO",
        "nome_gerencial": "Fornecedor Regional Norte",
        "raz_social": "FORNECEDOR TECNICO SA",
        "codigo": "7",
        "operador": 1,
        "usuario": "admin",
    }

    response = client.post(
        "/api/validacao/fornecedores/aprovar",
        data=payload,
        format="json",
    )

    assert response.status_code == 201
    fornecedor = Fornecedor.objects.get(id_fornecedor=99802)
    assert fornecedor.nome_fornecedor == "FORNECEDOR TECNICO"
    assert fornecedor.nome_gerencial == "Fornecedor Regional Norte"
    assert fornecedor.hash_md5 == gerar_hash_fornecedor(
        id_fornecedor=99802,
        nome_fornecedor="FORNECEDOR TECNICO",
        raz_social="FORNECEDOR TECNICO SA",
        dt_cadastro=fornecedor.dt_cadastro,
    )


@pytest.mark.django_db
def test_clientes_pendentes_retorna_nome_gerencial_sot_quando_existir() -> None:
    Cliente.objects.create(
        id_cliente=99811,
        nome_cliente="CLIENTE BASE",
        nome_gerencial="Cliente Base Premium",
        raz_social="CLIENTE BASE LTDA",
        prazo_cob=0,
    )

    StgClientesNovos.objects.create(
        id_cliente=99811,
        cliente="CLIENTE BASE ALTERADO",
        raz_social="CLIENTE BASE LTDA",
    )

    client = APIClient()
    response = client.get("/api/validacao/clientes/pendentes", HTTP_HOST="localhost")

    assert response.status_code == 200
    payload = response.json()
    rows = payload.get("results") or []
    row = next((item for item in rows if int(item.get("id_cliente")) == 99811), None)
    assert row is not None
    assert row.get("nome_gerencial") == "Cliente Base Premium"


@pytest.mark.django_db
def test_fornecedores_pendentes_retorna_nome_gerencial_sot_quando_existir() -> None:
    Fornecedor.objects.create(
        id_fornecedor=99812,
        nome_fornecedor="FORNECEDOR BASE",
        nome_gerencial="Fornecedor Base Centro",
        raz_social="FORNECEDOR BASE LTDA",
        codigo="",
        operador=0,
        usuario="",
    )

    StgFornecedoresNovos.objects.create(
        id_fornecedor=99812,
        fantasia="FORNECEDOR BASE ALTERADO",
        raz_social="FORNECEDOR BASE LTDA",
    )

    client = APIClient()
    response = client.get("/api/validacao/fornecedores/pendentes", HTTP_HOST="localhost")

    assert response.status_code == 200
    payload = response.json()
    rows = payload.get("results") or []
    row = next((item for item in rows if int(item.get("id_fornecedor")) == 99812), None)
    assert row is not None
    assert row.get("nome_gerencial") == "Fornecedor Base Centro"
