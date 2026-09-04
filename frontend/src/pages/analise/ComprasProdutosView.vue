<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AlertTriangle, PackageSearch, Search } from 'lucide-vue-next'
import RemoteSearchSelect from '@/components/ui/RemoteSearchSelect.vue'
import { getApiBaseUrl } from '@/services/firebirdSync'
import {
  MESES,
  estiloCelulaFinanceira,
  formatarQuantidade,
  formatarValor,
  indicesIgnoradosMesAberto,
  mapaQuartis,
  mesEstaAberto,
  numeroFinanceiro,
  tooltipMesAberto,
} from './analiseMensalUtils'

const API_BASE_URL = getApiBaseUrl()
const ENDPOINT = `${API_BASE_URL}/api/analise/categorias/produtos/compras/`
const METADATA_ENDPOINT = `${API_BASE_URL}/api/analise/categorias/compras/`
const CATEGORIAS_ENDPOINT = `${API_BASE_URL}/api/cadastros/plano-contas/opcoes`
const FORNECEDORES_ENDPOINT = `${API_BASE_URL}/api/cadastros/fornecedores`
const route = useRoute()
const router = useRouter()

const familias = ref([])
const anos = ref([])
const familiaSelecionada = ref(String(route.query.raiz_id || ''))
const categoriaSelecionada = ref(String(route.query.categoria_id || route.query.raiz_id || ''))
const anoSelecionado = ref(Number(route.query.ano) || null)
const metrica = ref(['valor', 'quantidade', 'custo_medio'].includes(route.query.metrica) ? route.query.metrica : 'valor')
const fornecedorSelecionado = ref(String(route.query.fornecedor_id || ''))
const incluirInativos = ref(['1', 'true'].includes(String(route.query.incluir_inativos || '').toLowerCase()))
const busca = ref(String(route.query.search || ''))
const buscaAplicada = ref(busca.value.trim())
const pagina = ref(Math.max(1, Number(route.query.page) || 1))
const dados = ref(null)
const loadingInicial = ref(true)
const loading = ref(false)
const erro = ref('')
const pronto = ref(false)
let debounceBusca = null
let requisicaoAtual = null

const categoriaControle = computed({
  get() {
    if (!familiaSelecionada.value || categoriaSelecionada.value === familiaSelecionada.value) return ''
    return categoriaSelecionada.value
  },
  set(valor) {
    categoriaSelecionada.value = String(valor || familiaSelecionada.value || '')
  },
})

const categoriaLabel = computed(() => {
  const categoria = dados.value?.categoria
  if (!categoria || String(categoria.id_conta) !== categoriaSelecionada.value) return ''
  return `${categoria.codigo_hierarquico} ${categoria.nome_conta}`
})

const fornecedorLabel = computed(() => {
  const fornecedor = dados.value?.fornecedor
  if (!fornecedor || String(fornecedor.id_fornecedor) !== fornecedorSelecionado.value) return ''
  return `${fornecedor.id_fornecedor} - ${fornecedor.nome_fornecedor}`
})

const quartisPorProduto = computed(() => new Map(
  (dados.value?.linhas ?? []).map((linha) => [
    linha.id_produto,
    mapaQuartis(linha.valores ?? [], indicesIgnoradosMesAberto(dados.value)),
  ]),
))

const quartisPorProdutoUnidade = computed(() => {
  const rankings = new Map()
  for (const linha of dados.value?.linhas ?? []) {
    for (const unidade of linha.unidades ?? []) {
      rankings.set(
        `${linha.id_produto}:${unidade.id_unidade}`,
        mapaQuartis(unidade.valores ?? [], indicesIgnoradosMesAberto(dados.value)),
      )
    }
  }
  return rankings
})

const paginacao = computed(() => dados.value?.paginacao ?? {
  pagina: pagina.value,
  por_pagina: 100,
  total_produtos: 0,
  total_paginas: 1,
})

function formatFornecedorOption(item) {
  const nome = String(item.nome_gerencial || '').trim() || item.nome_fornecedor
  return `${item.id_fornecedor} - ${nome}`
}

function trocarFamilia() {
  categoriaSelecionada.value = familiaSelecionada.value
}

function statusInativo(status) {
  return String(status || '').trim().toUpperCase() === 'INATIVO'
}

function estiloValor(linha, valor, indice) {
  return estiloCelulaFinanceira(
    quartisPorProduto.value.get(linha.id_produto),
    valor,
    true,
    mesEstaAberto(dados.value, indice),
  )
}

function estiloCusto(linha, unidade, valor, indice) {
  const chave = `${linha.id_produto}:${unidade.id_unidade}`
  return estiloCelulaFinanceira(
    quartisPorProdutoUnidade.value.get(chave),
    valor,
    true,
    mesEstaAberto(dados.value, indice),
  )
}

