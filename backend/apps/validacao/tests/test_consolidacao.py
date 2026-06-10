from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.cadastros.models import (
    Cliente,
    FormaPagamento,
    FormaPagamentoMapeamento,
    FormaPagamentoOrigem,
    Produto,
    UnidadeMedida,
    Usuario,
)
from apps.integracao.models import StgClientesNovos
from apps.validacao.models import STG_AuditoriaPlanilha, STG_ItemVenda, STG_PagamentoVenda, STG_Venda
from apps.validacao.services.auditoria_planilha import consolidar_stg_para_sot
from apps.vendas.models import ItemVenda, PagamentoVenda, Venda



def _criar_produto(id_produto: int, unidade: UnidadeMedida) -> Produto:
    return Produto.objects.create(
        id_produto=id_produto,
        gtin="",
        barras="",
        produto="Produto Teste",
        id_und_medida=unidade,
        custo=Decimal("10.000000"),
        venda=Decimal("12.000000"),
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


@pytest.mark.django_db
def test_consolidacao_mapeia_cliente_padrao_e_persiste_campos_novos() -> None:
    unidade = UnidadeMedida.objects.create(sigla="UN", descricao="Unidade")
    _criar_produto(101, unidade)

    usuario = Usuario.objects.create(id_usuario=5, nome="Operador Principal")
    cliente_padrao = Cliente.objects.create(
        id_cliente=245,
        nome_cliente="Consumidor Padrao",
        raz_social="",
        prazo_cob=0,
        cliente_padrao=True,
    )

    forma = FormaPagamento.objects.create(id_forma=10, descricao="Dinheiro")
    FormaPagamentoOrigem.objects.create(
        tipo_documento="NFCE",
        id_forma_origem=1,
        descricao_origem="Dinheiro",
        ativo=True,
    )
    FormaPagamentoMapeamento.objects.create(
        forma_pagamento=forma,
        tipo_documento="NFCE",
        id_forma_origem=1,
        descricao_origem="Dinheiro",
        ativo=True,
    )

    venda_stg = STG_Venda.objects.create(
        tipo_documento="NFCE",
        id_legado=9001,
        status_venda="F",
        data_venda=date(2026, 1, 10),
        id_cliente_legado=0,
        nome_cliente_legado="Consumidor Geral",
        id_usuario_legado=usuario.id_usuario,
        nome_usuario_legado=usuario.nome,
        valor_final=Decimal("100.000000"),
        status_validacao=STG_Venda.STATUS_APROVADO,
        status_tratamento=STG_Venda.TRATAMENTO_VALIDADO,
    )

    STG_ItemVenda.objects.create(
        stg_venda=venda_stg,
        tipo_documento="NFCE",
        id_venda_legado=venda_stg.id_legado,
        status_venda="F",
        data_venda=venda_stg.data_venda,
        id_cliente_legado=0,
        nome_cliente_legado="Consumidor Geral",
        id_produto_legado=101,
        nome_produto_legado="Produto Teste",
        unidade_comercial_legado="UN",
        valor_unitario=Decimal("10.000000"),
        quantidade=Decimal("10.000000"),
        valor_total_calculado=Decimal("100.000000"),
        cancelado=False,
    )

    STG_PagamentoVenda.objects.create(
        stg_venda=venda_stg,
        tipo_documento="NFCE",
        id_venda_legado=venda_stg.id_legado,
        id_tipo_pagamento_legado=1,
        tipo_pagamento_descricao_legado="Dinheiro",
        valor_pago=Decimal("100.000000"),
        estorno=True,
    )

    STG_AuditoriaPlanilha.objects.create(
        tipo_documento="NFCE",
        id_legado=venda_stg.id_legado,
        data_venda=venda_stg.data_venda,
        hora_venda=venda_stg.hora_venda,
        usuario_nome=usuario.nome,
        cliente_nome="Consumidor Geral",
        valor_total=Decimal("100.000000"),
        tipo_pagamento_descricao="Dinheiro",
    )

    resultado = consolidar_stg_para_sot()

    assert resultado["vendas_inseridas"] == 1
    assert resultado["vendas_ignoradas_duplicadas"] == 0

    venda = Venda.objects.get(id_legado=9001, tipo_documento="NFCE")
    assert venda.cliente_id == cliente_padrao.id_cliente
    assert venda.status == "F"
    assert venda.momento_consolidacao is not None

    item = ItemVenda.objects.get(venda=venda)
    assert item.unidade_medida_id == unidade.id_und_medida

    pagamento = PagamentoVenda.objects.get(venda=venda)
    assert pagamento.forma_pagamento_id == forma.id_forma
    assert pagamento.estorno is True

    assert STG_Venda.objects.count() == 0
    assert STG_ItemVenda.objects.count() == 0
    assert STG_PagamentoVenda.objects.count() == 0
    assert STG_AuditoriaPlanilha.objects.count() == 0


@pytest.mark.django_db
def test_consolidacao_bloqueia_cliente_legado_zero_sem_cliente_padrao() -> None:
    unidade = UnidadeMedida.objects.create(sigla="UN", descricao="Unidade")
    _criar_produto(101, unidade)

    usuario = Usuario.objects.create(id_usuario=5, nome="Operador Principal")

    forma = FormaPagamento.objects.create(id_forma=10, descricao="Dinheiro")
    FormaPagamentoOrigem.objects.create(
        tipo_documento="NFCE",
        id_forma_origem=1,
        descricao_origem="Dinheiro",
        ativo=True,
    )
    FormaPagamentoMapeamento.objects.create(
        forma_pagamento=forma,
        tipo_documento="NFCE",
        id_forma_origem=1,
        descricao_origem="Dinheiro",
        ativo=True,
    )

    venda_stg = STG_Venda.objects.create(
        tipo_documento="NFCE",
        id_legado=9002,
        status_venda="F",
        data_venda=date(2026, 1, 11),
        id_cliente_legado=0,
        nome_cliente_legado="Consumidor Geral",
        id_usuario_legado=usuario.id_usuario,
        nome_usuario_legado=usuario.nome,
        valor_final=Decimal("50.000000"),
        status_validacao=STG_Venda.STATUS_APROVADO,
        status_tratamento=STG_Venda.TRATAMENTO_VALIDADO,
    )

    STG_ItemVenda.objects.create(
        stg_venda=venda_stg,
        tipo_documento="NFCE",
        id_venda_legado=venda_stg.id_legado,
        status_venda="F",
        data_venda=venda_stg.data_venda,
        id_cliente_legado=0,
        nome_cliente_legado="Consumidor Geral",
        id_produto_legado=101,
        nome_produto_legado="Produto Teste",
        unidade_comercial_legado="UN",
        valor_unitario=Decimal("5.000000"),
        quantidade=Decimal("10.000000"),
        valor_total_calculado=Decimal("50.000000"),
        cancelado=False,
    )

    STG_PagamentoVenda.objects.create(
        stg_venda=venda_stg,
        tipo_documento="NFCE",
        id_venda_legado=venda_stg.id_legado,
        id_tipo_pagamento_legado=1,
        tipo_pagamento_descricao_legado="Dinheiro",
        valor_pago=Decimal("50.000000"),
        estorno=False,
    )

    with pytest.raises(ValueError, match="cliente_legado_zero_sem_cliente_padrao_configurado"):
        consolidar_stg_para_sot()


@pytest.mark.django_db
def test_consolidacao_bloqueia_quando_existem_pendencias_de_cadastro() -> None:
    StgClientesNovos.objects.create(id_cliente=1, cliente="Cliente Pendente")

    with pytest.raises(ValueError, match="pendencias de cadastro"):
        consolidar_stg_para_sot()
