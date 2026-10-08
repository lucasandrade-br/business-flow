<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AlertTriangle, PackageSearch, RefreshCw, Search } from 'lucide-vue-next'
import RemoteSearchSelect from '@/components/ui/RemoteSearchSelect.vue'
import { getApiBaseUrl } from '@/services/firebirdSync'
import SnapshotDetails from './SnapshotDetails.vue'
import VariacoesCompactas from './VariacoesCompactas.vue'
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
const ENDPOINT = `${API_BASE_URL}/api/analise/categorias/produtos/vendas/`
const ENDPOINT_SEMANAL = `${ENDPOINT}semanal/`
const ENDPOINT_ANUAL = `${ENDPOINT}anual/`
const METADATA_ENDPOINT = `${API_BASE_URL}/api/analise/categorias/vendas/`
const METADATA_SEMANAL_ENDPOINT = `${METADATA_ENDPOINT}semanal/`
const METADATA_ANUAL_ENDPOINT = `${METADATA_ENDPOINT}anual/`
const CATEGORIAS_ENDPOINT = `${API_BASE_URL}/api/cadastros/plano-contas/opcoes`
const route = useRoute()
const router = useRouter()

const familias = ref([])
const anos = ref([])
const anosAnuais = ref([])
const semanas = ref([])
const visao = ref(['semanal', 'anual'].includes(route.query.visao) ? route.query.visao : 'mensal')
const anosDaVisao = computed(() => visao.value === 'anual' ? anosAnuais.value : anos.value)
const semanaSelecionada = ref(String(route.query.semana_inicio || ''))
const equivalenteSemanal = ref(!['0', 'false'].includes(String(route.query.periodo_equivalente || '1').toLowerCase()))
const equivalenteMensal = ref(visao.value === 'mensal' && ['1', 'true'].includes(String(route.query.periodo_equivalente || '').toLowerCase()))
const equivalenteAnual = ref(!['0', 'false'].includes(String(route.query.periodo_equivalente || '1').toLowerCase()))
const ultimaAtualizacaoSemanal = ref(null)
const familiaSelecionada = ref(String(route.query.raiz_id || ''))
const categoriaSelecionada = ref(String(route.query.categoria_id || route.query.raiz_id || ''))
const anoSelecionado = ref(Number(route.query.ano) || null)
const metrica = ref(['valor', 'quantidade'].includes(route.query.metrica) ? route.query.metrica : 'valor')
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
let intervaloAtualizacao = null

function dataCurta(valor) {
  if (!valor) return ''
  const [ano, mes, dia] = valor.split('-')
  return `${dia}/${mes}/${ano}`
}

function rotuloSemana(inicio) {
  const fim = new Date(`${inicio}T12:00:00`)
  fim.setDate(fim.getDate() + 6)
  const fimIso = `${fim.getFullYear()}-${String(fim.getMonth() + 1).padStart(2, '0')}-${String(fim.getDate()).padStart(2, '0')}`
  return `${dataCurta(inicio)} a ${dataCurta(fimIso)}`
}

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
  if (!categoria || String(categoria.id_conta) !== String(categoriaSelecionada.value)) return ''
  return `${categoria.codigo_hierarquico} ${categoria.nome_conta}`
})

const tituloVariacoesAnuais = computed(() => {
  const anos = dados.value?.anos?.map((periodo) => periodo.ano) ?? []
  const transicoes = anos.slice(0, -2).map((ano, indice) => `${ano}→${anos[indice + 1]}`)
  const media = transicoes.length ? `Média das variações ${transicoes.join(' e ')}.` : 'Média histórica indisponível: menos de dois anos anteriores.'
  const recente = anos.length > 1 ? `Recente: ${anos.at(-2)}→${anos.at(-1)}.` : 'Recente indisponível: sem ano anterior.'
  return `${media} ${recente}`
})

const quartisPorProduto = computed(() => new Map(
  (dados.value?.linhas ?? []).map((linha) => [
    linha.id_produto,
    mapaQuartis(linha.valores ?? [], visao.value === 'anual'
      ? (dados.value?.ano_parcial && !dados.value?.periodo_equivalente ? [linha.valores.length - 1] : [])
      : dados.value?.periodo_equivalente ? [] : indicesIgnoradosMesAberto(dados.value)),
  ]),
))

