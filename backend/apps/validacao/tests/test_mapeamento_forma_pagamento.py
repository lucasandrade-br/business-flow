from decimal import Decimal

from django.test import TestCase

from apps.cadastros.models import FormaPagamento, FormaPagamentoMapeamento
from apps.validacao.models import STG_PagamentoVenda, STG_Venda
from apps.validacao.services.auditoria_planilha import aplicar_tratamento_divergencias_lote


class MapeamentoFormaPagamentoTests(TestCase):
    def test_editar_pagamento_em_lote_resolve_id_origem_por_tipo_documento(self):
        forma = FormaPagamento.objects.create(id_forma=999, descricao="Pix Canonico")
        FormaPagamentoMapeamento.objects.create(
            forma_pagamento=forma,
            tipo_documento="NFCE",
            id_forma_origem=12,
            descricao_origem="PIX NFCe",
        )

        venda = STG_Venda.objects.create(
            tipo_documento="NFCE",
            id_legado=1001,
            status_venda="F",
            data_venda="2026-01-01",
            valor_final=Decimal("100.000000"),
        )
        pagamento = STG_PagamentoVenda.objects.create(
            stg_venda=venda,
            tipo_documento="NFCE",
            id_venda_legado=1001,
            id_tipo_pagamento_legado=1,
            tipo_pagamento_descricao_legado="DINHEIRO",
            valor_pago=Decimal("100.000000"),
        )

        aplicar_tratamento_divergencias_lote(
            vendas=[{"tipo_documento": "NFCE", "id_legado": 1001}],
            acao="editar_pagamento",
            payload={"id_forma": 999},
        )

        pagamento.refresh_from_db()
        self.assertEqual(pagamento.id_tipo_pagamento_legado, 12)
        self.assertEqual(pagamento.tipo_pagamento_descricao_legado, "PIX NFCe")

    def test_editar_pagamento_em_lote_retorna_erro_quando_mapeamento_nao_existe(self):
        FormaPagamento.objects.create(id_forma=777, descricao="Cartao Canonico")
        venda = STG_Venda.objects.create(
            tipo_documento="DAV",
            id_legado=2002,
            status_venda="F",
            data_venda="2026-01-01",
            valor_final=Decimal("50.000000"),
        )
        STG_PagamentoVenda.objects.create(
            stg_venda=venda,
            tipo_documento="DAV",
            id_venda_legado=2002,
            id_tipo_pagamento_legado=5,
            tipo_pagamento_descricao_legado="DINHEIRO",
            valor_pago=Decimal("50.000000"),
        )

        with self.assertRaisesMessage(ValueError, "Nao existe mapeamento"):
            aplicar_tratamento_divergencias_lote(
                vendas=[{"tipo_documento": "DAV", "id_legado": 2002}],
                acao="editar_pagamento",
                payload={"id_forma": 777},
            )
