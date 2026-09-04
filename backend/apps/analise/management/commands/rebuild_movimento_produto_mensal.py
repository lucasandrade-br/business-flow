from django.core.management.base import BaseCommand, CommandError

from apps.analise.services import reconstruir_movimentos_produto_mensal


class Command(BaseCommand):
    help = "Reconstrói o agregado mensal de vendas por produto usado na análise por categorias."

    def add_arguments(self, parser):
        parser.add_argument("--ano", type=int, help="Reconstrói somente o ano informado.")

    def handle(self, *args, **options):
        try:
            resultado = reconstruir_movimentos_produto_mensal(ano=options.get("ano"))
        except Exception as exc:
            raise CommandError(f"Falha ao reconstruir o agregado: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Agregado reconstruído: {resultado['periodos_processados']} período(s), "
                f"{resultado['linhas_geradas']} linha(s)."
            )
        )
