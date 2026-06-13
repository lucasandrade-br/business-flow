from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.cadastros.models import Fornecedor, Produto, UnidadeMedida
from apps.compras.models import Compra, STG_Compra, STG_ItemCompra
from apps.compras.services import (
    ReconciliacaoCompraBloqueioError,
    aplicar_tratamento_divergencia_compra,
    aplicar_tratamento_divergencias_compra_lote,
    consolidar_compras_stg_para_sot,
    executar_validacao_compras,
    obter_kpis_reconciliacao_compras,
)


def _criar_unidade(sigla: str = "UN") -> UnidadeMedida:
    return UnidadeMedida.objects.create(sigla=sigla, descricao=sigla)


def _criar_fornecedor(id_fornecedor: int, nome: str) -> Fornecedor:
    return Fornecedor.objects.create(
        id_fornecedor=id_fornecedor,
        nome_fornecedor=nome,
    )


def _criar_produto(id_produto: int, nome: str, unidade: UnidadeMedida) -> Produto:
    return Produto.objects.create(
        id_produto=id_produto,
        produto=nome,
        id_und_medida=unidade,
        custo=Decimal("10.000000"),
        venda=Decimal("15.000000"),
        status="ATIVO",
        markup=Decimal("0.0000"),
        markup_inv=Decimal("0.0000"),
        perda=Decimal("0.0000"),
        fisico=Decimal("0.0000"),
        aliqefc="",
        cod_g3n=0,
        cod_rel=0,
    )


def _criar_stg_compra(
    *,
    id_compra_legado: int,
    id_fornecedor_legado: int,
    nome_fornecedor_legado: str,
    valor_total: Decimal,
    valor_produtos: Decimal,
) -> STG_Compra:
    return STG_Compra.objects.create(
        id_compra_legado=id_compra_legado,
        nota=id_compra_legado,
        id_fornecedor_legado=id_fornecedor_legado,
        nome_fornecedor_legado=nome_fornecedor_legado,
        data_emissao=date(2026, 1, 10),
        data_lanc=date(2026, 1, 10),
        valor_total=valor_total,
        valor_produtos=valor_produtos,
        nfe_status="AUTORIZADA",
    )


def _criar_stg_item(
    *,
    compra: STG_Compra,
    id_item_legado: int,
    id_produto_legado: int,
    nome_produto_legado: str,
    unidade_legado: str,
    quantidade: Decimal,
    valor_custo: Decimal,
) -> STG_ItemCompra:
    valor_total = quantidade * valor_custo
    return STG_ItemCompra.objects.create(
        stg_compra=compra,
        id_item_legado=id_item_legado,
        id_compra_legado=compra.id_compra_legado,
        id_produto_legado=id_produto_legado,
        nome_produto_legado=nome_produto_legado,
        unidade_legado=unidade_legado,
        quantidade=quantidade,
        valor_custo=valor_custo,
        valor_total_legado=valor_total,
        valor_total_calculado=valor_total,
    )


@pytest.mark.django_db
def test_validacao_prioriza_semelhanca_sobre_id_no_fornecedor() -> None:
    unidade = _criar_unidade("UN")
    produto = _criar_produto(501, "ARROZ BRANCO", unidade)

    fornecedor_por_id = _criar_fornecedor(100, "FORNECEDOR COM ID LEGADO")
    fornecedor_por_nome = _criar_fornecedor(200, "ACME INDUSTRIA LTDA")

    compra = _criar_stg_compra(
        id_compra_legado=9001,
        id_fornecedor_legado=fornecedor_por_id.id_fornecedor,
        nome_fornecedor_legado="ACME INDUSTRIA LTDA",
        valor_total=Decimal("10.000000"),
        valor_produtos=Decimal("10.000000"),
    )
    _criar_stg_item(
        compra=compra,
        id_item_legado=1,
        id_produto_legado=produto.id_produto,
        nome_produto_legado=produto.produto,
        unidade_legado="UN",
        quantidade=Decimal("1.000000"),
        valor_custo=Decimal("10.000000"),
    )

    resultado = executar_validacao_compras(reset_tracking=True)
    compra.refresh_from_db()

    assert resultado.compras_aprovadas == 1
    assert compra.status_validacao == STG_Compra.STATUS_VALIDADO
    assert compra.fornecedor_resolvido_id == fornecedor_por_nome.id_fornecedor
    assert compra.fornecedor_resolvido_id != fornecedor_por_id.id_fornecedor


