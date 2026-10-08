"""Fila de acompanhamento das folhas, sem modificar agregados de vendas."""

from collections import defaultdict
from datetime import date

from apps.cadastros.models import PlanoConta
from apps.vendas.models import Venda

from .models import CategoriaVendaQuarentena, MovimentoProdutoMensal, MovimentoProdutoSemanal
from .services import AgregadoDiarioIncompletoError, CategoriasAmbiguasError, montar_analise_vendas_categorias
from .services_vendas_anuais import montar_analise_vendas_categorias_anual
from .services_vendas_semanais import montar_analise_vendas_categorias_semanal


def validar_folha(categoria_id: int) -> PlanoConta:
    categoria = PlanoConta.objects.filter(pk=categoria_id).first()
    if categoria is None:
        raise PlanoConta.DoesNotExist
    if categoria.conta_pai_id is None or PlanoConta.objects.filter(conta_pai_id=categoria_id).exists():
        raise ValueError("Somente categorias folha de uma familia podem entrar na quarentena.")
    return categoria


def listar_marcacoes() -> list[dict]:
    """Resolve a familia pela arvore atual, inclusive apos mover uma categoria."""
    nodes = {
        node["id_conta"]: node
        for node in PlanoConta.objects.values(
            "id_conta", "codigo_hierarquico", "codigo_ordenacao", "nome_conta", "conta_pai_id"
        )
    }
    pais = {node["conta_pai_id"] for node in nodes.values() if node["conta_pai_id"] is not None}
    marcados = CategoriaVendaQuarentena.objects.values_list("categoria_id", flat=True)
    saida = []
    for categoria_id in marcados:
        node = nodes.get(categoria_id)
        if node is None:
            continue  # Protecao para bases antigas sem FK fisica; exclusao normal usa CASCADE.
        atual = node
        visitados = set()
        while atual["conta_pai_id"] in nodes and atual["id_conta"] not in visitados:
            visitados.add(atual["id_conta"])
            atual = nodes[atual["conta_pai_id"]]
        raiz = atual
        folha_valida = (
            node["conta_pai_id"] is not None
            and categoria_id not in pais
            and raiz["conta_pai_id"] is None
            and atual["id_conta"] not in visitados
        )
        saida.append({
            "id_conta": categoria_id,
            "codigo_hierarquico": node["codigo_hierarquico"],
            "nome_conta": node["nome_conta"],
            "raiz_id": raiz["id_conta"],
            "familia": {
                "id_conta": raiz["id_conta"],
                "codigo_hierarquico": raiz["codigo_hierarquico"],
                "nome_conta": raiz["nome_conta"],
            },
            "folha_valida": folha_valida,
            "motivo_invalido": None if folha_valida else "Esta categoria deixou de ser uma folha da familia.",
            "_ordem_familia": raiz["codigo_ordenacao"],
            "_ordem_categoria": node["codigo_ordenacao"],
        })
    saida.sort(key=lambda item: (item["_ordem_familia"], item["_ordem_categoria"], item["id_conta"]))
    for item in saida:
        item.pop("_ordem_familia")
        item.pop("_ordem_categoria")
    return saida


def montar_matriz_quarentena(
    *, visao: str, metrica: str, periodo_equivalente: bool,
    ano: int | None = None, semana_inicio: date | None = None, raiz_id: int | None = None,
) -> dict:
    if visao not in {"semanal", "mensal", "anual"} or metrica not in {"valor", "quantidade"}:
        raise ValueError("Informe visao=semanal|mensal|anual e metrica=valor|quantidade.")
    if visao == "semanal":
        if semana_inicio is None or (semana_inicio.weekday() + 1) % 7 != 0:
            raise ValueError("Informe o domingo inicial da semana.")
    elif ano is None or ano < 1:
        raise ValueError("Informe um ano valido.")
    if raiz_id is not None and not PlanoConta.objects.filter(pk=raiz_id, conta_pai__isnull=True).exists():
        raise PlanoConta.DoesNotExist

    categorias = [item for item in listar_marcacoes() if raiz_id is None or item["raiz_id"] == raiz_id]
    por_familia = defaultdict(list)
    for item in categorias:
        por_familia[item["raiz_id"]].append(item)

    grupos = []
    for familia_id, itens in por_familia.items():
        grupo = {"familia": itens[0]["familia"], "categorias": itens, "dados": None, "erro": None}
        ids_validos = {item["id_conta"] for item in itens if item["folha_valida"]}
        if ids_validos:
            try:
                if visao == "semanal":
                    dados = montar_analise_vendas_categorias_semanal(
                        raiz_id=familia_id, semana_inicio=semana_inicio,
                        metrica=metrica, periodo_equivalente=periodo_equivalente,
                    )
                elif visao == "mensal":
                    dados = montar_analise_vendas_categorias(
                        raiz_id=familia_id, ano=ano,
                        metrica=metrica, periodo_equivalente=periodo_equivalente,
                    )
                else:
                    dados = montar_analise_vendas_categorias_anual(
                        raiz_id=familia_id, ano=ano,
                        metrica=metrica, periodo_equivalente=periodo_equivalente,
                    )
                linhas = [linha for linha in dados["linhas"] if linha["id_conta"] in ids_validos and not linha["tem_filhos"]]
                if {linha["id_conta"] for linha in linhas} != ids_validos:
                    grupo["erro"] = {"status": 409, "detail": "A arvore atual da familia nao corresponde as categorias marcadas."}
                else:
                    grupo["dados"] = {**dados, "linhas": linhas}
            except CategoriasAmbiguasError as exc:
                grupo["erro"] = {"status": 409, "detail": str(exc), "produtos_conflitantes": exc.produtos}
            except AgregadoDiarioIncompletoError as exc:
                grupo["erro"] = {"status": 503, "detail": str(exc)}
            except (MovimentoProdutoMensal.DoesNotExist, MovimentoProdutoSemanal.DoesNotExist, Venda.DoesNotExist, PlanoConta.DoesNotExist):
                grupo["erro"] = {"status": 404, "detail": "Nao ha agregado valido para esta familia e periodo."}
        grupos.append(grupo)

    return {
        "visao": visao,
        "metrica": metrica,
        "ano": ano if visao != "semanal" else None,
        "semana_inicio": semana_inicio.isoformat() if visao == "semanal" else None,
        "periodo_equivalente": periodo_equivalente,
        "raiz_id": raiz_id,
        "total_categorias": len(categorias),
        "grupos": grupos,
    }
