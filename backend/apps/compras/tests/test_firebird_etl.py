from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from apps.compras.models import STG_ItemCompra
from apps.compras.services.firebird_etl import SQL_ITENS_COMPRA, sincronizar_compras_legado


@pytest.mark.django_db
@override_settings(FDB_PATH="compras.fdb", FDB_HOST="", FDB_PORT="", FDB_CLIENT_LIB_PATH="")
def test_importacao_usa_total_item_do_firebird_sem_recalcular() -> None:
    cursor = MagicMock()
    cursor.fetchall.side_effect = [
        [
            (1, 10, 20, "Fornecedor", date(2026, 1, 10), None, Decimal("9.50"), Decimal("9.50"), "")
        ],
        [
            (2, 1, 30, "Produto", Decimal("2"), Decimal("5"), Decimal("9.50"), "UN", "", "")
        ],
    ]
    conexao = MagicMock()
    conexao.cursor.return_value = cursor

    with patch("apps.compras.services.firebird_etl.fdb.connect", return_value=conexao) as conectar:
        resultado = sincronizar_compras_legado(date(2026, 1, 10), date(2026, 1, 10))

    item = STG_ItemCompra.objects.get(id_item_legado=2)
    assert resultado["totais"] == {"compras": 1, "itens": 1}
    assert item.quantidade == Decimal("2")
    assert item.valor_custo == Decimal("5")
    assert item.valor_total_legado == Decimal("9.50")
    assert item.valor_total_calculado is None
    assert conectar.call_args.kwargs["utf8params"] is True
    assert "NCD.TOTAL_ITEM AS VALOR_TOTAL" in SQL_ITENS_COMPRA
    assert "COALESCE(NCD.QUANTIDADE" not in SQL_ITENS_COMPRA
