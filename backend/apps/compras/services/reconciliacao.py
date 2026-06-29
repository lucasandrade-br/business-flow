from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from decimal import Decimal, InvalidOperation
from typing import Any
import unicodedata

from django.db import transaction
from django.db.models import Max, Min, Sum
from django.utils import timezone

from apps.cadastros.models import Fornecedor, Produto, UnidadeMedida
from apps.compras.models import Compra, ItemCompra, STG_Compra, STG_ItemCompra
DECIMAL_TOLERANCIA_TOTAL = Decimal("0.5")
LIMIAR_SEMELHANCA_FORNECEDOR = 0.8
LIMIAR_SEMELHANCA_PRODUTO = 0.8

MOTIVOS_DIVERGENCIA_VALIDOS = {
    "duplicado_sot",
    "compra_sem_itens",
    "fornecedor_sem_correspondencia",
    "produto_sem_correspondencia",
    "unidade_sem_mapeamento",
    "divergencia_total_itens",
    "valor_negativo_bloqueado",
}

MOTIVOS_DIVERGENCIA_NAO_BLOQUEANTES_CONSOLIDACAO = {
    "duplicado_sot",
    "divergencia_total_itens",
}

MOTIVOS_DIVERGENCIA_NAO_BLOQUEANTES_VALIDACAO_MANUAL = {
    "duplicado_sot",
    "divergencia_total_itens",
}

UNIDADE_ALIAS: dict[str, str] = {
    "UND": "UN",
    "UNID": "UN",
    "UNIDADE": "UN",
    "LITRO": "LT",
    "LITROS": "LT",
    "LTS": "LT",
    "KILO": "KG",
    "KILOGRAMA": "KG",
    "KILOGRAMAS": "KG",
    "GRAMA": "G",
    "GRAMAS": "G",
}


@dataclass
class ValidationResultCompras:
    compras_aprovadas: int
    compras_divergentes: int
    compras_duplicadas_sot: int
    divergencias: list[dict[str, Any]]
    inconsistencias: list[dict[str, Any]]
    kpis: dict[str, Any]
    pode_aprovar: bool


@dataclass(frozen=True)
class _EntityCandidate:
    entity_id: int
    nome: str
    nome_norm: str
    nome_tokens_sorted: str
    obj: Any