@pytest.mark.django_db
def test_normaliza_status_validacao_legado_aprovado_para_validado() -> None:
    compra = _criar_stg_compra(
        id_compra_legado=9990,
        id_fornecedor_legado=1,
        nome_fornecedor_legado="FORNECEDOR LEGADO",
        valor_total=Decimal("1.000000"),
        valor_produtos=Decimal("1.000000"),
    )
    item = _criar_stg_item(
        compra=compra,
        id_item_legado=9991,
        id_produto_legado=1,
        nome_produto_legado="ITEM LEGADO",
        unidade_legado="UN",
        quantidade=Decimal("1.000000"),
        valor_custo=Decimal("1.000000"),
    )

    compra.status_validacao = STG_Compra.STATUS_APROVADO_LEGADO
    compra.save(update_fields=["status_validacao"])
    item.status_validacao = STG_ItemCompra.STATUS_APROVADO_LEGADO
    item.save(update_fields=["status_validacao"])

    obter_kpis_reconciliacao_compras()

    compra.refresh_from_db()
    item.refresh_from_db()
    assert compra.status_validacao == STG_Compra.STATUS_VALIDADO
    assert item.status_validacao == STG_ItemCompra.STATUS_VALIDADO


@pytest.mark.django_db
def test_validacao_bloqueia_valor_negativo() -> None:
    unidade = _criar_unidade("UN")
    produto = _criar_produto(502, "FEIJAO", unidade)
    fornecedor = _criar_fornecedor(300, "FORNECEDOR NEGATIVO")

    compra = _criar_stg_compra(
        id_compra_legado=9002,
        id_fornecedor_legado=fornecedor.id_fornecedor,
        nome_fornecedor_legado=fornecedor.nome_fornecedor,
        valor_total=Decimal("-5.000000"),
        valor_produtos=Decimal("-5.000000"),
    )
    _criar_stg_item(
        compra=compra,
        id_item_legado=2,
        id_produto_legado=produto.id_produto,
        nome_produto_legado=produto.produto,
        unidade_legado="UN",
        quantidade=Decimal("1.000000"),
        valor_custo=Decimal("5.000000"),
    )

    executar_validacao_compras(reset_tracking=True)
    compra.refresh_from_db()

    motivos = compra.snapshot_divergencia.get("motivos") or []
    assert compra.status_validacao == STG_Compra.STATUS_DIVERGENTE
    assert "valor_negativo_bloqueado" in motivos


@pytest.mark.django_db
def test_consolidacao_ignora_id_legado_ja_existente_no_sot() -> None:
    unidade = _criar_unidade("UN")
    produto = _criar_produto(503, "OLEO", unidade)
    fornecedor = _criar_fornecedor(400, "FORNECEDOR CONSOLIDACAO")

    Compra.objects.create(
        id_legado=9100,
        nota=9100,
        fornecedor=fornecedor,
        data_emissao=date(2026, 1, 10),
        data_lanc=date(2026, 1, 10),
        valor_produtos=Decimal("10.000000"),
        valor_total_documento=Decimal("10.000000"),
        nfe_status="AUTORIZADA",
    )

    compra_duplicada = _criar_stg_compra(
        id_compra_legado=9100,
        id_fornecedor_legado=fornecedor.id_fornecedor,
        nome_fornecedor_legado=fornecedor.nome_fornecedor,
        valor_total=Decimal("10.000000"),
        valor_produtos=Decimal("10.000000"),
    )
    _criar_stg_item(
        compra=compra_duplicada,
        id_item_legado=3,
        id_produto_legado=produto.id_produto,
        nome_produto_legado=produto.produto,
        unidade_legado="UN",
        quantidade=Decimal("1.000000"),
        valor_custo=Decimal("10.000000"),
    )

    compra_nova = _criar_stg_compra(
        id_compra_legado=9101,
        id_fornecedor_legado=fornecedor.id_fornecedor,
        nome_fornecedor_legado=fornecedor.nome_fornecedor,
        valor_total=Decimal("20.000000"),
        valor_produtos=Decimal("20.000000"),
    )
    _criar_stg_item(
        compra=compra_nova,
        id_item_legado=4,
        id_produto_legado=produto.id_produto,
        nome_produto_legado=produto.produto,
        unidade_legado="UN",
        quantidade=Decimal("2.000000"),
        valor_custo=Decimal("10.000000"),
    )

    resultado = consolidar_compras_stg_para_sot()

    assert resultado["compras_inseridas"] == 1
    assert Compra.objects.filter(id_legado=9100).count() == 1
    assert Compra.objects.filter(id_legado=9101).count() == 1


