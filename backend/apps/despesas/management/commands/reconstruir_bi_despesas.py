from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Min, Max, Sum

from apps.despesas.models import (
    AgregadoDespesaDiario, AgregadoDespesaMensal, MovimentoDespesa,
    PagamentoDespesa, SnapshotDespesaMensal,
)
from apps.despesas.services import mes_inicio, proximo_mes, reconstruir_mes


class Command(BaseCommand):
    help = "Reconstrói os agregados diários e mensais da filial, incluindo meses vazios entre os extremos carregados."

    def add_arguments(self, parser):
        parser.add_argument("--inicio", help="YYYY-MM; exige --fim")
        parser.add_argument("--fim", help="YYYY-MM; exige --inicio")
        parser.add_argument("--somente-sem-diario", action="store_true", help="Retoma a carga sem refazer meses com diário pronto.")
        parser.add_argument("--conferir", action="store_true", help="Somente lê e concilia diário e mensal; não reconstrói.")

    def handle(self, *args, **options):
        inicio = options["inicio"]
        fim = options["fim"]
        if bool(inicio) != bool(fim):
            raise CommandError("Informe --inicio e --fim juntos.")
        if options["somente_sem_diario"] and options["conferir"]:
            raise CommandError("Use --somente-sem-diario ou --conferir, não ambos.")
        limites = {}
        if inicio:
            try:
                primeiro = date.fromisoformat(inicio + "-01")
                ultimo = date.fromisoformat(fim + "-01")
            except ValueError as exc:
                raise CommandError("Use datas válidas no formato YYYY-MM.") from exc
            if primeiro > ultimo:
                raise CommandError("--inicio não pode ser posterior a --fim.")
            limites = {"VENCIMENTO": (primeiro, ultimo), "PAGAMENTO": (primeiro, ultimo)}
        else:
            for base, model, campo in (("VENCIMENTO", MovimentoDespesa, "vencimento"), ("PAGAMENTO", PagamentoDespesa, "data")):
                dados = model.objects.aggregate(inicio=Min(campo), fim=Max(campo))
                snapshots = SnapshotDespesaMensal.objects.filter(base=base).aggregate(inicio=Min("mes"), fim=Max("mes"))
                inicios = [mes_inicio(valor) for valor in (dados["inicio"], snapshots["inicio"]) if valor]
                fins = [mes_inicio(valor) for valor in (dados["fim"], snapshots["fim"]) if valor]
                if inicios:
                    limites[base] = (min(inicios), max(fins))
        total = 0
        ignorados = 0
        divergencias = []
        for base, (primeiro, ultimo) in limites.items():
            atual = primeiro
            while atual <= ultimo:
                snapshot = SnapshotDespesaMensal.objects.filter(mes=atual, base=base).first()
                if options["conferir"]:
                    diario = dict(
                        AgregadoDespesaDiario.objects.filter(dia__gte=atual, dia__lt=proximo_mes(atual), base=base)
                        .values("tipo_id").annotate(total=Sum("valor")).values_list("tipo_id", "total")
                    )
                    mensal = dict(AgregadoDespesaMensal.objects.filter(mes=atual, base=base).values_list("tipo_id", "valor"))
                    if not snapshot or snapshot.status != "PRONTO" or not snapshot.diario_atualizado_em or diario != mensal:
                        divergencias.append(f"{base} {atual:%Y-%m}")
                    else:
                        total += 1
                elif options["somente_sem_diario"] and snapshot and snapshot.status == "PRONTO" and snapshot.diario_atualizado_em:
                    ignorados += 1
                else:
                    reconstruir_mes(atual, base)
                    total += 1
                atual = proximo_mes(atual)
        if divergencias:
            raise CommandError(f"{len(divergencias)} períodos sem diário pronto ou não conciliados: {', '.join(divergencias[:10])}")
        if options["conferir"]:
            self.stdout.write(self.style.SUCCESS(f"{total} períodos com diário e mensal conciliados."))
        else:
            self.stdout.write(self.style.SUCCESS(f"{total} períodos reconstruídos; {ignorados} já tinham diário pronto."))
