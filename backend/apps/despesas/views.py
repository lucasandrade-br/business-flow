from datetime import date
from decimal import Decimal
from collections import Counter

from django.core.files.uploadedfile import SimpleUploadedFile

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AuditoriaDespesa, CategoriaDespesa, ConflitoDespesa, LinhaDespesa,
    LoteDespesa, MovimentoDespesa, PagamentoDespesa, TipoDespesa,
    VinculoTipoDespesa,
)
from .serializers import CategoriaSerializer, MovimentoSerializer, PagamentoSerializer, TipoSerializer
from .services import (
    auditar, chave, chave_base_dados, consolidar_lote, criar_lote, hash_conteudo_dados, mes_inicio, meses_movimento, numero_decimal,
    reconstruir_periodos, salvar_vinculo, verificar_pai_sem_vinculos,
)
from .bi import obter_bi


def operador(request):
    return str(getattr(request.user, "username", "") or request.headers.get("X-Operador", ""))[:120]


def lista_paginada(request, queryset, serializer):
    paginator = PageNumberPagination()
    paginator.page_size = 100
    page = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response(serializer(page, many=True).data)


def erro_modelo(exc):
    if hasattr(exc, "message_dict"):
        raise ValidationError(exc.message_dict)
    raise ValidationError(exc.messages)


def ids_unicos(valor, campo):
    if not isinstance(valor, list) or len(valor) > 500 or any(type(item) is not int or item <= 0 for item in valor):
        raise ValidationError({campo: "Informe uma lista de até 500 IDs positivos."})
    if len(valor) != len(set(valor)):
        raise ValidationError({campo: "A lista contém IDs repetidos."})
    return valor


class CategoriasView(APIView):
    def get(self, request):
        qs = CategoriaDespesa.objects.select_related("pai").annotate(tipos_vinculados_count=Count("tipos_vinculados")).order_by("caminho")
        familia = request.query_params.get("familia_id")
        if familia:
            raiz = get_object_or_404(CategoriaDespesa, pk=familia, pai__isnull=True)
            qs = qs.filter(Q(pk=raiz.pk) | Q(caminho__startswith=raiz.caminho + "\x1f"))
        busca = request.query_params.get("search", "").strip()
        if busca:
            qs = qs.filter(Q(nome__icontains=busca) | Q(caminho__icontains=busca))
        return Response(CategoriaSerializer(qs, many=True).data)

    def post(self, request):
        with transaction.atomic():
            pai_id = request.data.get("pai")
            if pai_id:
                pai = get_object_or_404(CategoriaDespesa.objects.select_for_update(), pk=pai_id)
                try:
                    verificar_pai_sem_vinculos(pai)
                except DjangoValidationError as exc:
                    erro_modelo(exc)
            serializer = CategoriaSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            categoria = serializer.save()
            auditar("categoria", categoria.pk, "CRIAR", depois=serializer.data, operador=operador(request))
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CategoriasLoteView(APIView):
    def post(self, request):
        pai_id = request.data.get("pai_id")
        nomes = request.data.get("nomes")
        if not pai_id:
            raise ValidationError({"pai_id": "Selecione a categoria mãe."})
        if not isinstance(nomes, list) or not 1 <= len(nomes) <= 100:
            raise ValidationError({"nomes": "Informe de 1 a 100 categorias."})
        with transaction.atomic():
            pai = get_object_or_404(CategoriaDespesa.objects.select_for_update(), pk=pai_id)
            try:
                verificar_pai_sem_vinculos(pai)
            except DjangoValidationError as exc:
                erro_modelo(exc)
            nomes_limpios = [str(nome).strip() if isinstance(nome, str) else "" for nome in nomes]
            if len({chave(nome) for nome in nomes_limpios}) != len(nomes_limpios):
                raise ValidationError({"nomes": "Há nomes repetidos no lote."})
            existentes = {chave(nome) for nome in CategoriaDespesa.objects.filter(pai=pai).values_list("nome", flat=True)}
            if existentes.intersection(chave(nome) for nome in nomes_limpios):
                raise ValidationError({"nomes": "Uma ou mais categorias já existem sob esta mãe."})
            criadas = []
            for nome in nomes_limpios:
                serializer = CategoriaSerializer(data={"nome": nome, "pai": pai.pk})
                serializer.is_valid(raise_exception=True)
                categoria = serializer.save()
                auditar("categoria", categoria.pk, "CRIAR", depois=serializer.data, operador=operador(request))
                criadas.append(serializer.data)
        return Response({"total": len(criadas), "categorias": criadas}, status=status.HTTP_201_CREATED)