@pytest.mark.django_db
def test_consolidacao_bloqueia_quando_ha_divergencia_estrutural() -> None:
    _criar_unidade("UN")
    fornecedor = _criar_fornecedor(500, "FORNECEDOR BLOQUEIO")

    compra = _criar_stg_compra(
        id_compra_legado=9200,
        id_fornecedor_legado=fornecedor.id_fornecedor,
        nome_fornecedor_legado=fornecedor.nome_fornecedor,
        valor_total=Decimal("10.000000"),
        valor_produtos=Decimal("10.000000"),
    )
    _criar_stg_item(
        compra=compra,
        id_item_legado=5,
        id_produto_legado=999999,
        nome_produto_legado="PRODUTO SEM MATCH",
        unidade_legado="ZZ",
        quantidade=Decimal("1.000000"),
        valor_custo=Decimal("10.000000"),
    )

    with pytest.raises(ReconciliacaoCompraBloqueioError) as exc_info:
        consolidar_compras_stg_para_sot()

    assert exc_info.value.codigo == "consolidacao_bloqueada_divergencia_reconciliacao"
    assert exc_info.value.bloqueios


@pytest.mark.django_db
def test_validacao_lote_permite_divergencia_total_itens() -> None:
    unidade = _criar_unidade("UN")
    produto = _criar_produto(7001, "PRODUTO VALIDACAO LOTE", unidade)
    fornecedor = _criar_fornecedor(7001, "FORNECEDOR VALIDACAO LOTE")

    compra = _criar_stg_compra(
        id_compra_legado=9701,
        id_fornecedor_legado=fornecedor.id_fornecedor,
        nome_fornecedor_legado=fornecedor.nome_fornecedor,
        valor_total=Decimal("30.000000"),
        valor_produtos=Decimal("20.000000"),
    )
    _criar_stg_item(
        compra=compra,
        id_item_legado=97011,
        id_produto_legado=produto.id_produto,
        nome_produto_legado=produto.produto,
        unidade_legado="UN",
        quantidade=Decimal("2.000000"),
        valor_custo=Decimal("10.000000"),
    )

    executar_validacao_compras(reset_tracking=True)
    compra.refresh_from_db()
    assert compra.status_validacao == STG_Compra.STATUS_DIVERGENTE
    assert "divergencia_total_itens" in (compra.snapshot_divergencia.get("motivos") or [])

    resultado_lote = aplicar_tratamento_divergencias_compra_lote(
        compras=[{"id_compra_legado": compra.id_compra_legado}],
        acao="validar",
    )

    compra.refresh_from_db()
    assert resultado_lote["processadas"] == 1
    assert resultado_lote["bloqueadas"] == 0
    assert compra.status_validacao == STG_Compra.STATUS_VALIDADO
    assert compra.status_tratamento == STG_Compra.TRATAMENTO_VALIDADO


@pytest.mark.django_db
def test_consolidacao_permite_validada_com_divergencia_total_itens() -> None:
    unidade = _criar_unidade("UN")
    produto = _criar_produto(7051, "PRODUTO CONSOLIDACAO TOTAL", unidade)
    fornecedor = _criar_fornecedor(7051, "FORNECEDOR CONSOLIDACAO TOTAL")

    compra = _criar_stg_compra(
        id_compra_legado=9751,
        id_fornecedor_legado=fornecedor.id_fornecedor,
        nome_fornecedor_legado=fornecedor.nome_fornecedor,
        valor_total=Decimal("30.000000"),
        valor_produtos=Decimal("20.000000"),
    )
    _criar_stg_item(
        compra=compra,
        id_item_legado=97511,
        id_produto_legado=produto.id_produto,
        nome_produto_legado=produto.produto,
        unidade_legado="UN",
        quantidade=Decimal("2.000000"),
        valor_custo=Decimal("10.000000"),
    )

    executar_validacao_compras(reset_tracking=True)
    compra.refresh_from_db()
    assert compra.status_validacao == STG_Compra.STATUS_DIVERGENTE
    assert "divergencia_total_itens" in (compra.snapshot_divergencia.get("motivos") or [])

    aplicar_tratamento_divergencias_compra_lote(
        compras=[{"id_compra_legado": compra.id_compra_legado}],
        acao="validar",
    )

    compra.refresh_from_db()
    assert compra.status_validacao == STG_Compra.STATUS_VALIDADO
    assert compra.status_tratamento == STG_Compra.TRATAMENTO_VALIDADO

    resultado = consolidar_compras_stg_para_sot()

    assert resultado["compras_inseridas"] == 1
    assert resultado["compras_ignoradas_incompletas"] == 0
    assert Compra.objects.filter(id_legado=compra.id_compra_legado).exists()


