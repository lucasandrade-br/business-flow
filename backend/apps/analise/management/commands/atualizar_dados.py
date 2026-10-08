from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


COMANDOS_ATUALIZACAO = (
    ("refresh_dashboard_kpis", {}),
    ("refresh_dashboard_kpis_compras", {}),
    ("refresh_dre_consolidada", {"somente_pendentes": True}),
    ("refresh_movimento_diario", {}),
    ("rebuild_movimento_produto_mensal", {}),
    ("rebuild_movimento_produto_semanal", {"somente_pendentes": True}),
    ("rebuild_movimento_compra_produto_mensal", {"somente_pendentes": True}),
    ("rebuild_movimento_compra_produto_semanal", {"somente_pendentes": True}),
    ("reconstruir_bi_despesas", {}),
)


class Command(BaseCommand):
    help = "Executa a sequência completa de atualização de dados para a filial selecionada."

    def handle(self, *args, **options):
        total = len(COMANDOS_ATUALIZACAO)
        for indice, (nome, argumentos) in enumerate(COMANDOS_ATUALIZACAO, start=1):
            self.stdout.write(f"[{indice}/{total}] Executando {nome}...")
            try:
                call_command(
                    nome,
                    **argumentos,
                    stdout=self.stdout,
                    stderr=self.stderr,
                )
            except CommandError as exc:
                raise CommandError(f"Falha em {nome}: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("Atualização completa dos dados concluída."))
