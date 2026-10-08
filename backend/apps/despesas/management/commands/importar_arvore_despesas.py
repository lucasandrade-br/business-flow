from django.core.management.base import BaseCommand, CommandError

from apps.despesas.services import importar_arvores


class Command(BaseCommand):
    help = "Importa as famílias SETORES e IMPORTÂNCIAS a partir de duas planilhas."

    def add_arguments(self, parser):
        parser.add_argument("arquivo_setores", help="Planilha com MACROGRUPO e GRUPO GERENCIAL")
        parser.add_argument("arquivo_importancias", help="Planilha com Etiqueta de Eficiência e Tipo Financeiro")

    def handle(self, *args, **options):
        try:
            resultado = importar_arvores(
                options["arquivo_setores"],
                options["arquivo_importancias"],
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(str(resultado)))