@pytest.mark.django_db
def test_validacao_lote_bloqueia_sem_produto_ou_unidade_resolvida() -> None:
    _criar_unidade("UN")
    fornecedor = _criar_fornecedor(7002, "FORNECEDOR BLOQUEIO LOTE")

    compra = _criar_stg_compra(
        id_compra_legado=9702,
        id_fornecedor_legado=fornecedor.id_fornecedor,
        nome_fornecedor_legado=fornecedor.nome_fornecedor,
        valor_total=Decimal("10.000000"),
        valor_produtos=Decimal("10.000000"),
    )
    _criar_stg_item(
        compra=compra,
        id_item_legado=97021,
        id_produto_legado=999991,
        nome_produto_legado="PRODUTO NAO MAPEADO",
        unidade_legado="ZZ",
        quantidade=Decimal("1.000000"),
        valor_custo=Decimal("10.000000"),
    )

    executar_validacao_compras(reset_tracking=True)

    resultado_lote = aplicar_tratamento_divergencias_compra_lote(
        compras=[{"id_compra_legado": compra.id_compra_legado}],
        acao="validar",
    )

    compra.refresh_from_db()
    assert resultado_lote["processadas"] == 0
    assert resultado_lote["bloqueadas"] == 1
    assert resultado_lote["bloqueios"]
    codigos = set(resultado_lote["bloqueios"][0].get("codigos") or [])
    assert "produto_sem_correspondencia" in codigos or "unidade_sem_mapeamento" in codigos
    assert compra.status_validacao == STG_Compra.STATUS_DIVERGENTE


@pytest.mark.django_db
def test_ajuste_manual_persiste_resolucao_fornecedor_produto_unidade() -> None:
    unidade_base = _criar_unidade("UN")
    unidade_resolvida = _criar_unidade("CX")
    produto_resolvido = _criar_produto(7010, "PRODUTO RESOLVIDO MANUAL", unidade_base)
    fornecedor_resolvido = _criar_fornecedor(7010, "FORNECEDOR RESOLVIDO MANUAL")

    compra = _criar_stg_compra(
        id_compra_legado=9801,
        id_fornecedor_legado=999999,
        nome_fornecedor_legado="FORNECEDOR SEM MATCH",
        valor_total=Decimal("15.000000"),
        valor_produtos=Decimal("15.000000"),
    )
    item = _criar_stg_item(
        compra=compra,
        id_item_legado=98011,
        id_produto_legado=999999,
        nome_produto_legado="PRODUTO SEM MATCH",
        unidade_legado="ZZ",
        quantidade=Decimal("1.000000"),
        valor_custo=Decimal("15.000000"),
    )

    executar_validacao_compras(reset_tracking=True)

    aplicar_tratamento_divergencia_compra(
        id_compra_legado=compra.id_compra_legado,
        acao="ajustar",
        payload={
            "fornecedor_resolvido_id": fornecedor_resolvido.id_fornecedor,
            "itens": [
                {
                    "id_stg_item_compra": item.id_stg_item_compra,
                    "produto_resolvido_id": produto_resolvido.id_produto,
                    "unidade_resolvida_id": unidade_resolvida.id_und_medida,
                }
            ],
        },
    )

    compra.refresh_from_db()
    item.refresh_from_db()
    assert compra.fornecedor_resolvido_id == fornecedor_resolvido.id_fornecedor
    assert item.produto_resolvido_id == produto_resolvido.id_produto
    assert item.unidade_resolvida_id == unidade_resolvida.id_und_medida


