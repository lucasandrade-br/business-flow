from django.core.management.base import BaseCommand

from apps.analise.services import processar_kpis_compras


class Command(BaseCommand):
    help = "Consolida KPIs de compras no modelo DashboardKpiCompra"

    def handle(self, *args, **options):
        processar_kpis_compras()
        self.stdout.write(self.style.SUCCESS("KPIs de compras atualizados com sucesso."))
