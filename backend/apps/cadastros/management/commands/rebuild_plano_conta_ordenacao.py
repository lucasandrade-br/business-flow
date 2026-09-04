from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.cadastros.models import PlanoConta


class Command(BaseCommand):
    help = "Recalcula codigo_ordenacao de todas as contas do plano de contas."

    def handle(self, *args, **options):
        lote: list[PlanoConta] = []
        atualizados = 0

        for conta in PlanoConta.objects.all().only("id_conta", "codigo_hierarquico", "codigo_ordenacao").iterator(chunk_size=1000):
            novo = PlanoConta.build_codigo_ordenacao(conta.codigo_hierarquico)
            if novo == conta.codigo_ordenacao:
                continue
            conta.codigo_ordenacao = novo
            lote.append(conta)
            if len(lote) >= 1000:
                PlanoConta.objects.bulk_update(lote, ["codigo_ordenacao"])
                atualizados += len(lote)
                lote = []

        if lote:
            PlanoConta.objects.bulk_update(lote, ["codigo_ordenacao"])
            atualizados += len(lote)

        self.stdout.write(self.style.SUCCESS(f"codigo_ordenacao recalculado para {atualizados} conta(s)."))
