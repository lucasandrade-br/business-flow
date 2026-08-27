from django.core.management.base import BaseCommand

from apps.analise.services import atualizar_movimento_diario


class Command(BaseCommand):
    help = "Reconsolida o movimento diário de vendas por data e tipo de venda"

    def handle(self, *args, **options):
        atualizar_movimento_diario()
        self.stdout.write(self.style.SUCCESS("Movimento diário reconsolidado com sucesso."))