function sincronizarUrl() {
  const query = {}
  if (familiaSelecionada.value) query.raiz_id = familiaSelecionada.value
  if (categoriaSelecionada.value) query.categoria_id = categoriaSelecionada.value
  if (anoSelecionado.value) query.ano = String(anoSelecionado.value)
  query.metrica = metrica.value
  if (fornecedorSelecionado.value) query.fornecedor_id = fornecedorSelecionado.value
  if (incluirInativos.value) query.incluir_inativos = '1'
  if (buscaAplicada.value) query.search = buscaAplicada.value
  if (pagina.value > 1) query.page = String(pagina.value)
  router.replace({ query })
}

async function carregarOpcoes() {
  loadingInicial.value = true
  erro.value = ''
  try {
    const [resFamilias, resMetadata] = await Promise.all([
      fetch(`${API_BASE_URL}/api/cadastros/plano-contas/raizes`),
      fetch(METADATA_ENDPOINT),
    ])
    if (!resFamilias.ok || !resMetadata.ok) throw new Error('Não foi possível carregar as opções da análise.')
    familias.value = await resFamilias.json()
    const metadata = await resMetadata.json()
    anos.value = metadata.anos_disponiveis ?? []
    if (!anos.value.includes(anoSelecionado.value)) anoSelecionado.value = anos.value[0] ?? null
    const familiaExiste = familias.value.some(
      (familia) => String(familia.id_conta) === familiaSelecionada.value,
    )
    if (familiaSelecionada.value && !familiaExiste) {
      familiaSelecionada.value = ''
      categoriaSelecionada.value = ''
    } else if (familiaSelecionada.value && !categoriaSelecionada.value) {
      categoriaSelecionada.value = familiaSelecionada.value
    }
  } catch (e) {
    erro.value = e?.message || 'Falha ao carregar a análise.'
  } finally {
    loadingInicial.value = false
    pronto.value = true
  }
  await carregarRelatorio()
}

async function carregarRelatorio() {
  if (!pronto.value || !familiaSelecionada.value || !categoriaSelecionada.value || !anoSelecionado.value) {
    dados.value = null
    sincronizarUrl()
    return
  }
  if (requisicaoAtual) requisicaoAtual.abort()
  const requisicao = new AbortController()
  requisicaoAtual = requisicao
  loading.value = true
  erro.value = ''
  sincronizarUrl()
  try {
    const params = new URLSearchParams({
      ano: String(anoSelecionado.value),
      raiz_id: familiaSelecionada.value,
      categoria_id: categoriaSelecionada.value,
      metrica: metrica.value,
      incluir_inativos: incluirInativos.value ? '1' : '0',
      page: String(pagina.value),
    })
    if (fornecedorSelecionado.value) params.set('fornecedor_id', fornecedorSelecionado.value)
    if (buscaAplicada.value) params.set('search', buscaAplicada.value)
    const response = await fetch(`${ENDPOINT}?${params}`, { signal: requisicao.signal })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(payload.detail || `Erro ${response.status}`)
    dados.value = payload
    if (pagina.value !== payload.paginacao.pagina) pagina.value = payload.paginacao.pagina
  } catch (e) {
    if (e?.name === 'AbortError') return
    dados.value = null
    erro.value = e?.message || 'Falha ao processar o relatório.'
  } finally {
    if (requisicaoAtual === requisicao) {
      requisicaoAtual = null
      loading.value = false
    }
  }
}

function irParaPagina(destino) {
  const limite = Math.max(1, paginacao.value.total_paginas)
  pagina.value = Math.min(limite, Math.max(1, destino))
}

watch(busca, (valor) => {
  if (debounceBusca) clearTimeout(debounceBusca)
  debounceBusca = setTimeout(() => { buscaAplicada.value = String(valor || '').trim() }, 350)
})
watch(
  [familiaSelecionada, categoriaSelecionada, anoSelecionado, metrica, fornecedorSelecionado, incluirInativos, buscaAplicada],
  () => {
    if (!pronto.value) return
    if (pagina.value !== 1) pagina.value = 1
    else carregarRelatorio()
  },
)
watch(pagina, () => { if (pronto.value) carregarRelatorio() })
onMounted(carregarOpcoes)
onBeforeUnmount(() => {
  if (debounceBusca) clearTimeout(debounceBusca)
  if (requisicaoAtual) requisicaoAtual.abort()
})
</script>

