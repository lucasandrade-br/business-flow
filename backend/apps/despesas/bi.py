"""BI de despesas a partir dos agregados persistidos e dos vínculos atuais."""

import calendar
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    AgregadoDespesaDiario, AgregadoDespesaMensal, CategoriaDespesa,
    SnapshotDespesaMensal, VinculoTipoDespesa,
)


ZERO = Decimal("0")


def _mes(ano, numero):
    return date(ano, numero, 1)


def _fim_mes(ano, numero):
    return date(ano, numero, calendar.monthrange(ano, numero)[1])


def _corte_ano(ano, hoje):
    return date(ano, hoje.month, min(hoje.day, calendar.monthrange(ano, hoje.month)[1]))


def _estado(snapshot, diario=False):
    if snapshot is None:
        return "AUSENTE"
    if snapshot.status != "PRONTO":
        return snapshot.status
    if diario and snapshot.diario_atualizado_em is None:
        return "DIARIO_AUSENTE"
    return "PRONTO"


def _percentual(atual, anterior):
    if atual is None or anterior is None or anterior == ZERO:
        return None
    return str(((atual - anterior) * 100 / anterior).quantize(Decimal("0.01")))


def _historica(valores):
    if len(valores) < 3:
        return None
    taxas = []
    for indice in range(1, len(valores) - 1):
        anterior, atual = valores[indice - 1:indice + 1]
        if anterior is None or atual is None or anterior == ZERO:
            return None
        taxas.append((atual - anterior) * 100 / anterior)
    return str((sum(taxas, ZERO) / len(taxas)).quantize(Decimal("0.01")))


def _familia(params):
    familia_id = params.get("familia_id")
    if familia_id:
        familia = CategoriaDespesa.objects.filter(pk=familia_id, pai__isnull=True).first()
    else:
        familia = CategoriaDespesa.objects.filter(pai__isnull=True, nome__iexact="DESPESAS").order_by("id").first()
        if not familia:
            familia = CategoriaDespesa.objects.filter(pai__isnull=True).order_by("id").first()
    if not familia:
        raise ValidationError("Família inexistente ou nenhuma família cadastrada.")
    return familia


def _periodo_mensal(ano, numero, base, hoje, equivalente, snapshots):
    inicio, fim = _mes(ano, numero), _fim_mes(ano, numero)
    posicao = "ENCERRADO" if fim < hoje else "FUTURO" if inicio > hoje else "CORRENTE"
    # Pagamentos com data futura nunca entram no fluxo realizado, mesmo com o controle desligado.
    diario = (equivalente and posicao != "FUTURO") or (base == "PAGAMENTO" and posicao == "CORRENTE")
    corte = date(ano, numero, min(hoje.day, fim.day)) if diario else fim
    snapshot = snapshots.get(inicio)
    situacao = _estado(snapshot, diario)
    futuro_pagamento = base == "PAGAMENTO" and posicao == "FUTURO"
    valido = situacao == "PRONTO" and not futuro_pagamento
    estado = (
        "FUTURO" if futuro_pagamento else
        "PARCIAL" if valido and posicao == "CORRENTE" else
        "PRONTO" if valido else
        situacao if situacao in {"AUSENTE", "FALHO", "PENDENTE"} else "INDISPONIVEL"
    )
    return {
        "periodo": inicio.isoformat(), "estado": estado,
        "estado_snapshot": situacao, "posicao_calendario": posicao,
        "inicio": inicio.isoformat(), "fim": fim.isoformat(),
        "data_corte": corte.isoformat() if diario else None,
        "fim_efetivo": corte.isoformat() if valido else None,
        "programado": base == "VENCIMENTO" and posicao == "FUTURO",
        "inclui_programado": base == "VENCIMENTO" and posicao == "CORRENTE" and not diario,
        "meses_carregados": int(bool(snapshot and snapshot.status == "PRONTO")),
        "meses_indisponiveis": [inicio.isoformat()] if not valido and not futuro_pagamento else [],
        "motivo_indisponibilidade": situacao if not valido and not futuro_pagamento else None,
        "atualizado_em": snapshot.atualizado_em if snapshot else None,
        "_valido": valido, "_metodo": "DIARIO" if diario else "MENSAL",
        "_inicio": inicio, "_fim": corte, "_meses": [inicio] if valido else [],
    }