class CategoriaVinculosView(APIView):
    def get(self, request, pk):
        folha = get_object_or_404(CategoriaDespesa, pk=pk)
        if folha.pai_id is None or folha.filhas.exists():
            raise ValidationError({"folha": "Selecione uma categoria folha."})
        vinculos = VinculoTipoDespesa.objects.filter(folha=folha).order_by("tipo_id")
        return Response({"folha_id": folha.pk, "vinculados_ids": list(vinculos.values_list("tipo_id", flat=True))})

    def post(self, request, pk):
        adicionar = ids_unicos(request.data.get("adicionar_ids"), "adicionar_ids")
        remover = ids_unicos(request.data.get("remover_ids"), "remover_ids")
        if set(adicionar) & set(remover):
            raise ValidationError("O mesmo tipo não pode ser incluído e removido.")
        esperados = request.data.get("esperados")
        if not isinstance(esperados, dict):
            raise ValidationError({"esperados": "Informe a classificação observada para cada tipo alterado."})
        ids = sorted(set(adicionar + remover))
        if {str(tipo_id) for tipo_id in ids} != set(esperados):
            raise ValidationError({"esperados": "Informe a classificação de todos os tipos alterados."})
        with transaction.atomic():
            folha = get_object_or_404(CategoriaDespesa.objects.select_for_update(), pk=pk)
            if folha.pai_id is None or folha.filhas.exists():
                raise ValidationError({"folha": "Selecione uma categoria folha."})
            familia = folha
            while familia.pai_id:
                familia = familia.pai
            tipos = list(TipoDespesa.objects.select_for_update().filter(pk__in=ids).order_by("pk"))
            if len(tipos) != len(ids):
                raise ValidationError({"tipos": "Um ou mais tipos não existem."})
            atuais = {v.tipo_id: v for v in VinculoTipoDespesa.objects.select_for_update().filter(tipo_id__in=ids, familia=familia)}
            for tipo_id in ids:
                atual_id = atuais[tipo_id].folha_id if tipo_id in atuais else None
                esperado = esperados[str(tipo_id)]
                if type(esperado) not in (int, type(None)) or esperado != atual_id:
                    raise ValidationError({"esperados": "Os vínculos mudaram durante a edição. Reabra a seleção para revisar."})
            resultado = {"adicionados": 0, "transferidos": 0, "removidos": 0}
            for tipo in tipos:
                atual = atuais.get(tipo.pk)
                if tipo.pk in adicionar and (not atual or atual.folha_id != folha.pk):
                    resultado["transferidos" if atual else "adicionados"] += 1
                    salvar_vinculo(tipo, familia, folha, operador(request))
                elif tipo.pk in remover and atual and atual.folha_id == folha.pk:
                    auditar("vinculo", atual.pk, "REMOVER", antes={"folha_id": folha.pk}, operador=operador(request))
                    atual.delete()
                    resultado["removidos"] += 1
        return Response(resultado)