const paginacao = computed(() => dados.value?.paginacao ?? {
  pagina: pagina.value,
  por_pagina: 100,
  total_produtos: 0,
  total_paginas: 1,
})

function trocarFamilia() {
  categoriaSelecionada.value = familiaSelecionada.value
}

function selecionarMetrica(valor) {
  metrica.value = valor
}

function estiloLinha(linha, valor, indice) {
  return estiloCelulaFinanceira(
    quartisPorProduto.value.get(linha.id_produto),
    valor,
    false,
    !dados.value?.periodo_equivalente && (visao.value === 'anual'
      ? dados.value?.ano_parcial && indice === dados.value?.anos?.length - 1
      : mesEstaAberto(dados.value, indice)),
  )
}

function statusInativo(status) {
  return String(status || '').trim().toUpperCase() === 'INATIVO'
}

function sincronizarUrl() {
  const query = {}
  if (familiaSelecionada.value) query.raiz_id = familiaSelecionada.value
  if (categoriaSelecionada.value) query.categoria_id = categoriaSelecionada.value
  if (visao.value === 'semanal') {
    query.visao = 'semanal'
    if (semanaSelecionada.value) query.semana_inicio = semanaSelecionada.value
    query.periodo_equivalente = equivalenteSemanal.value ? '1' : '0'
  } else if (visao.value === 'anual') {
    query.visao = 'anual'
    if (anoSelecionado.value) query.ano = String(anoSelecionado.value)
    query.periodo_equivalente = equivalenteAnual.value ? '1' : '0'
  } else {
    if (anoSelecionado.value) query.ano = String(anoSelecionado.value)
    if (equivalenteMensal.value) query.periodo_equivalente = '1'
  }
  query.metrica = metrica.value
  if (incluirInativos.value) query.incluir_inativos = '1'
  if (buscaAplicada.value) query.search = buscaAplicada.value
  if (pagina.value > 1) query.page = String(pagina.value)
  router.replace({ query })
}