def _periodo_anual(ano, base, hoje, equivalente, snapshots):
    inicio, fim = date(ano, 1, 1), date(ano, 12, 31)
    posicao = "ENCERRADO" if ano < hoje.year else "FUTURO" if ano > hoje.year else "CORRENTE"
    meses = [_mes(ano, numero) for numero in range(1, 13)]
    diario = equivalente and posicao != "FUTURO"
    hibrido = base == "PAGAMENTO" and posicao == "CORRENTE" and not diario
    corte = _corte_ano(ano, hoje) if diario else fim
    if diario:
        requeridos = meses[:corte.month]
    elif posicao == "ENCERRADO":
        requeridos = meses
    elif posicao == "CORRENTE":
        requeridos = meses[:hoje.month]
    else:
        requeridos = []
    situacoes = {
        mes: _estado(snapshots.get(mes), diario or (hibrido and mes.month == hoje.month))
        for mes in meses
    }
    faltantes = [mes for mes in requeridos if situacoes[mes] != "PRONTO"]
    futuro_pagamento = base == "PAGAMENTO" and posicao == "FUTURO"
    if diario:
        usados = requeridos if not faltantes else []
        metodo = "DIARIO"
    elif hibrido:
        usados = requeridos[:-1] if not faltantes else []
        metodo = "HIBRIDO"
    else:
        usados = [mes for mes in meses if situacoes[mes] == "PRONTO"]
        metodo = "MENSAL"
    valido = not futuro_pagamento and not faltantes and (bool(usados) or hibrido and bool(requeridos))
    considerados = requeridos if diario or hibrido or posicao == "ENCERRADO" else meses
    indisponiveis = [mes for mes in considerados if situacoes[mes] != "PRONTO"]
    if futuro_pagamento:
        estado = "FUTURO"
    elif not valido:
        estado = "INDISPONIVEL"
    elif posicao == "CORRENTE" or indisponiveis:
        estado = "PARCIAL"
    else:
        estado = "PRONTO"
    situacao = next((situacoes[mes] for mes in requeridos if situacoes[mes] != "PRONTO"), None)
    if situacao is None:
        situacao = "INCOMPLETO" if indisponiveis else "PRONTO"
    atualizado = max(
        (snapshots[mes].atualizado_em for mes in meses if mes in snapshots and snapshots[mes].atualizado_em),
        default=None,
    )
    return {
        "periodo": str(ano), "estado": estado,
        "estado_snapshot": situacao, "posicao_calendario": posicao,
        "inicio": inicio.isoformat(), "fim": fim.isoformat(),
        "data_corte": corte.isoformat() if diario else hoje.isoformat() if posicao == "CORRENTE" else None,
        "fim_efetivo": corte.isoformat() if valido and diario else hoje.isoformat() if valido and hibrido else fim.isoformat() if valido else None,
        "programado": base == "VENCIMENTO" and posicao == "FUTURO",
        "inclui_programado": base == "VENCIMENTO" and posicao == "CORRENTE" and not diario,
        "meses_carregados": sum(bool(snapshots.get(mes) and snapshots[mes].status == "PRONTO") for mes in meses),
        "meses_indisponiveis": [mes.isoformat() for mes in indisponiveis],
        "motivo_indisponibilidade": situacao if not valido and not futuro_pagamento else None,
        "atualizado_em": atualizado,
        "_valido": valido, "_metodo": metodo,
        "_inicio": inicio if diario else _mes(ano, hoje.month) if hibrido else inicio,
        "_fim": corte if diario else hoje if hibrido else fim,
        "_meses": usados if valido else [],
    }


def _somar_periodo(periodo, mensais, diarios):
    totais = defaultdict(Decimal)
    if not periodo["_valido"]:
        return totais
    if periodo["_metodo"] in {"MENSAL", "HIBRIDO"}:
        for mes in periodo["_meses"]:
            for tipo_id, valor in mensais.get(mes, {}).items():
                totais[tipo_id] += valor
    if periodo["_metodo"] in {"DIARIO", "HIBRIDO"}:
        for dia, tipos in diarios.items():
            if periodo["_inicio"] <= dia <= periodo["_fim"]:
                for tipo_id, valor in tipos.items():
                    totais[tipo_id] += valor
    return totais