class CategoriaDetailView(APIView):
    def patch(self, request, pk):
        if set(request.data) - {"nome"}:
            raise ValidationError("Somente o nome pode ser editado nesta tela.")
        with transaction.atomic():
            categoria = get_object_or_404(CategoriaDespesa.objects.select_for_update(), pk=pk)
            antigo = categoria.caminho
            serializer = CategoriaSerializer(categoria, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            categoria = serializer.save()
            if categoria.caminho != antigo:
                descendentes = list(CategoriaDespesa.objects.filter(caminho__startswith=antigo + "\x1f").select_for_update())
                for no in descendentes:
                    no.caminho = categoria.caminho + no.caminho[len(antigo):]
                    if len(no.caminho) > 255:
                        raise ValidationError({"nome": "A alteração excederia 255 caracteres no caminho de uma categoria filha."})
                CategoriaDespesa.objects.bulk_update(descendentes, ["caminho"])
                auditar("categoria", categoria.pk, "RENOMEAR", antes={"caminho": antigo}, depois={"caminho": categoria.caminho}, operador=operador(request))
        return Response(CategoriaSerializer(categoria).data)


class TiposView(APIView):
    def get(self, request):
        qs = TipoDespesa.objects.prefetch_related("vinculos__folha").order_by("nome")
        busca = request.query_params.get("busca")
        if busca:
            qs = qs.filter(nome__icontains=busca)
        if request.query_params.get("ativo") == "1":
            qs = qs.filter(ativo=True)
        if request.query_params.get("folha_id"):
            qs = qs.filter(vinculos__folha_id=request.query_params["folha_id"])
        return lista_paginada(request, qs, TipoSerializer)

    def post(self, request):
        serializer = TipoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tipo = serializer.save()
        auditar("tipo", tipo.pk, "CRIAR", depois={"nome": tipo.nome}, operador=operador(request))
        return Response(TipoSerializer(tipo).data, status=status.HTTP_201_CREATED)


class TipoDetailView(APIView):
    def get(self, request, pk):
        return Response(TipoSerializer(get_object_or_404(TipoDespesa, pk=pk)).data)

    def patch(self, request, pk):
        tipo = get_object_or_404(TipoDespesa, pk=pk)
        antes = {"nome": tipo.nome, "ativo": tipo.ativo}
        serializer = TipoSerializer(tipo, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        tipo = serializer.save()
        depois = {"nome": tipo.nome, "ativo": tipo.ativo}
        if antes != depois:
            auditar("tipo", tipo.pk, "EDITAR", antes, depois, operador(request))
        return Response(TipoSerializer(tipo).data)


class VinculoView(APIView):
    def put(self, request, pk):
        tipo = get_object_or_404(TipoDespesa, pk=pk)
        familia = get_object_or_404(CategoriaDespesa, pk=request.data.get("familia_id"))
        folha = get_object_or_404(CategoriaDespesa, pk=request.data.get("folha_id"))
        try:
            vinculo = salvar_vinculo(tipo, familia, folha, operador(request))
        except DjangoValidationError as exc:
            erro_modelo(exc)
        return Response({"id": vinculo.pk, "familia_id": familia.pk, "folha_id": folha.pk})

    def delete(self, request, pk):
        tipo = get_object_or_404(TipoDespesa, pk=pk)
        familia = get_object_or_404(CategoriaDespesa, pk=request.data.get("familia_id") or request.query_params.get("familia_id"))
        with transaction.atomic():
            vinculo = get_object_or_404(VinculoTipoDespesa, tipo=tipo, familia=familia)
            auditar("vinculo", vinculo.pk, "REMOVER", antes={"folha_id": vinculo.folha_id}, operador=operador(request))
            vinculo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LotesView(APIView):
    def get(self, request):
        qs = LoteDespesa.objects.exclude(status="CONSOLIDADO").order_by("-id")
        return Response([{"id": x.pk, "nome_arquivo": x.nome_arquivo, "status": x.status, "total_linhas": x.total_linhas, "prontas": x.prontas, "pendentes": x.pendentes, "ignoradas": x.linhas.filter(status="IGNORADO").count(), "criado_em": x.criado_em} for x in qs])

    def post(self, request):
        arquivo = request.FILES.get("arquivo")
        if not arquivo or not arquivo.name.lower().endswith((".xlsx", ".xlsm")):
            raise ValidationError({"arquivo": "Envie uma planilha .xlsx ou .xlsm."})
        try:
            lote = criar_lote(arquivo)
        except IntegrityError:
            return Response({"detail": "Já existe uma captura ativa nesta filial."}, status=status.HTTP_409_CONFLICT)
        except (DjangoValidationError, ValueError) as exc:
            if isinstance(exc, DjangoValidationError):
                if "captura pendente" in " ".join(exc.messages):
                    return Response({"detail": exc.messages[0]}, status=status.HTTP_409_CONFLICT)
                erro_modelo(exc)
            raise ValidationError({"arquivo": str(exc)}) from exc
        return Response({"id": lote.pk, "total_linhas": lote.total_linhas, "prontas": lote.prontas, "pendentes": lote.pendentes, "ignoradas": lote.linhas.filter(status="IGNORADO").count()}, status=status.HTTP_201_CREATED)


class LoteDetailView(APIView):
    def delete(self, request, lote_id):
        with transaction.atomic():
            lote = get_object_or_404(LoteDespesa.objects.select_for_update(), pk=lote_id)
            if lote.status == "CONSOLIDADO" or lote.linhas.filter(status__in=["CONSOLIDADO", "CONFLITO"]).exists():
                raise ValidationError("Uma captura com dados oficiais ou conflitos não pode ser descartada.")
            arquivo = lote.arquivo.name
            lote.delete()
            if arquivo:
                transaction.on_commit(lambda: LoteDespesa._meta.get_field("arquivo").storage.delete(arquivo))
        return Response(status=status.HTTP_204_NO_CONTENT)


class LinhasView(APIView):
    def get(self, request, lote_id):
        lote = get_object_or_404(LoteDespesa, pk=lote_id)
        qs = lote.linhas.order_by("numero")
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        if request.query_params.get("classificacao"):
            escolha = request.query_params["classificacao"].upper()
            qs = qs.filter(dados__classificacao__isnull=True) if escolha == "SEM_CLASSIFICACAO" else qs.filter(dados__classificacao=escolha)
        if request.query_params.get("busca"):
            termo = request.query_params["busca"].strip()
            qs = qs.filter(Q(dados__nome_tipo_origem__icontains=termo) | Q(dados__documento__icontains=termo) | Q(dados__observacoes__icontains=termo) | Q(id_origem__icontains=termo))
        paginator = PageNumberPagination()
        paginator.page_size = 100
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response([{"id": x.pk, "numero": x.numero, "id_origem": x.id_origem, "dados": x.dados, "erros": x.erros, "avisos": x.dados.get("avisos", []), "status": x.status, "movimento_id": x.movimento_id} for x in page])


class ResumoLoteView(APIView):
    def get(self, request, lote_id):
        lote = get_object_or_404(LoteDespesa, pk=lote_id)
        motivos = Counter()
        classificacoes = Counter()
        for situacao, dados, erros in lote.linhas.values_list("status", "dados", "erros").iterator(chunk_size=1000):
            classificacoes[dados.get("classificacao") or ("IGNORADA" if situacao == "IGNORADO" else "SEM_CLASSIFICACAO")] += 1
            for erro in erros:
                motivos[erro.split(":")[0].split(" (")[0]] += 1
        return Response({"lote_id": lote.pk, "nome_arquivo": lote.nome_arquivo, "status": lote.status, "total": lote.total_linhas, "prontas": lote.prontas, "pendentes": lote.pendentes, "ignoradas": lote.linhas.filter(status="IGNORADO").count(), "classificacoes": dict(classificacoes), "motivos": [{"motivo": motivo, "quantidade": quantidade} for motivo, quantidade in motivos.most_common()]})


class RevalidarLoteView(APIView):
    def post(self, request, lote_id):
        lote = get_object_or_404(LoteDespesa, pk=lote_id)
        with lote.arquivo.open("rb") as arquivo:
            novo = criar_lote(SimpleUploadedFile(lote.nome_arquivo, arquivo.read()), lote_existente=lote)
        return Response({"id": novo.pk, "total_linhas": novo.total_linhas, "prontas": novo.prontas, "pendentes": novo.pendentes, "ignoradas": novo.linhas.filter(status="IGNORADO").count()})


class LinhaResolverView(APIView):
    def patch(self, request, lote_id, linha_id):
        linha = get_object_or_404(LinhaDespesa, pk=linha_id, lote_id=lote_id)
        if linha.status in ("CONSOLIDADO", "CONFLITO", "IGNORADO"):
            raise ValidationError("Linha já consolidada.")
        dados = dict(linha.dados)
        antes = {campo: dados.get(campo) for campo in request.data if campo in dados}
        for campo in ("emissao", "vencimento", "pagamento_data"):
            if campo in request.data:
                valor = request.data[campo]
                if valor in (None, "") and campo != "vencimento":
                    dados[campo] = None
                else:
                    try:
                        dados[campo] = date.fromisoformat(str(valor)).isoformat()
                    except ValueError as exc:
                        raise ValidationError({campo: "Data inválida. Use YYYY-MM-DD."}) from exc
        for campo in ("valor", "valor_pago"):
            if campo in request.data:
                valor = numero_decimal(request.data[campo])
                if valor is None or valor < 0:
                    raise ValidationError({campo: "Valor inválido."})
                dados[campo] = str(valor)
        if request.data.get("movimento_id"):
            existente = get_object_or_404(MovimentoDespesa, pk=request.data["movimento_id"], origem="XLSX")
            candidatos = {c["movimento_id"] for c in dados.get("candidatos", [])}
            if dados.get("classificacao") != "AMBIGUA" or existente.pk not in candidatos:
                raise ValidationError({"movimento_id": "O lançamento escolhido não corresponde aos candidatos desta linha."})
            dados["id_origem"] = existente.id_origem
            dados["movimento_id"] = existente.pk
            dados["identidade_situacao"] = "REVISADO_EXISTENTE"
            dados["classificacao"] = "ALTERADA"
        elif request.data.get("confirmar_novo") is True:
            if dados.get("classificacao") != "AMBIGUA":
                raise ValidationError({"identidade": "Confirmação de novo lançamento só é permitida para linha ambígua."})
            if MovimentoDespesa.objects.filter(id_origem=dados.get("id_origem")).exists():
                raise ValidationError({"identidade": "Esta identidade já foi consolidada; escolha o lançamento existente."})
            dados["identidade_situacao"] = "NOVO_REVISADO"
            dados["classificacao"] = "NOVA"
        if "tipo_id" in request.data:
            tipo = get_object_or_404(TipoDespesa, pk=request.data["tipo_id"])
            dados["tipo_id"] = tipo.pk
            dados["nome_tipo_origem"] = tipo.nome
            linha.tipo = tipo
        for campo in ("fornecedor_texto", "documento", "observacoes", "forma"):
            if campo in request.data:
                dados[campo] = str(request.data[campo] or "").strip()
        if "emissao" in request.data and not dados.get("emissao") and any(e.startswith("Data de emissão") for e in linha.erros):
            raise ValidationError({"emissao": "Informe uma data de emissão válida para esta linha."})
        dados["chave_base"] = chave_base_dados(dados)
        dados["hash_conteudo"] = hash_conteudo_dados(dados)
        if not dados.get("id_origem") or not dados.get("tipo_id"):
            raise ValidationError("Identidade e tipo são obrigatórios. Revalide lotes antigos para gerar a identidade.")
        if LinhaDespesa.objects.filter(lote_id=lote_id, id_origem=dados["id_origem"]).exclude(pk=linha.pk).exists():
            raise ValidationError({"id_origem": "ID repetido no lote."})
        resolver_identidade = request.data.get("movimento_id") or request.data.get("confirmar_novo") is True
        outros = []
        for e in linha.erros:
            if e.startswith("Tipo de despesa") and dados.get("tipo_id"):
                continue
            if e.startswith("Data de emissão") and "emissao" in request.data:
                continue
            if e.startswith("Vencimento inválido") and "vencimento" in request.data:
                continue
            if e.startswith("Valor inválido") and "valor" in request.data:
                continue
            if e.startswith("Pagamento sem data") or e.startswith("Valor pago inválido"):
                continue
            if e.startswith("Data de pagamento") and "pagamento_data" in request.data:
                continue
            if resolver_identidade and e.startswith("Identidade ambígua"):
                continue
            outros.append(e)
        if not dados.get("vencimento"):
            outros.append("Vencimento inválido")
        valor = numero_decimal(dados.get("valor"))
        pago = numero_decimal(dados.get("valor_pago")) or Decimal("0")
        if valor is None:
            outros.append("Valor inválido")
        if valor is not None and pago > valor:
            outros.append("Valor pago inválido")
        if pago > 0 and not dados.get("pagamento_data"):
            outros.append("Pagamento sem data válida")
        if not outros and dados.get("classificacao") == "INVALIDA" and not resolver_identidade:
            ocupados = set(linha.lote.linhas.exclude(pk=linha.pk).filter(status="PRONTO").values_list("id_origem", flat=True))
            candidatos = list(MovimentoDespesa.objects.filter(origem="XLSX", chave_base=dados["chave_base"]).exclude(id_origem__in=ocupados).order_by("id"))
            exatos = [item for item in candidatos if (item.dados_origem or {}).get("hash_conteudo") == dados["hash_conteudo"]]
            escolhido = exatos[0] if exatos else candidatos[0] if len(candidatos) == 1 and MovimentoDespesa.objects.filter(origem="XLSX", chave_base=dados["chave_base"]).count() == 1 else None
            if escolhido:
                dados["id_origem"] = escolhido.id_origem
                dados["movimento_id"] = escolhido.pk
                dados["classificacao"] = "EXISTENTE" if exatos else "ALTERADA"
                dados["identidade_situacao"] = "CONTEUDO_EXATO" if exatos else "CONCILIADO_UNICO"
            elif candidatos:
                dados["classificacao"] = "AMBIGUA"
                dados["identidade_situacao"] = "REVISAR"
                dados["candidatos"] = [{"movimento_id": c.pk, "tipo": c.tipo.nome, "documento": c.documento, "vencimento": c.vencimento.isoformat(), "valor": str(c.valor)} for c in candidatos[:100]]
                outros.append("Identidade ambígua: revise antes de consolidar")
            else:
                dados["classificacao"] = "NOVA"
                dados["identidade_situacao"] = "NOVO_REVISADO"
        linha.dados = dados
        linha.id_origem = dados["id_origem"]
        linha.erros = outros
        linha.status = "PRONTO" if not outros else "PENDENTE"
        linha.save()
        lote = linha.lote
        lote.prontas = lote.linhas.filter(status="PRONTO").count()
        lote.pendentes = lote.linhas.filter(status="PENDENTE").count()
        lote.save(update_fields=["prontas", "pendentes"])
        auditar("linha", linha.pk, "VALIDAR", antes=antes, depois={campo: dados.get(campo) for campo in request.data if campo in dados}, operador=operador(request))
        return Response({"id": linha.pk, "status": linha.status, "erros": linha.erros})


class ConsolidarLoteView(APIView):
    def post(self, request, lote_id):
        lote = get_object_or_404(LoteDespesa, pk=lote_id)
        try:
            resultado = consolidar_lote(lote, operador(request))
        except DjangoValidationError as exc:
            erro_modelo(exc)
        return Response(resultado)


class MovimentosView(APIView):
    def get(self, request):
        qs = MovimentoDespesa.objects.select_related("tipo", "fornecedor").prefetch_related("pagamentos").order_by("-vencimento", "-id")
        if request.query_params.get("tipo_id"):
            qs = qs.filter(tipo_id=request.query_params["tipo_id"])
        if request.query_params.get("folha_id"):
            qs = qs.filter(tipo__vinculos__folha_id=request.query_params["folha_id"])
        if request.query_params.get("busca"):
            termo = request.query_params["busca"]
            qs = qs.filter(Q(tipo__nome__icontains=termo) | Q(documento__icontains=termo) | Q(fornecedor_texto__icontains=termo) | Q(observacoes__icontains=termo))
        if request.query_params.get("vencimento_inicio"):
            qs = qs.filter(vencimento__gte=request.query_params["vencimento_inicio"])
        if request.query_params.get("vencimento_fim"):
            qs = qs.filter(vencimento__lte=request.query_params["vencimento_fim"])
        if request.query_params.get("situacao") == "ABERTO":
            qs = qs.annotate(total_pago=Sum("pagamentos__valor")).filter(Q(total_pago__lt=F("valor")) | Q(total_pago__isnull=True))
        return lista_paginada(request, qs.distinct(), MovimentoSerializer)

class MovimentoDetailView(APIView):
    def get(self, request, pk):
        return Response(MovimentoSerializer(get_object_or_404(MovimentoDespesa.objects.prefetch_related("pagamentos"), pk=pk)).data)

    def patch(self, request, pk):
        with transaction.atomic():
            mov = get_object_or_404(MovimentoDespesa.objects.select_for_update(), pk=pk)
            antes_periodos = meses_movimento(mov)
            aliases = {"tipo": "tipo_id", "fornecedor": "fornecedor_id"}
            antes = {aliases.get(campo, campo): str(getattr(mov, aliases.get(campo, campo))) for campo in request.data if campo in MovimentoSerializer.Meta.fields and hasattr(mov, aliases.get(campo, campo))}
            serializer = MovimentoSerializer(mov, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            mov = serializer.save()
            alterados = [campo for campo, valor in antes.items() if str(getattr(mov, campo)) != valor]
            if alterados:
                if mov.origem == "XLSX":
                    mov.campos_manuais = sorted(set(mov.campos_manuais) | set(alterados))
                    mov.save(update_fields=["campos_manuais"])
                auditar("movimento", mov.pk, "EDITAR", antes=antes, depois={campo: str(getattr(mov, campo)) for campo in alterados}, operador=operador(request))
                reconstruir_periodos(antes_periodos | meses_movimento(mov))
        return Response(MovimentoSerializer(mov).data)

    def delete(self, request, pk):
        with transaction.atomic():
            mov = get_object_or_404(MovimentoDespesa.objects.select_for_update(), pk=pk)
            periodos = meses_movimento(mov)
            auditar("movimento", mov.pk, "EXCLUIR", antes={"tipo_id": mov.tipo_id, "vencimento": mov.vencimento.isoformat(), "valor": str(mov.valor)}, operador=operador(request))
            mov.delete()
            reconstruir_periodos(periodos)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PagamentosView(APIView):
    """A inclusão de pagamentos ocorre somente durante a importação da fonte."""


class PagamentoDetailView(APIView):
    def patch(self, request, pk):
        with transaction.atomic():
            pag = get_object_or_404(PagamentoDespesa.objects.select_for_update(), pk=pk)
            antes = {"data": pag.data.isoformat(), "valor": str(pag.valor), "forma": pag.forma}
            mes_anterior = mes_inicio(pag.data)
            serializer = PagamentoSerializer(pag, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            pag = serializer.save()
            depois = {"data": pag.data.isoformat(), "valor": str(pag.valor), "forma": pag.forma}
            alterados = [campo for campo in antes if antes[campo] != depois[campo]]
            if alterados:
                if pag.origem == "XLSX":
                    pag.campos_manuais = sorted(set(pag.campos_manuais) | set(alterados))
                    pag.save(update_fields=["campos_manuais"])
                auditar("pagamento", pag.pk, "EDITAR", antes, depois, operador(request))
                reconstruir_periodos({(mes_anterior, "PAGAMENTO"), (mes_inicio(pag.data), "PAGAMENTO")})
        return Response(PagamentoSerializer(pag).data)

    def delete(self, request, pk):
        with transaction.atomic():
            pag = get_object_or_404(PagamentoDespesa.objects.select_for_update(), pk=pk)
            mes = mes_inicio(pag.data)
            auditar("pagamento", pag.pk, "EXCLUIR", antes={"data": pag.data.isoformat(), "valor": str(pag.valor)}, operador=operador(request))
            pag.delete()
            reconstruir_periodos({(mes, "PAGAMENTO")})
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConflitosView(APIView):
    def get(self, request):
        qs = ConflitoDespesa.objects.select_related("movimento", "linha").filter(resolvido=False).order_by("-id")
        return Response([{"id": c.pk, "movimento_id": c.movimento_id, "linha_id": c.linha_id, "campo": c.campo, "valor_atual": c.valor_atual, "valor_origem": c.valor_origem} for c in qs[:500]])


class ResolverConflitoView(APIView):
    def post(self, request, pk):
        decisao = request.data.get("decisao")
        if decisao not in ("MANTER_MANUAL", "USAR_ORIGEM"):
            raise ValidationError({"decisao": "Use MANTER_MANUAL ou USAR_ORIGEM."})
        with transaction.atomic():
            c = get_object_or_404(ConflitoDespesa.objects.select_for_update(), pk=pk, resolvido=False)
            mov = c.movimento
            periodos = meses_movimento(mov)
            if decisao == "USAR_ORIGEM":
                campo = c.campo
                if campo == "pagamento_total":
                    raise ValidationError("Revise os pagamentos e o valor da movimentação antes de usar o total da origem.")
                alvo = mov
                if campo.startswith("pagamento_"):
                    campo = campo.removeprefix("pagamento_")
                    alvo = get_object_or_404(PagamentoDespesa, id_origem=f"{mov.id_origem}:1")
                valor = c.valor_origem
                if campo in ("vencimento", "emissao", "data") and valor:
                    valor = date.fromisoformat(valor)
                if campo in ("valor",) and valor is not None:
                    valor = Decimal(str(valor))
                setattr(alvo, campo, valor)
                alvo.campos_manuais = [x for x in alvo.campos_manuais if x != campo]
                alvo.full_clean()
                alvo.save()
                auditar("pagamento" if alvo != mov else "movimento", alvo.pk, "RESOLVER_CONFLITO", antes={campo: c.valor_atual}, depois={campo: c.valor_origem}, operador=operador(request))
                periodos |= meses_movimento(mov)
            c.resolvido = True
            c.resolvido_em = timezone.now()
            c.save(update_fields=["resolvido", "resolvido_em"])
            if not c.linha.conflitodespesa_set.filter(resolvido=False).exists():
                c.linha.status = "CONSOLIDADO"
                c.linha.save(update_fields=["status"])
            reconstruir_periodos(periodos)
        return Response({"id": c.pk, "resolvido": True})


class AuditoriaView(APIView):
    def get(self, request):
        entidade = request.query_params.get("entidade")
        objeto_id = request.query_params.get("id")
        if not entidade or not objeto_id:
            raise ValidationError("Informe entidade e id.")
        qs = AuditoriaDespesa.objects.filter(entidade=entidade, entidade_id=objeto_id).order_by("-id")[:100]
        return Response([{"acao": a.acao, "antes": a.antes, "depois": a.depois, "operador": a.operador, "criado_em": a.criado_em} for a in qs])


class BIView(APIView):
    def get(self, request):
        try:
            return Response(obter_bi(request.query_params))
        except (ValueError, DjangoValidationError) as exc:
            raise ValidationError(str(exc)) from exc


def _bi_dados(request):
    try:
        return obter_bi(request.query_params)
    except (ValueError, DjangoValidationError) as exc:
        raise ValidationError(str(exc)) from exc


def _bi_folha(dados, folha_id):
    try:
        identificador = int(folha_id)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"folha_id": "Informe uma categoria folha válida."}) from exc
    folha = next((no for no in dados["categorias"] if no["id"] == identificador and no["folha"] and no["id"] != dados["familia"]["id"]), None)
    if folha is None:
        raise ValidationError({"folha_id": "A categoria não é folha desta família."})
    return folha


class BITiposView(APIView):
    def get(self, request):
        dados = _bi_dados(request)
        categorias = {no["id"]: no for no in dados["categorias"]}
        categoria_id = request.query_params.get("categoria_id")
        folha_id = request.query_params.get("folha_id")
        if categoria_id:
            try:
                categoria = categorias.get(int(categoria_id))
            except (TypeError, ValueError):
                categoria = None
            if categoria is None:
                raise ValidationError({"categoria_id": "A categoria não pertence à família selecionada."})
        elif folha_id:
            categoria = _bi_folha(dados, folha_id)
        else:
            categoria = categorias[dados["familia"]["id"]]

        folhas = set()
        for no in dados["categorias"]:
            if not no["folha"]:
                continue
            atual = no
            while atual:
                if atual["id"] == categoria["id"]:
                    folhas.add(no["id"])
                    break
                atual = categorias.get(atual["pai_id"])
        tipos = [tipo for tipo in dados["tipos"] if tipo["folha_id"] in folhas]
        busca = request.query_params.get("busca", "").strip().casefold()
        if busca:
            tipos = [tipo for tipo in tipos if busca in tipo["nome"].casefold()]
        def chave_ordenacao(tipo):
            valor = tipo["total"] if dados["visao"] == "mensal" else tipo["valores"].get(str(dados["ano"]))
            return (valor is None, -Decimal(valor) if valor is not None else Decimal("0"), tipo["nome"].casefold(), tipo["id"])
        tipos.sort(key=chave_ordenacao)
        paginator = PageNumberPagination()
        paginator.page_size = 100
        pagina = paginator.paginate_queryset(tipos, request)
        return paginator.get_paginated_response({
            "familia": dados["familia"], "categoria": categoria,
            "folha": categoria if categoria["folha"] and categoria["id"] != dados["familia"]["id"] else None,
            "visao": dados["visao"],
            "base": dados["base"], "ano": dados["ano"],
            "anos_disponiveis": dados["anos_disponiveis"], "periodos": dados["periodos"],
            "periodo_equivalente": dados["periodo_equivalente"],
            "mes_aberto": dados["mes_aberto"], "ano_parcial": dados["ano_parcial"],
            "estado_atualizacao": dados["estado_atualizacao"], "desatualizado": dados["desatualizado"],
            "data_corte": dados["data_corte"], "tipos": pagina,
        })


class BIMovimentosView(APIView):
    """Lançamentos ou pagamentos que compõem exatamente uma célula disponível."""

    def get(self, request):
        dados = _bi_dados(request)
        folha = _bi_folha(dados, request.query_params.get("folha_id"))
        try:
            tipo_id = int(request.query_params.get("tipo_id"))
        except (TypeError, ValueError) as exc:
            raise ValidationError({"tipo_id": "Informe um Tipo de Despesa válido."}) from exc
        tipo = next((item for item in dados["tipos"] if item["id"] == tipo_id and item["folha_id"] == folha["id"]), None)
        if tipo is None:
            raise ValidationError({"tipo_id": "O tipo não pertence a esta folha na classificação atual."})
        periodo = next((item for item in dados["periodos"] if item["periodo"] == request.query_params.get("periodo")), None)
        if periodo is None:
            raise ValidationError({"periodo": "Período fora da visão selecionada."})
        if tipo["valores"][periodo["periodo"]] is None:
            raise ValidationError({"periodo": "O agregado deste período está indisponível."})
        intervalos = periodo["intervalos_detalhe"]
        filtro_datas = Q(pk__in=[])
        for intervalo in intervalos:
            campo = "vencimento" if dados["base"] == "VENCIMENTO" else "data"
            filtro_datas |= Q(**{f"{campo}__gte": intervalo["inicio"], f"{campo}__lte": intervalo["fim"]})
        movimentos = MovimentoDespesa.objects.filter(tipo_id=tipo_id).select_related("tipo", "fornecedor").prefetch_related("pagamentos")
        if dados["base"] == "VENCIMENTO":
            movimentos = movimentos.filter(filtro_datas)
            total = movimentos.aggregate(total=Sum("valor"))["total"] or Decimal("0")
        else:
            pagamentos = PagamentoDespesa.objects.filter(movimento__tipo_id=tipo_id).filter(filtro_datas)
            total = pagamentos.aggregate(total=Sum("valor"))["total"] or Decimal("0")
            movimentos = movimentos.filter(pk__in=pagamentos.values("movimento_id"))
        movimentos = movimentos.order_by("-vencimento", "-id")
        paginator = PageNumberPagination()
        paginator.page_size = 100
        pagina = paginator.paginate_queryset(movimentos, request)
        resultado = MovimentoSerializer(pagina, many=True).data
        if dados["base"] == "PAGAMENTO":
            por_movimento = {}
            for pagamento in PagamentoDespesa.objects.filter(movimento_id__in=[item.pk for item in pagina]).filter(filtro_datas).values("movimento_id").annotate(total=Sum("valor")):
                por_movimento[pagamento["movimento_id"]] = pagamento["total"]
            for item in resultado:
                item["valor_periodo"] = str(por_movimento[item["id"]])
                item["pagamentos_periodo"] = [p for p in item["pagamentos"] if any(i["inicio"] <= p["data"] <= i["fim"] for i in intervalos)]
        else:
            for item in resultado:
                item["valor_periodo"] = item["valor"]
        resposta = paginator.get_paginated_response(resultado)
        resposta.data.update({
            "tipo": {"id": tipo["id"], "nome": tipo["nome"]}, "folha": {"id": folha["id"], "nome": folha["nome"]},
            "periodo": periodo, "base": dados["base"], "total_filtrado": str(total),
            "total_agregado": tipo["valores"][periodo["periodo"]], "conciliado": total == Decimal(tipo["valores"][periodo["periodo"]]),
        })
        return resposta
