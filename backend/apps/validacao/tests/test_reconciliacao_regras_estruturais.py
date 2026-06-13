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
from apps.validacao.models import STG_AuditoriaPlanilha, STG_ItemVenda, STG_PagamentoVenda, STG_Venda
from apps.validacao.services.auditoria_planilha import (
    aplicar_tratamento_divergencia,
    aplicar_tratamento_divergencias_lote,
    consolidar_stg_para_sot,
)


def _seed_base(tipo_documento: str = "NFCE") -> tuple[Usuario, Cliente, UnidadeMedida, Produto, FormaPagamento]:
    usuario = Usuario.objects.get_or_create(
        id_usuario=7,
        defaults={"nome": "Operador QA"},
    )[0]
    cliente = Cliente.objects.get_or_create(
        id_cliente=777,
        defaults={
            "nome_cliente": "Cliente QA",
            "raz_social": "Cliente QA LTDA",
            "prazo_cob": 0,
            "cliente_padrao": False,
        },
    )[0]
    unidade = UnidadeMedida.objects.get_or_create(sigla="UN", defaults={"descricao": "Unidade"})[0]
    produto = Produto.objects.get_or_create(
        id_produto=707,
        defaults={
            "gtin": "",
            "barras": "",
            "produto": "Produto QA",
            "id_und_medida": unidade,
            "custo": Decimal("10.000000"),
            "venda": Decimal("12.000000"),
            "status": "ATIVO",
            "markup": Decimal("0.0000"),
            "markup_inv": Decimal("0.0000"),
            "perda": Decimal("0.0000"),
            "fisico": Decimal("0.0000"),
            "aliqefc": "",
            "cod_g3n": 0,
            "cod_rel": 0,
            "usuario": "",
        },
    )[0]
    forma = FormaPagamento.objects.get_or_create(id_forma=70, defaults={"descricao": "Dinheiro"})[0]
    FormaPagamentoOrigem.objects.get_or_create(
        tipo_documento=tipo_documento,
        id_forma_origem=1,
        defaults={
            "descricao_origem": "Dinheiro",
            "ativo": True,
        },
    )
    FormaPagamentoMapeamento.objects.get_or_create(
        forma_pagamento=forma,
        tipo_documento=tipo_documento,
        id_forma_origem=1,
        defaults={
            "descricao_origem": "Dinheiro",
            "ativo": True,
        },
    )
    return usuario, cliente, unidade, produto, forma


def _seed_venda(
    *,
    id_legado: int,
    tipo_documento: str = "NFCE",
    total_documento: str = "100.000000",
    total_item: str = "100.000000",
    total_pagamento: str = "100.000000",
    pagamento_auditoria: str = "Dinheiro",
    pagamento_stg: str = "Dinheiro",
    criar_item: bool = True,
    status_validacao: str = STG_Venda.STATUS_DIVERGENTE,
    status_tratamento: str = STG_Venda.TRATAMENTO_PENDENTE,
) -> STG_Venda:
    usuario, cliente, _, produto, _ = _seed_base(tipo_documento)

    venda = STG_Venda.objects.create(
        tipo_documento=tipo_documento,
        id_legado=id_legado,
        status_venda="F",
        data_venda=date(2026, 2, 1),
        id_cliente_legado=cliente.id_cliente,
        nome_cliente_legado=cliente.nome_cliente,
        id_usuario_legado=usuario.id_usuario,
        nome_usuario_legado=usuario.nome,
        valor_final=Decimal(total_documento),
        status_validacao=status_validacao,
        status_tratamento=status_tratamento,
    )

    if criar_item:
        STG_ItemVenda.objects.create(
            stg_venda=venda,
            tipo_documento=tipo_documento,
            id_venda_legado=id_legado,
            status_venda="F",
            data_venda=venda.data_venda,
            id_cliente_legado=cliente.id_cliente,
            nome_cliente_legado=cliente.nome_cliente,
            id_produto_legado=produto.id_produto,
            nome_produto_legado=produto.produto,
            unidade_comercial_legado="UN",
            valor_unitario=Decimal(total_item),
            quantidade=Decimal("1.000000"),
            valor_total_calculado=Decimal(total_item),
            cancelado=False,
        )

    STG_PagamentoVenda.objects.create(
        stg_venda=venda,
        tipo_documento=tipo_documento,
        id_venda_legado=id_legado,
        id_tipo_pagamento_legado=1,
        tipo_pagamento_descricao_legado=pagamento_stg,
        valor_pago=Decimal(total_pagamento),
        estorno=False,
    )

    STG_AuditoriaPlanilha.objects.create(
        tipo_documento=tipo_documento,
        id_legado=id_legado,
        data_venda=venda.data_venda,
        hora_venda=venda.hora_venda,
        usuario_nome=usuario.nome,
        cliente_nome=cliente.nome_cliente,
        valor_total=Decimal(total_documento),
        tipo_pagamento_descricao=pagamento_auditoria,
    )

    return venda