def _intervalos_detalhe(periodo):
    """Datas efetivamente somadas na célula, inclusive anos com meses faltantes."""
    if not periodo["_valido"]:
        return []
    intervalos = []
    if periodo["_metodo"] in {"MENSAL", "HIBRIDO"}:
        intervalos.extend({"inicio": mes.isoformat(), "fim": _fim_mes(mes.year, mes.month).isoformat()} for mes in periodo["_meses"])
    if periodo["_metodo"] in {"DIARIO", "HIBRIDO"}:
        intervalos.append({"inicio": periodo["_inicio"].isoformat(), "fim": periodo["_fim"].isoformat()})
    return intervalos


def _valores_futuros(ano, base, hoje, mensais, diarios, snapshots):
    """Separa obrigações programadas de pagamentos futuros anômalos."""
    totais = defaultdict(Decimal)
    if ano < hoje.year:
        return totais, False, False
    primeiro = 1 if ano > hoje.year else hoje.month + 1
    meses = [_mes(ano, numero) for numero in range(primeiro, 13)]
    incompleto = any(_estado(snapshots.get(mes)) != "PRONTO" for mes in meses)
    conhecido = False
    for mes in meses:
        if _estado(snapshots.get(mes)) == "PRONTO":
            conhecido = True
            for tipo_id, valor in mensais.get(mes, {}).items():
                totais[tipo_id] += valor
    if ano == hoje.year:
        mes_atual = _mes(ano, hoje.month)
        if _estado(snapshots.get(mes_atual), True) == "PRONTO":
            conhecido = True
            if base == "VENCIMENTO":
                ate_hoje = defaultdict(Decimal)
                for dia, tipos in diarios.items():
                    if mes_atual <= dia <= hoje:
                        for tipo_id, valor in tipos.items():
                            ate_hoje[tipo_id] += valor
                for tipo_id, valor in mensais.get(mes_atual, {}).items():
                    totais[tipo_id] += valor - ate_hoje[tipo_id]
            else:
                for dia, tipos in diarios.items():
                    if hoje < dia <= _fim_mes(ano, hoje.month):
                        for tipo_id, valor in tipos.items():
                            totais[tipo_id] += valor
        else:
            incompleto = True
    return totais, incompleto, conhecido


def _serializar_linha(valores, periodos, visao, ano, hoje, equivalente, futuros, futuros_incompletos, futuros_conhecidos, base):
    chaves = [periodo["periodo"] for periodo in periodos]
    resultado = {"valores": {chave: str(valores[chave]) if valores[chave] is not None else None for chave in chaves}}
    if visao == "mensal":
        somaveis = [p for p in periodos if p["posicao_calendario"] != "FUTURO" or (not equivalente and p["programado"])]
        encontrados = [valores[p["periodo"]] for p in somaveis if valores[p["periodo"]] is not None]
        incompleto = len(encontrados) != len(somaveis)
        resultado.update({
            "total": None if incompleto else str(sum(encontrados, ZERO)),
            "total_conhecido": str(sum(encontrados, ZERO)),
            "total_incompleto": incompleto,
            "total_rotulo": "Total comparável" if equivalente else "Total conhecido (inclui programado)" if base == "VENCIMENTO" and any(p["programado"] for p in periodos) else "Total",
        })
    else:
        serie = [valores[chave] for chave in chaves]
        foco_futuro = ano > hoje.year
        resultado.update({
            "variacao_historica_percentual": None if foco_futuro else _historica(serie),
            "variacao_percentual": None if foco_futuro or len(serie) < 2 else _percentual(serie[-1], serie[-2]),
            "variacao_recente_neutra": ano == hoje.year and not equivalente,
            "anos_variacao_historica": [[int(chaves[i - 1]), int(chaves[i])] for i in range(1, len(chaves) - 1)],
            "anos_variacao_recente": [int(chaves[-2]), int(chaves[-1])] if len(chaves) >= 2 else [],
        })
    nome_futuro = "programado_apos_corte" if base == "VENCIMENTO" else "pagamentos_futuros_registrados"
    resultado[nome_futuro] = str(futuros) if futuros_conhecidos else None
    resultado["programado_incompleto" if base == "VENCIMENTO" else "pagamentos_futuros_incompletos"] = futuros_incompletos
    return resultado


