from django.core.management.base import BaseCommand, CommandError

from apps.analise.services import reconstruir_movimentos_compra_produto_mensal


class Command(BaseCommand):
    help = "Reconstrói o agregado mensal de compras por produto, fornecedor e unidade."

    def add_arguments(self, parser):
        parser.add_argument("--ano", type=int, help="Reconstrói somente o ano informado.")
        parser.add_argument("--mes", type=int, help="Reconstrói somente o mês informado; requer --ano.")

    def handle(self, *args, **options):
        try:
            resultado = reconstruir_movimentos_compra_produto_mensal(
                ano=options.get("ano"),
                mes=options.get("mes"),
            )
        except Exception as exc:
            raise CommandError(f"Falha ao reconstruir o agregado de compras: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Agregado de compras reconstruído: {resultado['periodos_processados']} período(s), "
                f"{resultado['linhas_geradas']} linha(s)."
            )
        )