@pytest.mark.django_db
def test_validar_bloqueia_venda_sem_itens() -> None:
    venda = _seed_venda(id_legado=90001, criar_item=False)

    with pytest.raises(ValueError, match="Validacao bloqueada"):
        aplicar_tratamento_divergencia(
            tipo_documento=venda.tipo_documento,
            id_legado=venda.id_legado,
            acao="validar",
            payload={},
        )


@pytest.mark.django_db
def test_validar_lote_nao_valida_venda_sem_itens() -> None:
    venda_ok = _seed_venda(id_legado=90002, criar_item=True)
    venda_sem_item = _seed_venda(id_legado=90003, criar_item=False)

    resultado = aplicar_tratamento_divergencias_lote(
        vendas=[
            {"tipo_documento": venda_ok.tipo_documento, "id_legado": venda_ok.id_legado},
            {"tipo_documento": venda_sem_item.tipo_documento, "id_legado": venda_sem_item.id_legado},
        ],
        acao="validar",
        payload={},
    )

    assert resultado["processadas"] == 1
    assert resultado["bloqueadas"] == 1
    assert len(resultado["bloqueios"]) == 1
    assert resultado["bloqueios"][0]["venda"] == f"{venda_sem_item.tipo_documento} #{int(venda_sem_item.id_legado):06d}"


@pytest.mark.django_db
def test_consolidacao_permite_divergencia_totais() -> None:
    venda = _seed_venda(
        id_legado=90004,
        total_documento="100.000000",
        total_item="80.000000",
        total_pagamento="100.000000",
        status_validacao=STG_Venda.STATUS_APROVADO,
        status_tratamento=STG_Venda.TRATAMENTO_VALIDADO,
    )

    # Simula snapshot informativo de divergencia de totais em venda apta estruturalmente.
    venda.snapshot_divergencia = {
        "motivos": ["divergencia_totais"],
        "total_documento": "100.000000",
        "total_itens": "80.000000",
        "total_pagamentos": "100.000000",
    }
    venda.save(update_fields=["snapshot_divergencia"])

    resultado = consolidar_stg_para_sot()
    assert resultado["vendas_inseridas"] == 1


@pytest.mark.django_db
def test_consolidacao_bloqueia_divergencia_formato() -> None:
    venda = _seed_venda(
        id_legado=90005,
        pagamento_auditoria="Cartao",
        pagamento_stg="Dinheiro",
    )

    venda.status_validacao = STG_Venda.STATUS_DIVERGENTE
    venda.status_tratamento = STG_Venda.TRATAMENTO_VALIDADO
    venda.snapshot_divergencia = {
        "motivos": ["divergencia_formato"],
        "formato_venda": ["DINHEIRO"],
        "formato_auditoria": ["CARTAO"],
    }
    venda.save(update_fields=["status_validacao", "status_tratamento", "snapshot_divergencia"])

    with pytest.raises(ValueError, match="divergencias estruturais"):
        consolidar_stg_para_sot()


@pytest.mark.django_db
def test_validar_permite_override_divergencia_formato() -> None:
    venda = _seed_venda(
        id_legado=90006,
        pagamento_auditoria="Cartao",
        pagamento_stg="Dinheiro",
    )

    venda.snapshot_divergencia = {
        "motivos": ["divergencia_formato"],
        "formato_venda": ["DINHEIRO"],
        "formato_auditoria": ["CARTAO"],
    }
    venda.save(update_fields=["snapshot_divergencia"])

    aplicar_tratamento_divergencia(
        tipo_documento=venda.tipo_documento,
        id_legado=venda.id_legado,
        acao="validar",
        payload={"forcar_divergencia_formato": True},
    )

    venda.refresh_from_db()
    assert venda.status_validacao == STG_Venda.STATUS_APROVADO
    assert venda.status_tratamento == STG_Venda.TRATAMENTO_VALIDADO


@pytest.mark.django_db
def test_consolidacao_permite_override_divergencia_formato() -> None:
    venda = _seed_venda(
        id_legado=90007,
        pagamento_auditoria="Cartao",
        pagamento_stg="Dinheiro",
        status_validacao=STG_Venda.STATUS_DIVERGENTE,
        status_tratamento=STG_Venda.TRATAMENTO_PENDENTE,
    )

    venda.snapshot_divergencia = {
        "motivos": ["divergencia_formato"],
        "formato_venda": ["DINHEIRO"],
        "formato_auditoria": ["CARTAO"],
    }
    venda.save(update_fields=["snapshot_divergencia"])

    resultado = consolidar_stg_para_sot(forcar_divergencia_formato=True)
    assert resultado["vendas_inseridas"] == 1
