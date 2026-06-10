from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.cadastros.models import Cliente, FormaPagamento, Produto, UnidadeMedida, Usuario
from apps.vendas.models import ItemVenda, PagamentoVenda, Venda


@pytest.mark.django_db
def test_vendas_list_filters_por_produto_forma_cliente_e_periodo() -> None:
	unidade = UnidadeMedida.objects.create(sigla="UN", descricao="Unidade")
	produto_1 = Produto.objects.create(
		id_produto=100,
		gtin="",
		barras="",
		produto="Produto 100",
		id_und_medida=unidade,
		custo=Decimal("1"),
		venda=Decimal("2"),
		status="ATIVO",
		markup=Decimal("0"),
		markup_inv=Decimal("0"),
		perda=Decimal("0"),
		fisico=Decimal("0"),
		aliqefc="",
		cod_g3n=0,
		cod_rel=0,
		usuario="",
	)
	produto_2 = Produto.objects.create(
		id_produto=200,
		gtin="",
		barras="",
		produto="Produto 200",
		id_und_medida=unidade,
		custo=Decimal("1"),
		venda=Decimal("2"),
		status="ATIVO",
		markup=Decimal("0"),
		markup_inv=Decimal("0"),
		perda=Decimal("0"),
		fisico=Decimal("0"),
		aliqefc="",
		cod_g3n=0,
		cod_rel=0,
		usuario="",
	)

	cliente_1 = Cliente.objects.create(id_cliente=1, nome_cliente="Cliente A", raz_social="", prazo_cob=0)
	cliente_2 = Cliente.objects.create(id_cliente=2, nome_cliente="Cliente B", raz_social="", prazo_cob=0)
	usuario = Usuario.objects.create(id_usuario=9, nome="Operador")

	forma_1 = FormaPagamento.objects.create(id_forma=10, descricao="Dinheiro")
	forma_2 = FormaPagamento.objects.create(id_forma=20, descricao="Cartao")

	venda_1 = Venda.objects.create(
		id_legado=9001,
		tipo_documento="NFCE",
		data_venda=date(2026, 1, 10),
		status="F",
		cliente=cliente_1,
		usuario=usuario,
		valor_total_documento=Decimal("30"),
	)
	venda_2 = Venda.objects.create(
		id_legado=9002,
		tipo_documento="DAV",
		data_venda=date(2026, 2, 10),
		status="F",
		cliente=cliente_2,
		usuario=usuario,
		valor_total_documento=Decimal("40"),
	)

	ItemVenda.objects.create(
		venda=venda_1,
		produto=produto_1,
		unidade_medida=unidade,
		quantidade=Decimal("10"),
		valor_unitario=Decimal("3"),
		valor_total_item=Decimal("30"),
		cancelado=False,
	)
	ItemVenda.objects.create(
		venda=venda_2,
		produto=produto_2,
		unidade_medida=unidade,
		quantidade=Decimal("20"),
		valor_unitario=Decimal("2"),
		valor_total_item=Decimal("40"),
		cancelado=False,
	)

	PagamentoVenda.objects.create(venda=venda_1, forma_pagamento=forma_1, valor_pago=Decimal("30"), estorno=False)
	PagamentoVenda.objects.create(venda=venda_2, forma_pagamento=forma_2, valor_pago=Decimal("40"), estorno=False)

	client = APIClient()
	response = client.get(
		"/api/vendas/vendas",
		{
			"produto_id": produto_1.id_produto,
			"forma_pagamento_id": forma_1.id_forma,
			"cliente_id": cliente_1.id_cliente,
			"data_inicial": "2026-01-01",
			"data_final": "2026-01-31",
		},
		HTTP_HOST="localhost",
	)

	assert response.status_code == 200
	assert response.data["count"] == 1
	assert response.data["results"][0]["id_venda"] == venda_1.id_venda


@pytest.mark.django_db
def test_venda_detail_retorna_itens_e_pagamentos() -> None:
	unidade = UnidadeMedida.objects.create(sigla="UN", descricao="Unidade")
	produto = Produto.objects.create(
		id_produto=300,
		gtin="",
		barras="",
		produto="Produto 300",
		id_und_medida=unidade,
		custo=Decimal("1"),
		venda=Decimal("2"),
		status="ATIVO",
		markup=Decimal("0"),
		markup_inv=Decimal("0"),
		perda=Decimal("0"),
		fisico=Decimal("0"),
		aliqefc="",
		cod_g3n=0,
		cod_rel=0,
		usuario="",
	)
	cliente = Cliente.objects.create(id_cliente=3, nome_cliente="Cliente C", raz_social="", prazo_cob=0)
	usuario = Usuario.objects.create(id_usuario=10, nome="Caixa")
	forma = FormaPagamento.objects.create(id_forma=30, descricao="PIX")

	venda = Venda.objects.create(
		id_legado=9999,
		tipo_documento="NFCE",
		data_venda=date(2026, 3, 1),
		status="F",
		cliente=cliente,
		usuario=usuario,
		valor_total_documento=Decimal("15"),
	)

	ItemVenda.objects.create(
		venda=venda,
		produto=produto,
		unidade_medida=unidade,
		quantidade=Decimal("3"),
		valor_unitario=Decimal("5"),
		valor_total_item=Decimal("15"),
		cancelado=False,
	)
	PagamentoVenda.objects.create(venda=venda, forma_pagamento=forma, valor_pago=Decimal("15"), estorno=False)

	client = APIClient()
	response = client.get(f"/api/vendas/vendas/{venda.id_venda}", HTTP_HOST="localhost")

	assert response.status_code == 200
	assert response.data["id_venda"] == venda.id_venda
	assert len(response.data["itens"]) == 1
	assert len(response.data["pagamentos"]) == 1
	assert response.data["itens"][0]["produto_nome"] == "Produto 300"
	assert response.data["pagamentos"][0]["forma_pagamento_descricao"] == "PIX"