class ReconciliacaoCompraBloqueioError(ValueError):
    def __init__(
        self,
        detail: str,
        *,
        codigo: str,
        bloqueios: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.codigo = codigo
        self.bloqueios = bloqueios or []

    def to_payload(self) -> dict[str, Any]:
        return {
            "detail": self.detail,
            "codigo": self.codigo,
            "bloqueios": self.bloqueios,
            "permite_override": False,
        }


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_identity_text(value: Any) -> str:
    raw = _normalize_text(value)
    if not raw:
        return ""
    normalized = unicodedata.normalize("NFKD", raw)
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(without_accents.upper().split())


def _normalize_unit_token(value: Any) -> str:
    text = _normalize_identity_text(value)
    return "".join(ch for ch in text if ch.isalnum())


def _sort_name_tokens(value: str) -> str:
    if not value:
        return ""
    return " ".join(sorted(token for token in value.split(" ") if token))


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _status_validacao_validada_values(model_cls: Any) -> list[str]:
    return [
        str(getattr(model_cls, "STATUS_VALIDADO", "VALIDADO")),
        str(getattr(model_cls, "STATUS_APROVADO_LEGADO", "APROVADO")),
    ]


def _normalizar_status_validacao_legado() -> None:
    STG_Compra.objects.filter(status_validacao=STG_Compra.STATUS_APROVADO_LEGADO).update(
        status_validacao=STG_Compra.STATUS_VALIDADO
    )
    STG_ItemCompra.objects.filter(status_validacao=STG_ItemCompra.STATUS_APROVADO_LEGADO).update(
        status_validacao=STG_ItemCompra.STATUS_VALIDADO
    )


def _garantir_validacao_materializada() -> None:
    _normalizar_status_validacao_legado()

    base_qs = STG_Compra.objects.all()
    if not base_qs.exists():
        return

    possui_pendentes = base_qs.filter(status_validacao=STG_Compra.STATUS_PENDENTE).exists()
    if not possui_pendentes:
        return

    possui_processados = base_qs.filter(
        status_validacao__in=[
            STG_Compra.STATUS_DIVERGENTE,
            *_status_validacao_validada_values(STG_Compra),
        ]
    ).exists()
    if not possui_processados:
        executar_validacao_compras(reset_tracking=False)


def _is_negative(value: Any) -> bool:
    decimal_value = _to_decimal(value)
    return bool(decimal_value is not None and decimal_value < 0)


def _sum_total_itens(itens: list[STG_ItemCompra]) -> Decimal:
    total = Decimal("0")
    for item in itens:
        if item.valor_total_calculado is not None:
            total += item.valor_total_calculado
            continue
        if item.valor_total_legado is not None:
            total += item.valor_total_legado
            continue

        quantidade = item.quantidade or Decimal("0")
        valor_custo = item.valor_custo or Decimal("0")
        total += quantidade * valor_custo
    return total


def _motivos_snapshot_compra(compra: STG_Compra) -> set[str]:
    snapshot = compra.snapshot_divergencia or {}
    motivos_raw = snapshot.get("motivos") or []
    return {
        _normalize_text(item).lower()
        for item in motivos_raw
        if _normalize_text(item)
    }


def _motivos_bloqueantes_consolidacao(compra: STG_Compra) -> set[str]:
    return _motivos_snapshot_compra(compra) - MOTIVOS_DIVERGENCIA_NAO_BLOQUEANTES_CONSOLIDACAO


def _motivos_bloqueantes_validacao_manual(compra: STG_Compra) -> set[str]:
    return _motivos_snapshot_compra(compra) - MOTIVOS_DIVERGENCIA_NAO_BLOQUEANTES_VALIDACAO_MANUAL


def _resolver_unidade_legado(
    *,
    unidade_legado: str,
    unidades_por_sigla: dict[str, UnidadeMedida],
) -> UnidadeMedida | None:
    token = _normalize_unit_token(unidade_legado)
    if not token:
        return None

    unidade = unidades_por_sigla.get(token)
    if unidade is not None:
        return unidade

    alias = UNIDADE_ALIAS.get(token)
    if alias:
        return unidades_por_sigla.get(alias)
    return None


def _match_by_similarity_first(
    *,
    nome_legado: Any,
    id_legado: Any,
    candidates: list[_EntityCandidate],
    by_id: dict[int, Any],
    limiar: float,
    ordenar_tokens: bool = False,
) -> tuple[Any | None, float, str]:
    nome_norm = _normalize_identity_text(nome_legado)
    nome_comparacao = _sort_name_tokens(nome_norm) if ordenar_tokens else nome_norm
    best_candidate: _EntityCandidate | None = None
    best_score = 0.0

    id_norm = _to_int(id_legado)

    # Fast path: if legacy id already maps to a highly similar candidate, skip full scan.
    if id_norm is not None and id_norm in by_id:
        candidate_by_id = by_id[id_norm]
        nome_id = _normalize_identity_text(
            getattr(candidate_by_id, "nome_fornecedor", None) or getattr(candidate_by_id, "produto", None)
        )
        nome_id_comparacao = _sort_name_tokens(nome_id) if ordenar_tokens else nome_id

        if not nome_comparacao:
            return candidate_by_id, 1.0, "id_apoio"

        if nome_id_comparacao:
            score_id = SequenceMatcher(None, nome_comparacao, nome_id_comparacao).ratio()
            if score_id >= limiar:
                return candidate_by_id, score_id, "id_apoio"

    if nome_comparacao:
        for candidate in candidates:
            candidate_nome = candidate.nome_tokens_sorted if ordenar_tokens else candidate.nome_norm
            if not candidate_nome:
                continue

            if candidate_nome == nome_comparacao:
                return candidate.obj, 1.0, "nome_exato"

            score = SequenceMatcher(None, nome_comparacao, candidate_nome).ratio()
            if score > best_score:
                best_score = score
                best_candidate = candidate

        if best_candidate is not None and best_score >= limiar:
            return best_candidate.obj, best_score, "similaridade"

    if id_norm is not None and id_norm in by_id:
        return by_id[id_norm], best_score, "id_apoio"

    return None, best_score, "nenhum"


def _build_catalogos_correspondencia() -> dict[str, Any]:
    fornecedores = list(Fornecedor.objects.all().only("id_fornecedor", "nome_fornecedor"))
    produtos = list(Produto.objects.all().only("id_produto", "produto"))

    fornecedor_candidates = [
        _EntityCandidate(
            entity_id=int(item.id_fornecedor),
            nome=item.nome_fornecedor,
            nome_norm=_normalize_identity_text(item.nome_fornecedor),
            nome_tokens_sorted=_sort_name_tokens(_normalize_identity_text(item.nome_fornecedor)),
            obj=item,
        )
        for item in fornecedores
    ]
    produto_candidates = [
        _EntityCandidate(
            entity_id=int(item.id_produto),
            nome=item.produto,
            nome_norm=_normalize_identity_text(item.produto),
            nome_tokens_sorted=_sort_name_tokens(_normalize_identity_text(item.produto)),
            obj=item,
        )
        for item in produtos
    ]

    fornecedores_por_id = {int(item.id_fornecedor): item for item in fornecedores}
    produtos_por_id = {int(item.id_produto): item for item in produtos}

    unidades_por_sigla: dict[str, UnidadeMedida] = {}
    for unidade in UnidadeMedida.objects.all().only("id_und_medida", "sigla"):
        token = _normalize_unit_token(unidade.sigla)
        if token:
            unidades_por_sigla[token] = unidade

    return {
        "fornecedor_candidates": fornecedor_candidates,
        "produto_candidates": produto_candidates,
        "fornecedores_por_id": fornecedores_por_id,
        "produtos_por_id": produtos_por_id,
        "unidades_por_sigla": unidades_por_sigla,
    }


def _build_snapshot_compra(
    *,
    compra: STG_Compra,
    motivos: list[str],
    total_itens: Decimal,
    fornecedor_resolvido: Fornecedor | None,
    fornecedor_similaridade: float,
    fornecedor_estrategia: str,
) -> dict[str, Any]:
    valor_total = compra.valor_total or Decimal("0")
    diferenca = valor_total - total_itens
    return {
        "motivos": sorted(set(motivos)),
        "total_compra": str(valor_total),
        "total_itens": str(total_itens),
        "diferenca_total": str(diferenca),
        "id_fornecedor_legado": compra.id_fornecedor_legado,
        "nome_fornecedor_legado": compra.nome_fornecedor_legado,
        "fornecedor_resolvido_id": int(fornecedor_resolvido.id_fornecedor) if fornecedor_resolvido else None,
        "fornecedor_resolvido_nome": fornecedor_resolvido.nome_fornecedor if fornecedor_resolvido else "",
        "fornecedor_match_similaridade": round(fornecedor_similaridade, 4),
        "fornecedor_match_estrategia": fornecedor_estrategia,
    }


def executar_validacao_compras(reset_tracking: bool = False) -> ValidationResultCompras:
    if reset_tracking:
        STG_Compra.objects.update(
            validacao_override=False,
            status_tratamento=STG_Compra.TRATAMENTO_PENDENTE,
            snapshot_divergencia={},
            tratamento_atualizado_em=None,
        )

    compras = list(STG_Compra.objects.prefetch_related("itens").all().order_by("data_emissao", "id_compra_legado"))
    if not compras:
        kpis_vazios = {
            "total_compras_stg": 0,
            "compras_aprovadas": 0,
            "compras_divergentes": 0,
            "compras_duplicadas_sot": 0,
            "motivos_divergencia": {},
            "soma_valor_stg": "0",
            "soma_valor_aprovadas": "0",
            "periodo_data_inicial": None,
            "periodo_data_final": None,
        }
        return ValidationResultCompras(
            compras_aprovadas=0,
            compras_divergentes=0,
            compras_duplicadas_sot=0,
            divergencias=[],
            inconsistencias=[],
            kpis=kpis_vazios,
            pode_aprovar=False,
        )

    catalogos = _build_catalogos_correspondencia()
    fornecedor_candidates = catalogos["fornecedor_candidates"]
    produto_candidates = catalogos["produto_candidates"]
    fornecedores_por_id = catalogos["fornecedores_por_id"]
    produtos_por_id = catalogos["produtos_por_id"]
    unidades_por_sigla = catalogos["unidades_por_sigla"]

    existentes_sot = {int(item) for item in Compra.objects.values_list("id_legado", flat=True)}

    compras_aprovadas = 0
    compras_divergentes = 0
    compras_duplicadas_sot = 0
    soma_valor_aprovadas = Decimal("0")
    divergencias: list[dict[str, Any]] = []
    inconsistencias: list[dict[str, Any]] = []
    motivos_count: dict[str, int] = {motivo: 0 for motivo in sorted(MOTIVOS_DIVERGENCIA_VALIDOS)}
    fornecedor_match_cache: dict[tuple[str, int | None], tuple[Fornecedor | None, float, str]] = {}
    produto_match_cache: dict[tuple[str, int | None], tuple[Produto | None, float, str]] = {}

    itens_to_update: list[STG_ItemCompra] = []

    for compra in compras:
        itens = list(compra.itens.all())
        total_itens = _sum_total_itens(itens)
        valor_total_compra = compra.valor_total or Decimal("0")
        usar_resolucao_manual = compra.status_tratamento in {
            STG_Compra.TRATAMENTO_AJUSTADO,
            STG_Compra.TRATAMENTO_VALIDADO,
        }

        if usar_resolucao_manual and compra.fornecedor_resolvido_id:
            fornecedor_match = compra.fornecedor_resolvido
            fornecedor_similaridade = 1.0
            fornecedor_estrategia = "manual"
        else:
            fornecedor_match_key = (
                _normalize_identity_text(compra.nome_fornecedor_legado),
                _to_int(compra.id_fornecedor_legado),
            )
            fornecedor_match, fornecedor_similaridade, fornecedor_estrategia = fornecedor_match_cache.get(
                fornecedor_match_key,
                (None, 0.0, "nenhum"),
            )
            if fornecedor_match_key not in fornecedor_match_cache:
                fornecedor_match, fornecedor_similaridade, fornecedor_estrategia = _match_by_similarity_first(
                    nome_legado=compra.nome_fornecedor_legado,
                    id_legado=compra.id_fornecedor_legado,
                    candidates=fornecedor_candidates,
                    by_id=fornecedores_por_id,
                    limiar=LIMIAR_SEMELHANCA_FORNECEDOR,
                    ordenar_tokens=False,
                )
                fornecedor_match_cache[fornecedor_match_key] = (
                    fornecedor_match,
                    fornecedor_similaridade,
                    fornecedor_estrategia,
                )

        compra.fornecedor_resolvido = fornecedor_match
        motivos: list[str] = []

        if int(compra.id_compra_legado) in existentes_sot:
            motivos.append("duplicado_sot")
            compras_duplicadas_sot += 1

        if fornecedor_match is None:
            motivos.append("fornecedor_sem_correspondencia")

        if _is_negative(compra.valor_total) or _is_negative(compra.valor_produtos):
            motivos.append("valor_negativo_bloqueado")

        if not itens:
            motivos.append("compra_sem_itens")

        for item in itens:
            if usar_resolucao_manual and item.produto_resolvido_id:
                produto_match = item.produto_resolvido
            else:
                produto_match_key = (
                    _normalize_identity_text(item.nome_produto_legado),
                    _to_int(item.id_produto_legado),
                )
                produto_match, _, _ = produto_match_cache.get(produto_match_key, (None, 0.0, "nenhum"))
                if produto_match_key not in produto_match_cache:
                    produto_match, produto_similaridade, produto_estrategia = _match_by_similarity_first(
                        nome_legado=item.nome_produto_legado,
                        id_legado=item.id_produto_legado,
                        candidates=produto_candidates,
                        by_id=produtos_por_id,
                        limiar=LIMIAR_SEMELHANCA_PRODUTO,
                        ordenar_tokens=True,
                    )
                    produto_match_cache[produto_match_key] = (
                        produto_match,
                        produto_similaridade,
                        produto_estrategia,
                    )

            if usar_resolucao_manual and item.unidade_resolvida_id:
                unidade_match = item.unidade_resolvida
            else:
                unidade_match = _resolver_unidade_legado(
                    unidade_legado=item.unidade_legado,
                    unidades_por_sigla=unidades_por_sigla,
                )

            item.produto_resolvido = produto_match
            item.unidade_resolvida = unidade_match

            if produto_match is None:
                motivos.append("produto_sem_correspondencia")
            if unidade_match is None:
                motivos.append("unidade_sem_mapeamento")

            if _is_negative(item.quantidade) or _is_negative(item.valor_custo):
                motivos.append("valor_negativo_bloqueado")

            valor_total_item = item.valor_total_calculado if item.valor_total_calculado is not None else item.valor_total_legado
            if _is_negative(valor_total_item):
                motivos.append("valor_negativo_bloqueado")

            item.status_validacao = (
                STG_ItemCompra.STATUS_VALIDADO
                if produto_match is not None and unidade_match is not None
                else STG_ItemCompra.STATUS_DIVERGENTE
            )
            itens_to_update.append(item)

        if abs(valor_total_compra - total_itens) > DECIMAL_TOLERANCIA_TOTAL:
            motivos.append("divergencia_total_itens")

        motivos_limpos = sorted(set(motivos))
        motivos_bloqueantes_validacao_manual = sorted(
            set(motivos_limpos) - MOTIVOS_DIVERGENCIA_NAO_BLOQUEANTES_VALIDACAO_MANUAL
        )
        snapshot = _build_snapshot_compra(
            compra=compra,
            motivos=motivos_limpos,
            total_itens=total_itens,
            fornecedor_resolvido=fornecedor_match,
            fornecedor_similaridade=fornecedor_similaridade,
            fornecedor_estrategia=fornecedor_estrategia,
        )

        if motivos_limpos:
            if compra.validacao_override and not motivos_bloqueantes_validacao_manual:
                compra.status_validacao = STG_Compra.STATUS_VALIDADO
                compra.status_tratamento = STG_Compra.TRATAMENTO_VALIDADO
                compra.snapshot_divergencia = {}
                compras_aprovadas += 1
                soma_valor_aprovadas += compra.valor_total or Decimal("0")
            else:
                if "duplicado_sot" in motivos_limpos:
                    compra.status_tratamento = STG_Compra.TRATAMENTO_NEGLIGENCIADO
                compra.status_validacao = STG_Compra.STATUS_DIVERGENTE
                compra.snapshot_divergencia = snapshot
                if compra.status_tratamento != STG_Compra.TRATAMENTO_NEGLIGENCIADO:
                    compras_divergentes += 1

                for motivo in motivos_limpos:
                    motivos_count[motivo] = motivos_count.get(motivo, 0) + 1

                divergencias.append(
                    {
                        "id_compra_legado": int(compra.id_compra_legado),
                        "motivos": motivos_limpos,
                    }
                )
                inconsistencias.append(
                    {
                        "id_compra_legado": int(compra.id_compra_legado),
                        "nota": compra.nota,
                        "data_emissao": compra.data_emissao.isoformat() if isinstance(compra.data_emissao, date) else None,
                        "nfe_status": compra.nfe_status,
                        "tratamento": compra.status_tratamento,
                        **snapshot,
                    }
                )
        else:
            compra.status_validacao = STG_Compra.STATUS_VALIDADO
            compra.snapshot_divergencia = {}
            compra.status_tratamento = STG_Compra.TRATAMENTO_VALIDADO
            compras_aprovadas += 1
            soma_valor_aprovadas += compra.valor_total or Decimal("0")

    STG_Compra.objects.bulk_update(
        compras,
        [
            "status_validacao",
            "status_tratamento",
            "snapshot_divergencia",
            "fornecedor_resolvido",
        ],
        batch_size=1000,
    )

    if itens_to_update:
        STG_ItemCompra.objects.bulk_update(
            itens_to_update,
            ["status_validacao", "produto_resolvido", "unidade_resolvida"],
            batch_size=2000,
        )

    periodo = STG_Compra.objects.aggregate(data_inicial=Min("data_emissao"), data_final=Max("data_emissao"))
    soma_valor_stg = sum((compra.valor_total or Decimal("0") for compra in compras), Decimal("0"))

    kpis = {
        "total_compras_stg": len(compras),
        "compras_aprovadas": compras_aprovadas,
        "compras_divergentes": compras_divergentes,
        "compras_duplicadas_sot": compras_duplicadas_sot,
        "motivos_divergencia": motivos_count,
        "soma_valor_stg": str(soma_valor_stg),
        "soma_valor_aprovadas": str(soma_valor_aprovadas),
        "periodo_data_inicial": periodo["data_inicial"].isoformat() if periodo["data_inicial"] else None,
        "periodo_data_final": periodo["data_final"].isoformat() if periodo["data_final"] else None,
        "compras_negligenciadas": STG_Compra.objects.filter(
            status_tratamento=STG_Compra.TRATAMENTO_NEGLIGENCIADO
        ).count(),
    }

    return ValidationResultCompras(
        compras_aprovadas=compras_aprovadas,
        compras_divergentes=compras_divergentes,
        compras_duplicadas_sot=compras_duplicadas_sot,
        divergencias=divergencias[:300],
        inconsistencias=inconsistencias[:500],
        kpis=kpis,
        pode_aprovar=compras_divergentes == 0 and compras_aprovadas > 0,
    )


def obter_kpis_reconciliacao_compras() -> dict[str, Any]:
    _garantir_validacao_materializada()

    base_qs = STG_Compra.objects.all()
    periodo = base_qs.aggregate(data_inicial=Min("data_emissao"), data_final=Max("data_emissao"))
    soma_valor = base_qs.aggregate(total=Sum("valor_total"))

    motivos_count: dict[str, int] = {motivo: 0 for motivo in sorted(MOTIVOS_DIVERGENCIA_VALIDOS)}
    compras_duplicadas_sot = 0

    for snapshot in STG_Compra.objects.filter(status_validacao=STG_Compra.STATUS_DIVERGENTE).values_list(
        "snapshot_divergencia", flat=True
    ):
        snapshot_data = snapshot or {}
        motivos = {
            _normalize_text(item).lower()
            for item in (snapshot_data.get("motivos") or [])
            if _normalize_text(item)
        }
        for motivo in motivos:
            if motivo in MOTIVOS_DIVERGENCIA_VALIDOS:
                motivos_count[motivo] = motivos_count.get(motivo, 0) + 1
        if "duplicado_sot" in motivos:
            compras_duplicadas_sot += 1

    return {
        "total_compras_stg": base_qs.count(),
        "compras_aprovadas": STG_Compra.objects.filter(
            status_validacao__in=_status_validacao_validada_values(STG_Compra)
        ).count(),
        "compras_divergentes": STG_Compra.objects.filter(status_validacao=STG_Compra.STATUS_DIVERGENTE)
        .exclude(status_tratamento=STG_Compra.TRATAMENTO_NEGLIGENCIADO)
        .count(),
        "compras_duplicadas_sot": compras_duplicadas_sot,
        "motivos_divergencia": motivos_count,
        "soma_valor_stg": str(soma_valor.get("total") or Decimal("0")),
        "soma_valor_aprovadas": str(
            STG_Compra.objects.filter(
                status_validacao__in=_status_validacao_validada_values(STG_Compra)
            ).aggregate(total=Sum("valor_total")).get("total") or Decimal("0")
        ),
        "periodo_data_inicial": periodo["data_inicial"].isoformat() if periodo["data_inicial"] else None,
        "periodo_data_final": periodo["data_final"].isoformat() if periodo["data_final"] else None,
        "compras_negligenciadas": STG_Compra.objects.filter(
            status_tratamento=STG_Compra.TRATAMENTO_NEGLIGENCIADO
        ).count(),
    }


def obter_queryset_divergencias_reconciliacao_compras(
    *,
    motivo: str | None = None,
    status_tratamento: str | None = None,
    nfe_status: str | None = None,
    id_compra_legado: str | int | None = None,
):
    _garantir_validacao_materializada()

    motivo_norm = _normalize_text(motivo).lower()
    if motivo_norm and motivo_norm not in MOTIVOS_DIVERGENCIA_VALIDOS:
        motivo_norm = ""

    status_norm = _normalize_text(status_tratamento).upper()
    if status_norm not in {
        "",
        STG_Compra.TRATAMENTO_PENDENTE,
        STG_Compra.TRATAMENTO_AJUSTADO,
        STG_Compra.TRATAMENTO_VALIDADO,
        STG_Compra.TRATAMENTO_NEGLIGENCIADO,
    }:
        status_norm = ""

    nfe_status_norm = _normalize_text(nfe_status).upper()
    id_compra_norm = _normalize_text(id_compra_legado)

    if status_norm:
        if status_norm == STG_Compra.TRATAMENTO_PENDENTE:
            compras = STG_Compra.objects.filter(
                status_validacao=STG_Compra.STATUS_DIVERGENTE,
                status_tratamento__in=[
                    STG_Compra.TRATAMENTO_PENDENTE,
                    STG_Compra.TRATAMENTO_AJUSTADO,
                ],
            )
        else:
            compras = STG_Compra.objects.filter(status_tratamento=status_norm)
    else:
        compras = STG_Compra.objects.filter(status_validacao=STG_Compra.STATUS_DIVERGENTE)
    if nfe_status_norm:
        compras = compras.filter(nfe_status=nfe_status_norm)
    if id_compra_norm:
        try:
            compra_id = int(id_compra_norm)
        except (TypeError, ValueError):
            compras = compras.none()
        else:
            compras = compras.filter(id_compra_legado=compra_id)
    if motivo_norm:
        compras = compras.filter(snapshot_divergencia__motivos__contains=[motivo_norm])

    return compras.prefetch_related("itens", "fornecedor_resolvido").order_by("data_emissao", "id_compra_legado")


def serializar_divergencia_reconciliacao_compra(compra: STG_Compra) -> dict[str, Any]:
    snapshot = compra.snapshot_divergencia or {}
    motivos = sorted(
        {
            _normalize_text(item).lower()
            for item in snapshot.get("motivos") or []
            if _normalize_text(item)
        }
    )

    return {
        "id_compra_legado": int(compra.id_compra_legado),
        "nota": compra.nota,
        "compra": f"COMPRA #{int(compra.id_compra_legado):06d}",
        "data_emissao": compra.data_emissao.isoformat() if compra.data_emissao else None,
        "nfe_status": compra.nfe_status,
        "motivos": motivos,
        "tratamento": compra.status_tratamento,
        "fornecedor_legado": {
            "id_fornecedor_legado": compra.id_fornecedor_legado,
            "nome_fornecedor_legado": compra.nome_fornecedor_legado,
        },
        "fornecedor_resolvido": {
            "id_fornecedor": int(compra.fornecedor_resolvido.id_fornecedor),
            "nome_fornecedor": compra.fornecedor_resolvido.nome_fornecedor,
        }
        if compra.fornecedor_resolvido is not None
        else None,
        "totais": {
            "total_compra": snapshot.get("total_compra"),
            "total_itens": snapshot.get("total_itens"),
            "diferenca_total": snapshot.get("diferenca_total"),
        },
        "itens": [
            {
                "id_stg_item_compra": int(item.id_stg_item_compra),
                "id_produto_legado": item.id_produto_legado,
                "nome_produto_legado": item.nome_produto_legado,
                "unidade_legado": item.unidade_legado,
                "quantidade": str(item.quantidade or Decimal("0")),
                "valor_custo": str(item.valor_custo or Decimal("0")),
                "valor_total_calculado": str(
                    item.valor_total_calculado
                    if item.valor_total_calculado is not None
                    else item.valor_total_legado
                    if item.valor_total_legado is not None
                    else Decimal("0")
                ),
                "produto_resolvido_id": item.produto_resolvido_id,
                "unidade_resolvida_id": item.unidade_resolvida_id,
            }
            for item in compra.itens.all()
        ],
    }


def listar_divergencias_reconciliacao_compras(
    *,
    motivo: str | None = None,
    status_tratamento: str | None = None,
    nfe_status: str | None = None,
) -> list[dict[str, Any]]:
    compras = obter_queryset_divergencias_reconciliacao_compras(
        motivo=motivo,
        status_tratamento=status_tratamento,
        nfe_status=nfe_status,
    )
    return [serializar_divergencia_reconciliacao_compra(compra) for compra in compras]


def _montar_bloqueio_compra(compra: STG_Compra, motivos: list[str]) -> dict[str, Any]:
    return {
        "id_compra_legado": int(compra.id_compra_legado),
        "compra": f"COMPRA #{int(compra.id_compra_legado):06d}",
        "nota": compra.nota,
        "erros": [f"{compra.id_compra_legado}: {', '.join(motivos)}"],
        "codigos": sorted(set(motivos)),
        "permite_override": False,
    }


def _formatar_erros_bloqueio(prefixo: str, bloqueios: list[dict[str, Any]]) -> str:
    linhas = [prefixo]
    for item in bloqueios[:40]:
        compra = item.get("compra") or item.get("id_compra_legado")
        codigos = ", ".join(item.get("codigos") or [])
        linhas.append(f"- {compra}: {codigos}")

    restante = len(bloqueios) - 40
    if restante > 0:
        linhas.append(f"- ... e mais {restante} compra(s).")

    return "\n".join(linhas)


def aplicar_tratamento_divergencia_compra(
    *,
    id_compra_legado: int,
    acao: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    compra = STG_Compra.objects.filter(id_compra_legado=id_compra_legado).prefetch_related("itens").first()
    if compra is None:
        raise ValueError("Compra STG nao encontrada para tratamento.")

    acao_norm = _normalize_text(acao).lower()
    if acao_norm != "ajustar":
        raise ValueError("Acao invalida para tratamento unitario. Use apenas 'ajustar'.")

    with transaction.atomic():
        update_fields_compra = ["validacao_override", "status_tratamento", "tratamento_atualizado_em"]
        compra.validacao_override = False
        compra.status_tratamento = STG_Compra.TRATAMENTO_AJUSTADO

        if "valor_total" in payload:
            valor_total = _to_decimal(payload.get("valor_total"))
            if valor_total is None:
                raise ValueError("valor_total invalido.")
            compra.valor_total = valor_total
            update_fields_compra.append("valor_total")

        if "valor_produtos" in payload:
            valor_produtos = _to_decimal(payload.get("valor_produtos"))
            if valor_produtos is None:
                raise ValueError("valor_produtos invalido.")
            compra.valor_produtos = valor_produtos
            update_fields_compra.append("valor_produtos")

        if "nfe_status" in payload:
            compra.nfe_status = _normalize_text(payload.get("nfe_status"))
            update_fields_compra.append("nfe_status")

        if "fornecedor_resolvido_id" in payload:
            fornecedor_id_raw = payload.get("fornecedor_resolvido_id")
            if fornecedor_id_raw in (None, ""):
                compra.fornecedor_resolvido = None
            else:
                try:
                    fornecedor_id = int(fornecedor_id_raw)
                except (TypeError, ValueError):
                    raise ValueError("fornecedor_resolvido_id invalido.")
                fornecedor = Fornecedor.objects.filter(id_fornecedor=fornecedor_id).first()
                if fornecedor is None:
                    raise ValueError("fornecedor_resolvido_id nao encontrado.")
                compra.fornecedor_resolvido = fornecedor
            update_fields_compra.append("fornecedor_resolvido")

        for item_data in payload.get("itens") or []:
            item_id_raw = item_data.get("id_stg_item_compra")
            try:
                item_id = int(item_id_raw)
            except (TypeError, ValueError):
                continue

            item = STG_ItemCompra.objects.filter(id_stg_item_compra=item_id, stg_compra=compra).first()
            if item is None:
                continue

            update_fields_item: list[str] = []

            if "quantidade" in item_data:
                quantidade = _to_decimal(item_data.get("quantidade"))
                if quantidade is None:
                    raise ValueError("quantidade invalida no item.")
                item.quantidade = quantidade
                update_fields_item.append("quantidade")

            if "valor_custo" in item_data:
                valor_custo = _to_decimal(item_data.get("valor_custo"))
                if valor_custo is None:
                    raise ValueError("valor_custo invalido no item.")
                item.valor_custo = valor_custo
                update_fields_item.append("valor_custo")

            if "valor_total_calculado" in item_data:
                valor_total_calc = _to_decimal(item_data.get("valor_total_calculado"))
                if valor_total_calc is None:
                    raise ValueError("valor_total_calculado invalido no item.")
                item.valor_total_calculado = valor_total_calc
                update_fields_item.append("valor_total_calculado")

            if "produto_resolvido_id" in item_data:
                produto_id_raw = item_data.get("produto_resolvido_id")
                if produto_id_raw in (None, ""):
                    item.produto_resolvido = None
                else:
                    try:
                        produto_id = int(produto_id_raw)
                    except (TypeError, ValueError):
                        raise ValueError("produto_resolvido_id invalido no item.")
                    produto = Produto.objects.filter(id_produto=produto_id).first()
                    if produto is None:
                        raise ValueError("produto_resolvido_id nao encontrado no item.")
                    item.produto_resolvido = produto
                update_fields_item.append("produto_resolvido")

            if "unidade_resolvida_id" in item_data:
                unidade_id_raw = item_data.get("unidade_resolvida_id")
                if unidade_id_raw in (None, ""):
                    item.unidade_resolvida = None
                else:
                    try:
                        unidade_id = int(unidade_id_raw)
                    except (TypeError, ValueError):
                        raise ValueError("unidade_resolvida_id invalido no item.")
                    unidade = UnidadeMedida.objects.filter(id_und_medida=unidade_id).first()
                    if unidade is None:
                        raise ValueError("unidade_resolvida_id nao encontrado no item.")
                    item.unidade_resolvida = unidade
                update_fields_item.append("unidade_resolvida")

            if "descricao_legado" in item_data:
                item.descricao_legado = _normalize_text(item_data.get("descricao_legado"))
                update_fields_item.append("descricao_legado")

            if "descricao_compra_legado" in item_data:
                item.descricao_compra_legado = _normalize_text(item_data.get("descricao_compra_legado"))
                update_fields_item.append("descricao_compra_legado")

            if update_fields_item:
                item.save(update_fields=update_fields_item)

        compra.tratamento_atualizado_em = timezone.now()
        compra.save(update_fields=update_fields_compra)

    validation = executar_validacao_compras(reset_tracking=False)
    return {
        "detail": "Tratamento aplicado com sucesso.",
        "kpis": validation.kpis,
    }


def aplicar_tratamento_divergencias_compra_lote(
    *,
    compras: list[dict[str, Any]],
    acao: str,
) -> dict[str, Any]:
    acao_norm = _normalize_text(acao).lower()
    if acao_norm not in {"validar", "negligenciar"}:
        raise ValueError("Acao em lote invalida. Use 'validar' ou 'negligenciar'.")

    processadas = 0
    ignoradas = 0
    bloqueadas = 0
    bloqueios: list[dict[str, Any]] = []

    with transaction.atomic():
        for item in compras:
            id_compra_raw = item.get("id_compra_legado")
            try:
                id_compra_legado = int(id_compra_raw)
            except (TypeError, ValueError):
                ignoradas += 1
                continue

            compra = STG_Compra.objects.filter(id_compra_legado=id_compra_legado).first()
            if compra is None:
                ignoradas += 1
                continue

            if acao_norm == "validar":
                motivos_bloqueantes = sorted(_motivos_bloqueantes_validacao_manual(compra))
                if motivos_bloqueantes:
                    bloqueadas += 1
                    bloqueios.append(_montar_bloqueio_compra(compra, motivos_bloqueantes))
                    continue

                compra.validacao_override = True
                compra.status_validacao = STG_Compra.STATUS_VALIDADO
                compra.status_tratamento = STG_Compra.TRATAMENTO_VALIDADO
                compra.snapshot_divergencia = {}
                compra.tratamento_atualizado_em = timezone.now()
                compra.save(
                    update_fields=[
                        "validacao_override",
                        "status_validacao",
                        "status_tratamento",
                        "snapshot_divergencia",
                        "tratamento_atualizado_em",
                    ]
                )
            else:
                compra.validacao_override = False
                compra.status_validacao = STG_Compra.STATUS_DIVERGENTE
                compra.status_tratamento = STG_Compra.TRATAMENTO_NEGLIGENCIADO
                compra.tratamento_atualizado_em = timezone.now()
                compra.save(
                    update_fields=[
                        "validacao_override",
                        "status_validacao",
                        "status_tratamento",
                        "tratamento_atualizado_em",
                    ]
                )

            processadas += 1

    validation = executar_validacao_compras(reset_tracking=False)
    return {
        "detail": "Tratamento em lote concluido.",
        "processadas": processadas,
        "ignoradas": ignoradas,
        "bloqueadas": bloqueadas,
        "bloqueios": bloqueios[:200],
        "kpis": validation.kpis,
    }


def consolidar_compras_stg_para_sot() -> dict[str, Any]:
    _normalizar_status_validacao_legado()

    executar_validacao_compras(reset_tracking=False)

    divergentes_pendentes = list(
        STG_Compra.objects.filter(status_validacao=STG_Compra.STATUS_DIVERGENTE)
        .exclude(status_tratamento=STG_Compra.TRATAMENTO_NEGLIGENCIADO)
        .prefetch_related("itens")
        .order_by("data_emissao", "id_compra_legado")
    )

    bloqueios_divergencia: list[dict[str, Any]] = []
    for compra in divergentes_pendentes:
        motivos_bloqueantes = sorted(_motivos_bloqueantes_consolidacao(compra))
        if motivos_bloqueantes:
            bloqueios_divergencia.append(_montar_bloqueio_compra(compra, motivos_bloqueantes))

    if bloqueios_divergencia:
        raise ReconciliacaoCompraBloqueioError(
            _formatar_erros_bloqueio(
                "Consolidacao bloqueada por divergencias estruturais na reconciliacao de compras.",
                bloqueios_divergencia,
            ),
            codigo="consolidacao_bloqueada_divergencia_reconciliacao",
            bloqueios=bloqueios_divergencia[:200],
        )

    aprovadas = list(
        STG_Compra.objects.filter(status_validacao__in=_status_validacao_validada_values(STG_Compra))
        .exclude(status_tratamento=STG_Compra.TRATAMENTO_NEGLIGENCIADO)
        .prefetch_related("itens")
        .order_by("data_emissao", "id_compra_legado")
    )

    if not aprovadas:
        raise ValueError("Nao ha compras aprovadas na STG para consolidar.")

    compras_por_id_legado: dict[int, STG_Compra] = {}
    for compra in aprovadas:
        compras_por_id_legado[int(compra.id_compra_legado)] = compra

    aprovadas = list(compras_por_id_legado.values())

    existentes_sot = {int(item) for item in Compra.objects.values_list("id_legado", flat=True)}

    ignoradas_duplicadas = 0
    candidatas: list[STG_Compra] = []
    for compra in aprovadas:
        if int(compra.id_compra_legado) in existentes_sot:
            ignoradas_duplicadas += 1
            continue
        candidatas.append(compra)

    if not candidatas:
        with transaction.atomic():
            stg_compras_removidas = STG_Compra.objects.count()
            stg_itens_removidos = STG_ItemCompra.objects.count()
            STG_ItemCompra.objects.all().delete()
            STG_Compra.objects.all().delete()

        return {
            "compras_inseridas": 0,
            "compras_ignoradas_duplicadas": ignoradas_duplicadas,
            "compras_ignoradas_incompletas": 0,
            "detalhes_ignorados": [],
            "momento_consolidacao": None,
            "stg_compras_removidas": stg_compras_removidas,
            "stg_itens_removidos": stg_itens_removidos,
        }

    catalogos = _build_catalogos_correspondencia()
    fornecedor_candidates = catalogos["fornecedor_candidates"]
    produto_candidates = catalogos["produto_candidates"]
    fornecedores_por_id = catalogos["fornecedores_por_id"]
    produtos_por_id = catalogos["produtos_por_id"]
    unidades_por_sigla = catalogos["unidades_por_sigla"]

    preparadas: list[dict[str, Any]] = []
    bloqueios_precheck: list[dict[str, Any]] = []

    for compra in candidatas:
        itens = list(compra.itens.all())
        motivos_compra: list[str] = []

        fornecedor = compra.fornecedor_resolvido
        if fornecedor is None:
            fornecedor, _, _ = _match_by_similarity_first(
                nome_legado=compra.nome_fornecedor_legado,
                id_legado=compra.id_fornecedor_legado,
                candidates=fornecedor_candidates,
                by_id=fornecedores_por_id,
                limiar=LIMIAR_SEMELHANCA_FORNECEDOR,
                ordenar_tokens=False,
            )

        if fornecedor is None:
            motivos_compra.append("fornecedor_sem_correspondencia")

        if _is_negative(compra.valor_total) or _is_negative(compra.valor_produtos):
            motivos_compra.append("valor_negativo_bloqueado")

        if not itens:
            motivos_compra.append("compra_sem_itens")

        total_itens = _sum_total_itens(itens)
        if abs((compra.valor_total or Decimal("0")) - total_itens) > DECIMAL_TOLERANCIA_TOTAL:
            motivos_compra.append("divergencia_total_itens")

        itens_convertidos: list[tuple[STG_ItemCompra, Produto, UnidadeMedida, Decimal]] = []

        for item in itens:
            produto = item.produto_resolvido
            if produto is None:
                produto, _, _ = _match_by_similarity_first(
                    nome_legado=item.nome_produto_legado,
                    id_legado=item.id_produto_legado,
                    candidates=produto_candidates,
                    by_id=produtos_por_id,
                    limiar=LIMIAR_SEMELHANCA_PRODUTO,
                    ordenar_tokens=True,
                )

            if produto is None:
                motivos_compra.append("produto_sem_correspondencia")
                continue

            unidade = item.unidade_resolvida
            if unidade is None:
                unidade = _resolver_unidade_legado(
                    unidade_legado=item.unidade_legado,
                    unidades_por_sigla=unidades_por_sigla,
                )

            if unidade is None:
                motivos_compra.append("unidade_sem_mapeamento")
                continue

            quantidade = item.quantidade or Decimal("0")
            valor_custo = item.valor_custo or Decimal("0")
            valor_total_item = (
                item.valor_total_calculado
                if item.valor_total_calculado is not None
                else item.valor_total_legado
                if item.valor_total_legado is not None
                else quantidade * valor_custo
            )

            if _is_negative(quantidade) or _is_negative(valor_custo) or _is_negative(valor_total_item):
                motivos_compra.append("valor_negativo_bloqueado")
                continue

            itens_convertidos.append((item, produto, unidade, valor_total_item))

        motivos_bloqueantes_precheck = sorted(
            set(motivos_compra) - MOTIVOS_DIVERGENCIA_NAO_BLOQUEANTES_CONSOLIDACAO
        )
        if motivos_bloqueantes_precheck:
            bloqueios_precheck.append(_montar_bloqueio_compra(compra, motivos_bloqueantes_precheck))
            continue

        preparadas.append(
            {
                "compra": compra,
                "fornecedor": fornecedor,
                "itens": itens_convertidos,
            }
        )

    if bloqueios_precheck:
        raise ReconciliacaoCompraBloqueioError(
            _formatar_erros_bloqueio(
                "Consolidacao bloqueada por inconsistencias estruturais de pre-check.",
                bloqueios_precheck,
            ),
            codigo="consolidacao_bloqueada_precheck",
            bloqueios=bloqueios_precheck[:200],
        )

    if not preparadas:
        raise ValueError("Nao ha compras aptas para consolidacao apos o pre-check.")

    inseridas = 0
    momento_consolidacao = timezone.now()

    with transaction.atomic():
        for pacote in preparadas:
            stg_compra = pacote["compra"]
            fornecedor = pacote["fornecedor"]

            compra = Compra.objects.create(
                id_legado=stg_compra.id_compra_legado,
                nota=stg_compra.nota,
                fornecedor=fornecedor,
                data_emissao=stg_compra.data_emissao,
                data_lanc=stg_compra.data_lanc,
                valor_produtos=stg_compra.valor_produtos,
                valor_total_documento=stg_compra.valor_total or Decimal("0"),
                nfe_status=stg_compra.nfe_status,
                momento_consolidacao=momento_consolidacao,
            )

            ItemCompra.objects.bulk_create(
                [
                    ItemCompra(
                        compra=compra,
                        produto=produto,
                        unidade_medida=unidade,
                        quantidade=item.quantidade or Decimal("0"),
                        valor_custo=item.valor_custo or Decimal("0"),
                        valor_total_item=valor_total_item,
                        descricao_origem=item.descricao_legado,
                        descricao_compra_origem=item.descricao_compra_legado,
                    )
                    for item, produto, unidade, valor_total_item in pacote["itens"]
                ],
                batch_size=2000,
            )

            inseridas += 1

        stg_compras_removidas = STG_Compra.objects.count()
        stg_itens_removidos = STG_ItemCompra.objects.count()
        STG_ItemCompra.objects.all().delete()
        STG_Compra.objects.all().delete()

    return {
        "compras_inseridas": inseridas,
        "compras_ignoradas_duplicadas": ignoradas_duplicadas,
        "compras_ignoradas_incompletas": 0,
        "detalhes_ignorados": [],
        "momento_consolidacao": momento_consolidacao.isoformat(),
        "stg_compras_removidas": stg_compras_removidas,
        "stg_itens_removidos": stg_itens_removidos,
    }


def limpar_fluxo_reconciliacao_compras() -> dict[str, int]:
    with transaction.atomic():
        stg_itens_removidos = STG_ItemCompra.objects.count()
        stg_compras_removidas = STG_Compra.objects.count()

        STG_ItemCompra.objects.all().delete()
        STG_Compra.objects.all().delete()

    return {
        "stg_compras_removidas": stg_compras_removidas,
        "stg_itens_removidos": stg_itens_removidos,
    }

