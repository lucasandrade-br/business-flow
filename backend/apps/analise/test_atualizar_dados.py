from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class AtualizarDadosCommandTests(SimpleTestCase):
    @patch("apps.analise.management.commands.atualizar_dados.call_command")
    def test_executa_sequencia_completa_incluindo_despesas(self, executar_comando):
        saida = StringIO()
        erros = StringIO()
        call_command("atualizar_dados", stdout=saida, stderr=erros)

        self.assertEqual(
            [chamada.args[0] for chamada in executar_comando.call_args_list],
            [
                "refresh_dashboard_kpis",
                "refresh_dashboard_kpis_compras",
                "refresh_dre_consolidada",
                "refresh_movimento_diario",
                "rebuild_movimento_produto_mensal",
                "rebuild_movimento_produto_semanal",
                "rebuild_movimento_compra_produto_mensal",
                "rebuild_movimento_compra_produto_semanal",
                "reconstruir_bi_despesas",
            ],
        )
        self.assertTrue(executar_comando.call_args_list[2].kwargs["somente_pendentes"])
        self.assertTrue(executar_comando.call_args_list[5].kwargs["somente_pendentes"])
        self.assertIs(
            executar_comando.call_args_list[-1].kwargs["stdout"],
            executar_comando.call_args_list[0].kwargs["stdout"],
        )
        self.assertIs(
            executar_comando.call_args_list[-1].kwargs["stderr"],
            executar_comando.call_args_list[0].kwargs["stderr"],
        )

    @patch(
        "apps.analise.management.commands.atualizar_dados.call_command",
        side_effect=CommandError("erro simulado"),
    )
    def test_falha_interrompe_a_sequencia_com_contexto(self, executar_comando):
        with self.assertRaisesMessage(
            CommandError,
            "Falha em refresh_dashboard_kpis: erro simulado",
        ):
            call_command("atualizar_dados", stdout=StringIO())

        executar_comando.assert_called_once()
