from django.core.management.base import BaseCommand

from apps.analise.services import atualizar_dre_consolidada


class Command(BaseCommand):
    help = "Reconsolida a tabela DRE mensal agregando vendas e compras por ano/mês"

    def handle(self, *args, **options):
        atualizar_dre_consolidada()
        self.stdout.write(self.style.SUCCESS("DRE mensal reconsolidada com sucesso."))
