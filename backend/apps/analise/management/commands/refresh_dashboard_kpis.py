from django.core.management.base import BaseCommand, CommandError

from apps.analise.services import processar_kpis_dashboard


class Command(BaseCommand):
    help = "Recalcula e salva os KPIs do dashboard de vendas (singleton DashboardKpiVenda)."

    def handle(self, *args, **options):
        try:
            processar_kpis_dashboard()
            self.stdout.write(self.style.SUCCESS("KPIs do dashboard atualizados com sucesso."))
        except Exception as exc:
            raise CommandError(f"Falha ao atualizar KPIs: {exc}") from exc
