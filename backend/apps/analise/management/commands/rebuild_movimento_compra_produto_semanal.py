from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.analise.services_compras_periodos import reconstruir_movimentos_compra_produto_semanais


class Command(BaseCommand):
    help = "Reconstrói o histórico semanal e diário de compras da filial atual, inclusive semanas zeradas."

    def add_arguments(self, parser):
        parser.add_argument("--inicio", type=date.fromisoformat)
        parser.add_argument("--fim", type=date.fromisoformat)
        parser.add_argument("--somente-pendentes", action="store_true")

    def handle(self, *args, **options):
        try:
            resultado = reconstruir_movimentos_compra_produto_semanais(
                inicio=options["inicio"], fim=options["fim"],
                somente_pendentes=options["somente_pendentes"],
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"Compras: {resultado['periodos_processados']} semana(s), {resultado['linhas_geradas']} linha(s)."
        ))