@pytest.mark.django_db
def test_ajuste_manual_anterior_nao_e_desfeito_apos_novo_ajuste() -> None:
    unidade_base = _criar_unidade("UN")
    unidade_resolvida_1 = _criar_unidade("CX")
    unidade_resolvida_2 = _criar_unidade("PC")

    produto_resolvido_1 = _criar_produto(7101, "PRODUTO RESOLVIDO 1", unidade_base)
    produto_resolvido_2 = _criar_produto(7102, "PRODUTO RESOLVIDO 2", unidade_base)
    fornecedor_resolvido_1 = _criar_fornecedor(7101, "FORNECEDOR RESOLVIDO 1")
    fornecedor_resolvido_2 = _criar_fornecedor(7102, "FORNECEDOR RESOLVIDO 2")

    compra_1 = _criar_stg_compra(
        id_compra_legado=9811,
        id_fornecedor_legado=991111,
        nome_fornecedor_legado="FORNECEDOR SEM MATCH 1",
        valor_total=Decimal("11.000000"),
        valor_produtos=Decimal("11.000000"),
    )
    item_1 = _criar_stg_item(
        compra=compra_1,
        id_item_legado=98111,
        id_produto_legado=991111,
        nome_produto_legado="PRODUTO SEM MATCH 1",
        unidade_legado="ZZ",
        quantidade=Decimal("1.000000"),
        valor_custo=Decimal("11.000000"),
    )

    compra_2 = _criar_stg_compra(
        id_compra_legado=9812,
        id_fornecedor_legado=992222,
        nome_fornecedor_legado="FORNECEDOR SEM MATCH 2",
        valor_total=Decimal("12.000000"),
        valor_produtos=Decimal("12.000000"),
    )
    item_2 = _criar_stg_item(
        compra=compra_2,
        id_item_legado=98121,
        id_produto_legado=992222,
        nome_produto_legado="PRODUTO SEM MATCH 2",
        unidade_legado="YY",
        quantidade=Decimal("1.000000"),
        valor_custo=Decimal("12.000000"),
    )

    executar_validacao_compras(reset_tracking=True)

    aplicar_tratamento_divergencia_compra(
        id_compra_legado=compra_1.id_compra_legado,
        acao="ajustar",
        payload={
            "fornecedor_resolvido_id": fornecedor_resolvido_1.id_fornecedor,
            "itens": [
                {
                    "id_stg_item_compra": item_1.id_stg_item_compra,
                    "produto_resolvido_id": produto_resolvido_1.id_produto,
                    "unidade_resolvida_id": unidade_resolvida_1.id_und_medida,
                }
            ],
        },
    )

    compra_1.refresh_from_db()
    item_1.refresh_from_db()
    assert compra_1.status_validacao == STG_Compra.STATUS_VALIDADO
    assert compra_1.status_tratamento == STG_Compra.TRATAMENTO_VALIDADO
    assert compra_1.fornecedor_resolvido_id == fornecedor_resolvido_1.id_fornecedor
    assert item_1.produto_resolvido_id == produto_resolvido_1.id_produto
    assert item_1.unidade_resolvida_id == unidade_resolvida_1.id_und_medida

    aplicar_tratamento_divergencia_compra(
        id_compra_legado=compra_2.id_compra_legado,
        acao="ajustar",
        payload={
            "fornecedor_resolvido_id": fornecedor_resolvido_2.id_fornecedor,
            "itens": [
                {
                    "id_stg_item_compra": item_2.id_stg_item_compra,
                    "produto_resolvido_id": produto_resolvido_2.id_produto,
                    "unidade_resolvida_id": unidade_resolvida_2.id_und_medida,
                }
            ],
        },
    )

    compra_1.refresh_from_db()
    item_1.refresh_from_db()
    compra_2.refresh_from_db()
    item_2.refresh_from_db()

    assert compra_1.status_validacao == STG_Compra.STATUS_VALIDADO
    assert compra_1.status_tratamento == STG_Compra.TRATAMENTO_VALIDADO
    assert compra_1.fornecedor_resolvido_id == fornecedor_resolvido_1.id_fornecedor
    assert item_1.produto_resolvido_id == produto_resolvido_1.id_produto
    assert item_1.unidade_resolvida_id == unidade_resolvida_1.id_und_medida

    assert compra_2.status_validacao == STG_Compra.STATUS_VALIDADO
    assert compra_2.status_tratamento == STG_Compra.TRATAMENTO_VALIDADO
    assert compra_2.fornecedor_resolvido_id == fornecedor_resolvido_2.id_fornecedor
    assert item_2.produto_resolvido_id == produto_resolvido_2.id_produto
    assert item_2.unidade_resolvida_id == unidade_resolvida_2.id_und_medida
