from django.core.management.base import BaseCommand, CommandError

from apps.analise.services import atualizar_dre_consolidada


class Command(BaseCommand):
    help = "Reconstrói os agregados diário e mensal do DRE; usa BUSINESS_FILIAL para escolher a base."

    def add_arguments(self, parser):
        parser.add_argument("--somente-pendentes", action="store_true", help="Reconstrói apenas meses sem snapshot pronto ou com falha.")

    def handle(self, *args, **options):
        resultado = atualizar_dre_consolidada(somente_pendentes=options["somente_pendentes"])
        if resultado["falhas"]:
            raise CommandError(f"DRE com {len(resultado['falhas'])} mês(es) com falha; consulte status_dre_consolidada.")
        self.stdout.write(self.style.SUCCESS(f"DRE diário e mensal: {resultado['processados']} mês(es) reconsolidados."))
