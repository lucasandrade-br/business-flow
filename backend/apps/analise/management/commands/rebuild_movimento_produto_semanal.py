from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.analise.services_vendas_semanais import reconstruir_movimentos_produto_semanais


class Command(BaseCommand):
    help = "Reconstrói os agregados diário e semanal de vendas por produto."

    def add_arguments(self, parser):
        parser.add_argument("--inicio", type=date.fromisoformat, help="Data inicial AAAA-MM-DD.")
        parser.add_argument("--fim", type=date.fromisoformat, help="Data final AAAA-MM-DD.")
        parser.add_argument("--somente-pendentes", action="store_true", help="Ignora semanas já prontas.")

    def handle(self, *args, **options):
        try:
            resultado = reconstruir_movimentos_produto_semanais(
                inicio=options["inicio"], fim=options["fim"],
                somente_pendentes=options["somente_pendentes"],
            )
        except Exception as exc:
            raise CommandError(f"Falha ao reconstruir agregado semanal: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(
            f"Agregado semanal reconstruído: {resultado['periodos_processados']} semana(s), "
            f"{resultado['linhas_geradas']} linha(s)."
        ))