def obter_bi(params):
    visao = params.get("visao", "mensal")
    base = str(params.get("base", "VENCIMENTO")).upper()
    if visao not in {"mensal", "anual"} or base not in {"VENCIMENTO", "PAGAMENTO"}:
        raise ValidationError("Visão ou base inválida.")
    hoje = timezone.localdate()
    try:
        ano = int(params.get("ano") or hoje.year)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Ano inválido.") from exc
    if not 1900 <= ano <= 2200:
        raise ValidationError("Ano fora do intervalo permitido.")
    equivalente_param = str(params.get("periodo_equivalente", "0"))
    if equivalente_param not in {"0", "1"}:
        raise ValidationError("Períodos equivalentes deve ser 1 ou 0.")
    familia = _familia(params)
    equivalente = equivalente_param == "1" and ano == hoje.year
    anos_disponiveis = sorted(set(SnapshotDespesaMensal.objects.filter(base=base).values_list("mes__year", flat=True)))
    if visao == "mensal":
        anos = [ano]
    else:
        anteriores = [valor for valor in anos_disponiveis if valor <= ano]
        primeiro = max(ano - 3, min(anteriores)) if anteriores else ano
        anos = list(range(primeiro, ano + 1))
    snapshots = {
        item.mes: item for item in SnapshotDespesaMensal.objects.filter(
            base=base, mes__year__gte=anos[0], mes__year__lte=anos[-1],
        )
    }
    periodos = (
        [_periodo_mensal(ano, numero, base, hoje, equivalente, snapshots) for numero in range(1, 13)]
        if visao == "mensal" else
        [_periodo_anual(valor, base, hoje, equivalente, snapshots) for valor in anos]
    )
    mensais = defaultdict(dict)
    for item in AgregadoDespesaMensal.objects.filter(base=base, mes__year__gte=anos[0], mes__year__lte=anos[-1]).values("mes", "tipo_id", "valor").iterator():
        mensais[item["mes"]][item["tipo_id"]] = item["valor"]
    diarios = defaultdict(dict)
    if equivalente or hoje.year in anos:
        inicio_diario = date(anos[0], 1, 1) if equivalente else _mes(hoje.year, hoje.month)
        fim_diario = _fim_mes(hoje.year, hoje.month) if hoje.year in anos else hoje
        for item in AgregadoDespesaDiario.objects.filter(base=base, dia__gte=inicio_diario, dia__lte=fim_diario).values("dia", "tipo_id", "valor").iterator():
            diarios[item["dia"]][item["tipo_id"]] = item["valor"]
    valores_periodo = {item["periodo"]: _somar_periodo(item, mensais, diarios) for item in periodos}
    futuros, futuros_incompletos, futuros_conhecidos = _valores_futuros(ano, base, hoje, mensais, diarios, snapshots)

    nos = list(CategoriaDespesa.objects.filter(caminho__startswith=familia.caminho + "\x1f").order_by("caminho"))
    nos.insert(0, familia)
    por_id = {no.pk: no for no in nos}
    pais = {no.pai_id for no in nos if no.pai_id in por_id}
    folhas = {no.pk for no in nos if no.pk not in pais and no.pk != familia.pk}
    vinculos = list(VinculoTipoDespesa.objects.filter(familia=familia).select_related("tipo"))
    folha_por_tipo = {v.tipo_id: v.folha_id for v in vinculos if v.folha_id in folhas}
    tipo_nomes = {v.tipo_id: v.tipo.nome for v in vinculos}
    invalidos = {v.tipo_id for v in vinculos if v.folha_id not in folhas}
    relevantes = set(futuros)
    for valores in valores_periodo.values():
        relevantes.update(valores)
    nao_vinculados = sorted(relevantes - folha_por_tipo.keys())
    invalidos = sorted(invalidos.intersection(relevantes))
    valores_nos = defaultdict(lambda: defaultdict(Decimal))
    futuros_nos = defaultdict(Decimal)
    for tipo_id, folha_id in folha_por_tipo.items():
        atual = por_id[folha_id]
        while atual:
            for periodo, valores in valores_periodo.items():
                valores_nos[atual.pk][periodo] += valores.get(tipo_id, ZERO)
            futuros_nos[atual.pk] += futuros.get(tipo_id, ZERO)
            atual = por_id.get(atual.pai_id)

    def linha(tipo_id=None, no_id=None):
        valores = {
            periodo["periodo"]: (
                None if not periodo["_valido"] else
                valores_periodo[periodo["periodo"]].get(tipo_id, ZERO) if tipo_id is not None else
                valores_nos[no_id][periodo["periodo"]]
            ) for periodo in periodos
        }
        valor_futuro = futuros.get(tipo_id, ZERO) if tipo_id is not None else futuros_nos[no_id]
        return _serializar_linha(
            valores, periodos, visao, ano, hoje, equivalente,
            valor_futuro, futuros_incompletos, futuros_conhecidos, base,
        )

    tipos = [
        {"id": tipo_id, "nome": tipo_nomes[tipo_id], "folha_id": folha_id, **linha(tipo_id=tipo_id)}
        for tipo_id, folha_id in sorted(folha_por_tipo.items(), key=lambda item: (tipo_nomes[item[0]].casefold(), item[0]))
    ]
    categorias = [
        {"id": no.pk, "nome": no.nome, "pai_id": no.pai_id, "nivel": no.nivel,
         "folha": no.pk not in pais, **linha(no_id=no.pk)}
        for no in nos
    ]
    nao_classificados_valores = {
        periodo["periodo"]: None if not periodo["_valido"] else
        sum((valores_periodo[periodo["periodo"]].get(tipo_id, ZERO) for tipo_id in nao_vinculados), ZERO)
        for periodo in periodos
    }
    nao_classificados = {
        "tipos_ids": nao_vinculados, "quantidade_tipos": len(nao_vinculados),
        "tipos_com_vinculo_invalido": invalidos,
        **_serializar_linha(
            nao_classificados_valores, periodos, visao, ano, hoje, equivalente,
            sum((futuros.get(tipo_id, ZERO) for tipo_id in nao_vinculados), ZERO),
            futuros_incompletos, futuros_conhecidos, base,
        ),
    }
    periodos_publicos = [
        {**{chave: valor for chave, valor in item.items() if not chave.startswith("_")},
         "intervalos_detalhe": _intervalos_detalhe(item)}
        for item in periodos
    ]
    indisponiveis = [p for p in periodos_publicos if p["estado"] not in {"PRONTO", "PARCIAL", "FUTURO"}]
    desatualizados = [p for p in indisponiveis if p["estado_snapshot"] in {"FALHO", "PENDENTE", "DESATUALIZADO"}]
    atualizado = max((p["atualizado_em"] for p in periodos_publicos if p["atualizado_em"]), default=None)
    estado_atualizacao = (
        "SEM_HISTORICO" if not snapshots else
        "DESATUALIZADO" if desatualizados else
        "INCOMPLETO" if indisponiveis else "PRONTO"
    )
    return {
        "familia": {"id": familia.pk, "nome": familia.nome},
        "visao": visao, "base": base, "ano": ano,
        "anos_disponiveis": anos_disponiveis,
        "periodos": periodos_publicos, "categorias": categorias, "tipos": tipos,
        "tipos_sem_vinculo": nao_vinculados,
        "nao_classificados": nao_classificados,
        "periodo_equivalente": equivalente,
        "periodo_equivalente_solicitado": equivalente_param == "1",
        "data_corte": hoje.isoformat() if equivalente else None,
        "mes_aberto": ano == hoje.year and visao == "mensal" and hoje < _fim_mes(ano, hoje.month),
        "ano_parcial": ano == hoje.year and visao == "anual" and hoje < date(ano, 12, 31),
        "fonte_atualizada_em": None, "cobertura_fonte_ate": None,
        "atualizado_em": atualizado, "estado_atualizacao": estado_atualizacao,
        "desatualizado": bool(desatualizados),
        "periodos_desatualizados": [p["periodo"] for p in desatualizados],
        "periodos_indisponiveis": [p["periodo"] for p in indisponiveis],
        "programado_incompleto" if base == "VENCIMENTO" else "pagamentos_futuros_incompletos": futuros_incompletos,
    }
