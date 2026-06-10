from decimal import Decimal

from django.test import TestCase

from apps.validacao.models import STG_ItemVenda, STG_PagamentoVenda, STG_Venda
from apps.validacao.services.auditoria_planilha import executar_tripla_validacao


class TotalItensFallbackTests(TestCase):
    def test_usa_total_de_todos_itens_quando_nao_existem_itens_ativos(self):
        venda = STG_Venda.objects.create(
            tipo_documento="NFCE",
            id_legado=123456,
            status_venda="F",
            data_venda="2026-01-01",
            valor_final=Decimal("19.620000"),
        )

        STG_ItemVenda.objects.create(
            stg_venda=venda,
            tipo_documento="NFCE",
            id_venda_legado=123456,
            status_venda="F",
            data_venda="2026-01-01",
            id_produto_legado=1,
            quantidade=Decimal("1.000000"),
            valor_unitario=Decimal("10.000000"),
            valor_total_calculado=Decimal("10.000000"),
            cancelado=True,
        )
        STG_ItemVenda.objects.create(
            stg_venda=venda,
            tipo_documento="NFCE",
            id_venda_legado=123456,
            status_venda="F",
            data_venda="2026-01-01",
            id_produto_legado=2,
            quantidade=Decimal("1.000000"),
            valor_unitario=Decimal("9.620000"),
            valor_total_calculado=Decimal("9.620000"),
            cancelado=True,
        )

        STG_PagamentoVenda.objects.create(
            stg_venda=venda,
            tipo_documento="NFCE",
            id_venda_legado=123456,
            valor_pago=Decimal("19.620000"),
        )

        executar_tripla_validacao(reset_tracking=False)
        venda.refresh_from_db()

        snapshot = venda.snapshot_divergencia or {}
        self.assertEqual(snapshot.get("total_itens"), "19.620000")
        self.assertIs(snapshot.get("total_itens_via_fallback"), True)