async function carregarOpcoes() {
  loadingInicial.value = true
  erro.value = ''
  try {
    const [resFamilias, resMetadata, resSemanas, resAnual] = await Promise.all([
      fetch(`${API_BASE_URL}/api/cadastros/plano-contas/raizes`),
      fetch(METADATA_ENDPOINT),
      fetch(METADATA_SEMANAL_ENDPOINT).catch(() => null),
      fetch(METADATA_ANUAL_ENDPOINT),
    ])
    if (!resFamilias.ok || !resMetadata.ok || !resAnual.ok) throw new Error('Não foi possível carregar as opções da análise.')

    familias.value = await resFamilias.json()
    const metadata = await resMetadata.json()
    anos.value = metadata.anos_disponiveis ?? []
    anosAnuais.value = (await resAnual.json()).anos_disponiveis ?? []
    if (!anosDaVisao.value.includes(anoSelecionado.value)) anoSelecionado.value = anosDaVisao.value[0] ?? null
    if (resSemanas?.ok) {
      const metadataSemanal = await resSemanas.json()
      semanas.value = metadataSemanal.semanas_disponiveis ?? []
      if (!semanas.value.includes(semanaSelecionada.value)) semanaSelecionada.value = metadataSemanal.semana_inicial ?? semanas.value[0] ?? ''
      ultimaAtualizacaoSemanal.value = metadataSemanal.atualizado_em
    } else if (visao.value === 'semanal') {
      throw new Error('Não foi possível carregar as semanas disponíveis.')
    }

    const familiaExiste = familias.value.some(
      (familia) => String(familia.id_conta) === String(familiaSelecionada.value),
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
  const semanal = visao.value === 'semanal'
  const anual = visao.value === 'anual'
  if (!pronto.value || !familiaSelecionada.value || !categoriaSelecionada.value || (semanal ? !semanaSelecionada.value : !anoSelecionado.value)) {
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
      raiz_id: String(familiaSelecionada.value),
      categoria_id: String(categoriaSelecionada.value),
      metrica: metrica.value,
      incluir_inativos: incluirInativos.value ? '1' : '0',
      page: String(pagina.value),
    })
    if (semanal) {
      params.set('semana_inicio', semanaSelecionada.value)
      params.set('periodo_equivalente', equivalenteSemanal.value ? '1' : '0')
    } else {
      params.set('ano', String(anoSelecionado.value))
      if (anual) params.set('periodo_equivalente', equivalenteAnual.value ? '1' : '0')
      else if (equivalenteMensal.value) params.set('periodo_equivalente', '1')
    }
    if (buscaAplicada.value) params.set('search', buscaAplicada.value)

    const response = await fetch(`${semanal ? ENDPOINT_SEMANAL : anual ? ENDPOINT_ANUAL : ENDPOINT}?${params}`, { signal: requisicao.signal })
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

async function atualizarSemanas(forcar = false) {
  try {
    const response = await fetch(METADATA_SEMANAL_ENDPOINT)
    if (!response.ok) throw new Error('Falha ao verificar atualização semanal.')
    const metadata = await response.json()
    const semanaAnterior = semanas.value[0]
    const mudou = metadata.atualizado_em !== ultimaAtualizacaoSemanal.value
    semanas.value = metadata.semanas_disponiveis ?? []
    ultimaAtualizacaoSemanal.value = metadata.atualizado_em
    if (!semanaSelecionada.value || semanaSelecionada.value === semanaAnterior) {
      const novaSemana = metadata.semana_inicial ?? semanas.value[0] ?? ''
      if (novaSemana !== semanaSelecionada.value) {
        semanaSelecionada.value = novaSemana
        return
      }
    }
    if ((mudou || forcar) && visao.value === 'semanal') carregarRelatorio()
  } catch (e) {
    if (forcar) erro.value = e?.message || 'Falha ao verificar atualização semanal.'
  }
}

function irParaPagina(destino) {
  const limite = Math.max(1, paginacao.value.total_paginas)
  pagina.value = Math.min(limite, Math.max(1, destino))
}

watch(busca, (valor) => {
  if (debounceBusca) clearTimeout(debounceBusca)
  debounceBusca = setTimeout(() => {
    buscaAplicada.value = String(valor || '').trim()
  }, 350)
})
watch(visao, () => {
  if (visao.value !== 'semanal' && !anosDaVisao.value.includes(anoSelecionado.value)) {
    anoSelecionado.value = anosDaVisao.value[0] ?? null
  }
})

watch(
  [familiaSelecionada, categoriaSelecionada, anoSelecionado, semanaSelecionada, visao, equivalenteSemanal, equivalenteMensal, equivalenteAnual, metrica, incluirInativos, buscaAplicada],
  () => {
    if (!pronto.value) return
    if (pagina.value !== 1) pagina.value = 1
    else carregarRelatorio()
  },
)
watch(pagina, () => {
  if (pronto.value) carregarRelatorio()
})

onMounted(() => {
  carregarOpcoes()
  intervaloAtualizacao = window.setInterval(() => {
    if (visao.value === 'semanal') atualizarSemanas()
  }, 60000)
})
onBeforeUnmount(() => {
  if (debounceBusca) clearTimeout(debounceBusca)
  if (requisicaoAtual) requisicaoAtual.abort()
  if (intervaloAtualizacao) window.clearInterval(intervaloAtualizacao)
})
</script>

<template>
  <div class="flex flex-col gap-5">
    <div>
      <h1 class="text-xl font-bold text-gray-900">Vendas por Produto</h1>
      <p class="mt-0.5 text-sm text-gray-400">Detalhamento dos produtos vinculados à categoria selecionada.</p>
    </div>

    <div class="rounded-xl border border-gray-200 bg-white shadow-sm">
      <div class="flex flex-wrap items-end gap-3 border-b border-gray-100 bg-gray-50/70 px-4 py-3">
        <label class="flex min-w-[220px] flex-1 flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
          Família do plano de contas
          <select
            v-model="familiaSelecionada"
            class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium normal-case text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300"
            :disabled="loadingInicial || (!anos.length && !semanas.length)"
            @change="trocarFamilia"
          >
            <option value="">Selecione uma família</option>
            <option v-for="familia in familias" :key="familia.id_conta" :value="String(familia.id_conta)">
              {{ familia.codigo_hierarquico }} {{ familia.nome_conta }}
            </option>
          </select>
        </label>

        <label class="flex min-w-[250px] flex-1 flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
          Categoria
          <RemoteSearchSelect
            v-model="categoriaControle"
            :endpoint="CATEGORIAS_ENDPOINT"
            value-field="id_conta"
            label-field="label"
            all-label="Toda a família"
            search-placeholder="Pesquisar categoria..."
            :min-chars="1"
            :limit="50"
            :extra-params="{ raiz_id: familiaSelecionada }"
            resolve-param="ids"
            :initial-label="categoriaLabel"
            :disabled="!familiaSelecionada || loadingInicial"
            button-class="flex h-[34px] w-full items-center justify-between gap-2 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium normal-case text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
          />
        </label>

        <label class="flex h-[34px] cursor-pointer items-center gap-2 rounded-md border border-gray-200 bg-white px-3 text-xs font-medium text-gray-600">
          <input v-model="incluirInativos" type="checkbox" class="h-3.5 w-3.5 rounded border-gray-300 accent-[#373435]" />
          Incluir inativos ({{ dados?.inativos_ocultos ?? 0 }})
        </label>
      </div>

      <div class="grid gap-3 border-b border-gray-100 bg-gray-50/70 px-4 py-3 xl:grid-cols-[minmax(0,1fr)_auto] xl:gap-0">
        <div class="min-w-0 xl:pr-4" role="group" aria-label="Período">
          <div class="flex flex-wrap items-end gap-3">
            <div class="flex flex-col gap-1">
              <span class="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Visão</span>
              <div class="flex h-[34px] overflow-hidden rounded-md border border-gray-200 text-xs font-semibold">
                <button type="button" class="px-3 transition-colors" :class="visao === 'semanal' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" @click="visao = 'semanal'">Semanal</button>
                <button type="button" class="border-l border-gray-200 px-3 transition-colors" :class="visao === 'mensal' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" @click="visao = 'mensal'">Mensal</button>
                <button type="button" class="border-l border-gray-200 px-3 transition-colors" :class="visao === 'anual' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" @click="visao = 'anual'">Anual</button>
              </div>
            </div>

            <label v-if="visao !== 'semanal'" class="flex w-28 flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
              Ano
              <select v-model="anoSelecionado" class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300" :disabled="loadingInicial || !anosDaVisao.length">
                <option v-for="ano in anosDaVisao" :key="ano" :value="ano">{{ ano }}</option>
              </select>
            </label>

            <label v-else class="flex min-w-[230px] flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
              Semana de referência
              <select v-model="semanaSelecionada" class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium normal-case text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300" :disabled="loadingInicial || !semanas.length">
                <option v-for="semana in semanas" :key="semana" :value="semana">{{ rotuloSemana(semana) }}</option>
              </select>
            </label>

            <label v-if="visao === 'semanal'" class="flex h-[34px] cursor-pointer items-center gap-2 rounded-md border border-gray-200 bg-white px-3 text-xs font-medium text-gray-600">
              <input v-model="equivalenteSemanal" type="checkbox" class="accent-[#373435]" />
              Períodos equivalentes
            </label>
            <label v-if="visao === 'mensal' && dados?.mes_aberto" class="flex h-[34px] cursor-pointer items-center gap-2 rounded-md border border-gray-200 bg-white px-3 text-xs font-medium text-gray-600">
              <input v-model="equivalenteMensal" type="checkbox" class="accent-[#373435]" />
              Períodos equivalentes
            </label>
            <label v-if="visao === 'anual' && dados?.ano_parcial" class="flex h-[34px] cursor-pointer items-center gap-2 rounded-md border border-gray-200 bg-white px-3 text-xs font-medium text-gray-600">
              <input v-model="equivalenteAnual" type="checkbox" class="accent-[#373435]" />
              Períodos equivalentes
            </label>
          </div>
        </div>

        <div class="min-w-0 border-t border-gray-200 pt-3 xl:border-l xl:border-t-0 xl:pl-4 xl:pt-0" role="group" aria-label="Leitura">
          <div class="flex flex-wrap items-end gap-3">
            <div class="flex flex-col gap-1">
              <span class="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Métrica</span>
              <div class="flex h-[34px] overflow-hidden rounded-md border border-gray-200 text-xs font-semibold">
                <button type="button" class="px-3 transition-colors" :class="metrica === 'valor' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" @click="selecionarMetrica('valor')">Valores financeiros</button>
                <button type="button" class="border-l border-gray-200 px-3 transition-colors" :class="metrica === 'quantidade' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" @click="selecionarMetrica('quantidade')">Quantidades</button>
              </div>
            </div>

            <button type="button" class="flex h-[34px] items-center gap-1.5 rounded-md border border-gray-200 bg-white px-3 text-xs font-medium text-gray-600 hover:bg-gray-100" @click="visao === 'semanal' ? atualizarSemanas(true) : carregarRelatorio()">
              <RefreshCw class="h-3.5 w-3.5" /> Atualizar
            </button>
            <SnapshotDetails v-if="dados" :key="visao" :ultima-venda="dados.ultima_data_disponivel" :atualizado-em="dados.atualizado_em" />
          </div>
        </div>
      </div>

      <div class="flex items-center border-b border-gray-100 px-4 py-2.5">
        <div class="flex w-full max-w-sm items-center gap-2 rounded-md border border-gray-200 bg-white px-3 py-2">
          <Search class="h-4 w-4 text-gray-400" />
          <input v-model="busca" type="search" class="w-full border-0 bg-transparent p-0 text-xs text-gray-700 outline-none" placeholder="Buscar por código ou nome do produto" />
        </div>
      </div>

      <div v-if="dados?.desatualizado" class="flex items-start gap-2 border-b border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
        <AlertTriangle class="mt-0.5 h-4 w-4 shrink-0" />
        <span>Existem períodos aguardando atualização. Os últimos valores válidos continuam visíveis.</span>
      </div>
      <div v-if="dados && visao === 'semanal' && (dados.semana_parcial || dados.periodos_considerados_20 < 20 || dados.periodos_considerados_5 < 5)" class="border-b border-gray-100 px-4 py-2 text-xs text-gray-600">
        <span v-if="dados.semana_parcial" :class="dados.periodo_equivalente ? 'text-gray-700' : 'font-semibold text-amber-700'">Prévia até {{ dataCurta(dados.semanas?.[5]?.data_corte) }}{{ dados.periodo_equivalente ? '; referências cortadas no mesmo dia da semana.' : '; comparação com semanas anteriores completas.' }}</span>
        <span v-if="dados.periodos_considerados_20 < 20 || dados.periodos_considerados_5 < 5" class="ml-1">Histórico: {{ dados.periodos_considerados_20 }}/20 semanas (últimas cinco: {{ dados.periodos_considerados_5 }}/5).</span>
      </div>
      <div v-if="dados && visao === 'anual' && dados.ano_parcial" class="border-b border-gray-100 px-4 py-2 text-xs text-gray-600">
        <span :class="dados.periodo_equivalente ? 'text-gray-700' : 'font-semibold text-amber-700'">Prévia até {{ dataCurta(dados.anos?.at(-1)?.fim) }}{{ dados.periodo_equivalente ? '; anos anteriores cortados no mesmo mês e dia.' : '; comparação recente com ano anterior completo.' }}</span>
      </div>

      <div v-if="erro" class="border-b border-red-100 bg-red-50 px-4 py-3 text-xs font-semibold text-red-700">{{ erro }}</div>

      <div v-if="loadingInicial || loading" class="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
        <div class="h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-[#373435]" />
        <div>
          <p class="text-sm font-medium text-gray-700">Processando análise</p>
          <p class="mt-1 text-xs text-gray-400">A consulta pode levar alguns segundos.</p>
        </div>
      </div>

      <div v-else-if="!(visao === 'semanal' ? semanas.length : anosDaVisao.length) && !erro" class="flex flex-col items-center justify-center px-6 py-16 text-center">
        <AlertTriangle class="mb-3 h-7 w-7 text-amber-500" />
        <p class="text-sm font-medium text-gray-600">Agregado analítico ainda não construído</p>
      </div>

      <div v-else-if="!familiaSelecionada && !erro" class="flex flex-col items-center justify-center px-6 py-16 text-center">
        <PackageSearch class="mb-3 h-8 w-8 text-gray-300" />
        <p class="text-sm font-medium text-gray-600">Selecione uma família</p>
        <p class="mt-1 text-xs text-gray-400">Depois, refine por qualquer categoria da hierarquia.</p>
      </div>

      <div v-else-if="dados && !dados.linhas.length" class="flex flex-col items-center justify-center px-6 py-16 text-center">
        <PackageSearch class="mb-3 h-8 w-8 text-gray-300" />
        <p class="text-sm font-medium text-gray-600">Nenhum produto encontrado</p>
        <p class="mt-1 text-xs text-gray-400">Revise a categoria, a busca ou o filtro de inativos.</p>
      </div>

      <template v-else-if="dados">
        <div v-if="visao === 'mensal'" class="app-scrollbar overflow-x-auto">
          <table class="w-full border-collapse text-xs">
            <thead>
              <tr class="border-b border-gray-100 bg-white">
                <th class="sticky left-0 z-20 min-w-[300px] bg-white px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-400 shadow-[1px_0_0_#f3f4f6]">Produto</th>
                <th v-for="(mes, indice) in MESES" :key="mes" class="min-w-[100px] px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400" :title="tooltipMesAberto(dados, indice)" :aria-label="tooltipMesAberto(dados, indice) || mes">{{ mes }}</th>
                <th class="min-w-[120px] bg-gray-50 px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-600">{{ dados.periodo_equivalente ? 'Total comparável' : 'Total' }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="linha in dados.linhas" :key="linha.id_produto" class="border-b border-gray-50 last:border-0 hover:bg-gray-50/70">
                <td class="sticky left-0 z-10 bg-white px-4 py-2.5 shadow-[1px_0_0_#f3f4f6]">
                  <div class="flex items-center gap-2">
                    <span class="font-mono text-[10px] text-gray-400">{{ linha.id_produto }}</span>
                    <span class="font-medium text-gray-700">{{ linha.nome_produto }}</span>
                    <span v-if="statusInativo(linha.status)" class="ml-auto rounded-full bg-amber-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-amber-700">Inativo</span>
                  </div>
                </td>

                <template v-if="metrica === 'valor'">
                  <td
                    v-for="(valor, indice) in linha.valores"
                    :key="indice"
                    class="px-3 py-2.5 text-right font-mono tabular-nums"
                    :class="numeroFinanceiro(valor) === null ? 'text-gray-300' : 'text-gray-700'"
                    :style="estiloLinha(linha, valor, indice)"
                  >{{ formatarValor(valor) }}</td>
                  <td class="bg-gray-50 px-4 py-2.5 text-right font-mono font-semibold tabular-nums text-gray-800">{{ formatarValor(linha.total) }}</td>
                </template>
                <template v-else>
                  <td v-for="indice in 12" :key="indice" class="px-3 py-2 text-right align-top font-mono tabular-nums text-gray-600">
                    <div v-if="linha.unidades.length" class="space-y-0.5">
                      <div v-for="unidade in linha.unidades" :key="unidade.id_unidade" class="whitespace-nowrap">
                        {{ formatarQuantidade(unidade.valores[indice - 1]) }} <span class="text-[9px] font-semibold text-gray-400">{{ unidade.sigla }}</span>
                      </div>
                    </div>
                    <span v-else class="text-gray-300">-</span>
                  </td>
                  <td class="bg-gray-50 px-4 py-2 text-right align-top font-mono font-semibold tabular-nums text-gray-800">
                    <div v-if="linha.unidades.length" class="space-y-0.5">
                      <div v-for="unidade in linha.unidades" :key="unidade.id_unidade" class="whitespace-nowrap">
                        {{ formatarQuantidade(unidade.total) }} <span class="text-[9px] text-gray-500">{{ unidade.sigla }}</span>
                      </div>
                    </div>
                    <span v-else class="text-gray-300">-</span>
                  </td>
                </template>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else-if="visao === 'anual'" class="app-scrollbar overflow-x-auto">
          <table class="w-full border-collapse text-xs">
            <thead><tr class="border-b border-gray-100 bg-white">
              <th class="sticky left-0 z-20 min-w-[300px] bg-white px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-400 shadow-[1px_0_0_#f3f4f6]">Produto</th>
              <th v-for="periodo in dados.anos" :key="periodo.ano" class="min-w-[145px] px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-600" :title="`${dataCurta(periodo.inicio)} a ${dataCurta(periodo.fim)}`">{{ periodo.ano }}<span v-if="periodo.parcial" class="block font-normal normal-case text-amber-700">Parcial</span><span v-else-if="periodo.equivalente" class="block font-normal normal-case text-gray-400">Até {{ dataCurta(periodo.fim).slice(0, 5) }}</span></th>
              <th class="min-w-[135px] bg-gray-50 px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-600" :title="tituloVariacoesAnuais">Variações<span class="block font-normal normal-case">Média / recente</span></th>
            </tr></thead>
            <tbody>
              <tr v-for="linha in dados.linhas" :key="linha.id_produto" class="border-b border-gray-50 last:border-0 hover:bg-gray-50/70">
                <td class="sticky left-0 z-10 bg-white px-4 py-2.5 shadow-[1px_0_0_#f3f4f6]"><div class="flex items-center gap-2"><span class="font-mono text-[10px] text-gray-400">{{ linha.id_produto }}</span><span class="font-medium text-gray-700">{{ linha.nome_produto }}</span><span v-if="statusInativo(linha.status)" class="ml-auto rounded-full bg-amber-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-amber-700">Inativo</span></div></td>
                <template v-if="metrica === 'valor'">
                  <td v-for="(valor, indice) in linha.valores" :key="indice" class="px-3 py-2.5 text-right font-mono tabular-nums text-gray-700" :style="estiloLinha(linha, valor, indice)">{{ formatarValor(valor) }}</td>
                  <td class="bg-gray-50 px-3 py-2 text-right" :title="tituloVariacoesAnuais"><VariacoesCompactas :media="linha.variacao_historica_percentual" :recente="linha.variacao_percentual" :recente-neutra="dados.ano_parcial && !dados.periodo_equivalente" /></td>
                </template>
                <template v-else>
                  <td v-for="indice in dados.anos.length" :key="indice" class="px-3 py-2 text-right align-top font-mono tabular-nums text-gray-700"><div v-for="unidade in linha.unidades" :key="unidade.id_unidade">{{ formatarQuantidade(unidade.valores[indice - 1]) }} <span class="text-[9px] text-gray-400">{{ unidade.sigla }}</span></div><span v-if="!linha.unidades.length" class="text-gray-300">0</span></td>
                  <td class="bg-gray-50 px-3 py-2 text-right align-top" :title="tituloVariacoesAnuais"><VariacoesCompactas v-for="unidade in linha.unidades" :key="unidade.id_unidade" class="mb-1 last:mb-0" :media="unidade.variacao_historica_percentual" :recente="unidade.variacao_percentual" :sigla="unidade.sigla" :recente-neutra="dados.ano_parcial && !dados.periodo_equivalente" /><span v-if="!linha.unidades.length" class="text-gray-300">—</span></td>
                </template>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="app-scrollbar overflow-x-auto">
          <table class="w-full border-collapse text-xs">
            <thead>
              <tr class="border-b border-gray-100 bg-white">
                <th class="sticky left-0 z-20 min-w-[300px] bg-white px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-400 shadow-[1px_0_0_#f3f4f6]">Produto</th>
                <th class="min-w-[125px] bg-gray-50 px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-600">Média 20 semanas</th>
                <th v-for="(periodo, indice) in dados.semanas" :key="periodo.inicio" class="min-w-[120px] px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider" :class="indice === 5 ? 'bg-gray-50 text-[#373435]' : 'text-gray-400'" :title="`${rotuloSemana(periodo.inicio)}${periodo.data_corte ? ` · até ${dataCurta(periodo.data_corte)}` : ''}`">
                  <span v-if="indice === 5" class="block">Semana foco</span>
                  {{ dataCurta(periodo.inicio).slice(0, 5) }}–{{ dataCurta(periodo.fim).slice(0, 5) }}
                </th>
                <th class="min-w-[135px] bg-gray-50 px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-600" title="Média: média das últimas 5 semanas contra a média de 20. Recente: semana foco contra a média das últimas 5.">Variações<span class="block font-normal normal-case">Média / recente</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="linha in dados.linhas" :key="linha.id_produto" class="border-b border-gray-50 last:border-0 hover:bg-gray-50/70">
                <td class="sticky left-0 z-10 bg-white px-4 py-2.5 shadow-[1px_0_0_#f3f4f6]">
                  <div class="flex items-center gap-2">
                    <span class="font-mono text-[10px] text-gray-400">{{ linha.id_produto }}</span>
                    <span class="font-medium text-gray-700">{{ linha.nome_produto }}</span>
                    <span v-if="statusInativo(linha.status)" class="ml-auto rounded-full bg-amber-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-amber-700">Inativo</span>
                  </div>
                </td>
                <template v-if="metrica === 'valor'">
                  <td class="bg-gray-50 px-3 py-2.5 text-right font-mono tabular-nums text-gray-700">{{ formatarValor(linha.media_20) }}</td>
                  <td v-for="(valor, indice) in linha.valores" :key="indice" class="px-3 py-2.5 text-right font-mono tabular-nums text-gray-700" :class="indice === 5 ? 'font-semibold' : ''">{{ formatarValor(valor) }}</td>
                  <td class="bg-gray-50 px-3 py-2 text-right" :title="`Média 20: ${formatarValor(linha.media_20)} · Média 5: ${formatarValor(linha.media_5)}`"><VariacoesCompactas :media="linha.variacao_5_vs_20_percentual" :recente="linha.variacao_5_percentual" /></td>
                </template>
                <template v-else>
                  <td class="bg-gray-50 px-3 py-2.5 text-right align-top font-mono tabular-nums text-gray-700">
                    <div v-for="unidade in linha.unidades" :key="unidade.id_unidade">{{ formatarQuantidade(unidade.media_20) }} <span class="text-[9px] text-gray-400">{{ unidade.sigla }}</span></div>
                    <span v-if="!linha.unidades.length" class="text-gray-300">-</span>
                  </td>
                  <td v-for="indice in 6" :key="indice" class="px-3 py-2.5 text-right align-top font-mono tabular-nums text-gray-700">
                    <div v-for="unidade in linha.unidades" :key="unidade.id_unidade">{{ formatarQuantidade(unidade.valores[indice - 1]) }} <span class="text-[9px] text-gray-400">{{ unidade.sigla }}</span></div>
                    <span v-if="!linha.unidades.length" class="text-gray-300">-</span>
                  </td>
                  <td class="bg-gray-50 px-3 py-2 text-right align-top font-mono tabular-nums">
                    <VariacoesCompactas v-for="unidade in linha.unidades" :key="unidade.id_unidade" class="mb-1 last:mb-0" :media="unidade.variacao_5_vs_20_percentual" :recente="unidade.variacao_5_percentual" :sigla="unidade.sigla" :title="`Média 20: ${formatarQuantidade(unidade.media_20)} ${unidade.sigla} · Média 5: ${formatarQuantidade(unidade.media_5)} ${unidade.sigla}`" />
                    <span v-if="!linha.unidades.length" class="text-gray-300">-</span>
                  </td>
                </template>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 px-4 py-3 text-xs text-gray-500">
          <span>{{ paginacao.total_produtos }} produto(s) · página {{ paginacao.pagina }} de {{ paginacao.total_paginas }}</span>
          <div class="flex gap-2">
            <button type="button" class="rounded-md border border-gray-200 px-3 py-1.5 font-medium text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40" :disabled="paginacao.pagina <= 1" @click="irParaPagina(paginacao.pagina - 1)">Anterior</button>
            <button type="button" class="rounded-md border border-gray-200 px-3 py-1.5 font-medium text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40" :disabled="paginacao.pagina >= paginacao.total_paginas" @click="irParaPagina(paginacao.pagina + 1)">Próxima</button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