<template>
  <div class="flex flex-col gap-5">
    <div>
      <h1 class="text-xl font-bold text-gray-900">Compras por Produto</h1>
      <p class="mt-0.5 text-sm text-gray-400">Detalhamento mensal dos produtos vinculados à categoria selecionada.</p>
    </div>

    <div class="rounded-xl border border-gray-200 bg-white shadow-sm">
      <div class="flex flex-wrap items-end gap-3 border-b border-gray-100 bg-gray-50/70 px-4 py-3">
        <label class="flex min-w-[200px] flex-1 flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
          Família do plano de contas
          <select v-model="familiaSelecionada" class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium normal-case text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300" :disabled="loadingInicial || !anos.length" @change="trocarFamilia">
            <option value="">Selecione uma família</option>
            <option v-for="familia in familias" :key="familia.id_conta" :value="String(familia.id_conta)">{{ familia.codigo_hierarquico }} {{ familia.nome_conta }}</option>
          </select>
        </label>

        <label class="flex min-w-[220px] flex-1 flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
          Categoria
          <RemoteSearchSelect v-model="categoriaControle" :endpoint="CATEGORIAS_ENDPOINT" value-field="id_conta" label-field="label" all-label="Toda a família" search-placeholder="Pesquisar categoria..." :min-chars="1" :limit="50" :extra-params="{ raiz_id: familiaSelecionada }" resolve-param="ids" :initial-label="categoriaLabel" :disabled="!familiaSelecionada || loadingInicial" button-class="flex h-[34px] w-full items-center justify-between gap-2 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium normal-case text-gray-700 hover:bg-gray-50 disabled:opacity-60" />
        </label>

        <label class="flex min-w-[220px] flex-1 flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
          Fornecedor
          <RemoteSearchSelect v-model="fornecedorSelecionado" :endpoint="FORNECEDORES_ENDPOINT" value-field="id_fornecedor" :format-option-label="formatFornecedorOption" all-label="Todos os fornecedores" search-placeholder="Pesquisar fornecedor..." :min-chars="2" :limit="20" :initial-label="fornecedorLabel" :disabled="loadingInicial" button-class="flex h-[34px] w-full items-center justify-between gap-2 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium normal-case text-gray-700 hover:bg-gray-50 disabled:opacity-60" />
        </label>

        <label class="flex w-24 flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
          Ano
          <select v-model="anoSelecionado" class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300" :disabled="loadingInicial || !anos.length"><option v-for="ano in anos" :key="ano" :value="ano">{{ ano }}</option></select>
        </label>

        <div class="flex flex-col gap-1">
          <span class="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Métrica</span>
          <div class="flex h-[34px] overflow-hidden rounded-md border border-gray-200 text-xs font-semibold">
            <button type="button" class="px-3 transition-colors" :class="metrica === 'valor' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" @click="metrica = 'valor'">Valor</button>
            <button type="button" class="border-l border-gray-200 px-3 transition-colors" :class="metrica === 'quantidade' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" @click="metrica = 'quantidade'">Quantidade</button>
            <button type="button" class="border-l border-gray-200 px-3 transition-colors" :class="metrica === 'custo_medio' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" @click="metrica = 'custo_medio'">Custo médio</button>
          </div>
        </div>

        <label class="flex h-[34px] cursor-pointer items-center gap-2 rounded-md border border-gray-200 bg-white px-3 text-xs font-medium text-gray-600">
          <input v-model="incluirInativos" type="checkbox" class="h-3.5 w-3.5 rounded border-gray-300 accent-[#373435]" />
          Incluir inativos ({{ dados?.inativos_ocultos ?? 0 }})
        </label>
      </div>

      <div class="flex items-center border-b border-gray-100 px-4 py-2.5">
        <div class="flex w-full max-w-sm items-center gap-2 rounded-md border border-gray-200 bg-white px-3 py-2">
          <Search class="h-4 w-4 text-gray-400" />
          <input v-model="busca" type="search" class="w-full border-0 bg-transparent p-0 text-xs text-gray-700 outline-none" placeholder="Buscar por código ou nome do produto" />
        </div>
      </div>

      <div v-if="dados?.desatualizado" class="flex items-start gap-2 border-b border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800"><AlertTriangle class="mt-0.5 h-4 w-4 shrink-0" /><span>Existem períodos aguardando atualização. Os últimos valores válidos continuam visíveis.</span></div>
      <div v-if="erro" class="border-b border-red-100 bg-red-50 px-4 py-3 text-xs font-semibold text-red-700">{{ erro }}</div>
      <div v-if="loadingInicial || loading" class="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center"><div class="h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-[#373435]" /><div><p class="text-sm font-medium text-gray-700">Processando análise</p><p class="mt-1 text-xs text-gray-400">A consulta pode levar alguns segundos.</p></div></div>
      <div v-else-if="!anos.length && !erro" class="flex flex-col items-center justify-center px-6 py-16 text-center"><AlertTriangle class="mb-3 h-7 w-7 text-amber-500" /><p class="text-sm font-medium text-gray-600">Agregado analítico ainda não construído</p></div>
      <div v-else-if="!familiaSelecionada && !erro" class="flex flex-col items-center justify-center px-6 py-16 text-center"><PackageSearch class="mb-3 h-8 w-8 text-gray-300" /><p class="text-sm font-medium text-gray-600">Selecione uma família</p><p class="mt-1 text-xs text-gray-400">Depois, refine por categoria e fornecedor.</p></div>
      <div v-else-if="dados && !dados.linhas.length" class="flex flex-col items-center justify-center px-6 py-16 text-center"><PackageSearch class="mb-3 h-8 w-8 text-gray-300" /><p class="text-sm font-medium text-gray-600">Nenhum produto encontrado</p><p class="mt-1 text-xs text-gray-400">Revise a categoria, o fornecedor, a busca ou o filtro de inativos.</p></div>

      <template v-else-if="dados">
        <div class="app-scrollbar overflow-x-auto">
          <table class="w-full border-collapse text-xs">
            <thead><tr class="border-b border-gray-100 bg-white">
              <th class="sticky left-0 z-20 min-w-[300px] bg-white px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-400 shadow-[1px_0_0_#f3f4f6]">Produto</th>
              <th v-for="(mes, indice) in MESES" :key="mes" class="min-w-[100px] px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400" :title="tooltipMesAberto(dados, indice)" :aria-label="tooltipMesAberto(dados, indice) || mes">{{ mes }}</th>
              <th class="min-w-[120px] bg-gray-50 px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-600">Total</th>
            </tr></thead>
            <tbody>
              <tr v-for="linha in dados.linhas" :key="linha.id_produto" class="border-b border-gray-50 last:border-0 hover:bg-gray-50/70">
                <td class="sticky left-0 z-10 bg-white px-4 py-2.5 shadow-[1px_0_0_#f3f4f6]"><div class="flex items-center gap-2"><span class="font-mono text-[10px] text-gray-400">{{ linha.id_produto }}</span><span class="font-medium text-gray-700">{{ linha.nome_produto }}</span><span v-if="statusInativo(linha.status)" class="ml-auto rounded-full bg-amber-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-amber-700">Inativo</span></div></td>

                <template v-if="metrica === 'valor'">
                  <td v-for="(valor, indice) in linha.valores" :key="indice" class="px-3 py-2.5 text-right font-mono tabular-nums" :class="numeroFinanceiro(valor) === null ? 'text-gray-300' : 'text-gray-700'" :style="estiloValor(linha, valor, indice)">{{ formatarValor(valor) }}</td>
                  <td class="bg-gray-50 px-4 py-2.5 text-right font-mono font-semibold tabular-nums text-gray-800">{{ formatarValor(linha.total) }}</td>
                </template>

                <template v-else>
                  <td v-for="indice in 12" :key="indice" class="px-3 py-2 text-right align-top font-mono tabular-nums text-gray-600">
                    <div v-if="linha.unidades.length" class="space-y-0.5">
                      <div v-for="unidade in linha.unidades" :key="unidade.id_unidade" class="whitespace-nowrap" :style="metrica === 'custo_medio' ? estiloCusto(linha, unidade, unidade.valores[indice - 1], indice - 1) : {}">
                        {{ metrica === 'custo_medio' ? formatarValor(unidade.valores[indice - 1], 2) : formatarQuantidade(unidade.valores[indice - 1]) }}
                        <span class="text-[9px] font-semibold text-gray-400">{{ metrica === 'custo_medio' ? `R$/${unidade.sigla}` : unidade.sigla }}</span>
                      </div>
                    </div>
                    <span v-else class="text-gray-300">-</span>
                  </td>
                  <td class="bg-gray-50 px-4 py-2 text-right align-top font-mono font-semibold tabular-nums text-gray-800">
                    <div v-if="linha.unidades.length" class="space-y-0.5"><div v-for="unidade in linha.unidades" :key="unidade.id_unidade" class="whitespace-nowrap">{{ metrica === 'custo_medio' ? formatarValor(unidade.total, 2) : formatarQuantidade(unidade.total) }} <span class="text-[9px] text-gray-500">{{ metrica === 'custo_medio' ? `R$/${unidade.sigla}` : unidade.sigla }}</span></div></div>
                    <span v-else class="text-gray-300">-</span>
                  </td>
                </template>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 px-4 py-3 text-xs text-gray-500">
          <span>{{ paginacao.total_produtos }} produto(s) · página {{ paginacao.pagina }} de {{ paginacao.total_paginas }}</span>
          <div class="flex gap-2"><button type="button" class="rounded-md border border-gray-200 px-3 py-1.5 font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40" :disabled="paginacao.pagina <= 1" @click="irParaPagina(paginacao.pagina - 1)">Anterior</button><button type="button" class="rounded-md border border-gray-200 px-3 py-1.5 font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40" :disabled="paginacao.pagina >= paginacao.total_paginas" @click="irParaPagina(paginacao.pagina + 1)">Próxima</button></div>
        </div>
      </template>
    </div>
  </div>
</template>
