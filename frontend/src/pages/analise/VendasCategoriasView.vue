<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AlertTriangle, ChevronDown, ChevronRight, ExternalLink, Layers3, RefreshCw, TrendingDown, TrendingUp, X } from 'lucide-vue-next'
import { getApiBaseUrl } from '@/services/firebirdSync'
import SnapshotDetails from './SnapshotDetails.vue'
import VariacoesCompactas from './VariacoesCompactas.vue'
import QuarentenaBotao from './QuarentenaBotao.vue'
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
const ENDPOINT = `${API_BASE_URL}/api/analise/categorias/vendas/`
const ENDPOINT_SEMANAL = `${ENDPOINT}semanal/`
const ENDPOINT_ANUAL = `${ENDPOINT}anual/`
const ENDPOINT_OSCILACOES = `${ENDPOINT}oscilacoes/`
const ENDPOINT_QUARENTENA = `${ENDPOINT}quarentena/`
const router = useRouter()
const route = useRoute()

const familias = ref([])
const anos = ref([])
const anosAnuais = ref([])
const semanas = ref([])
const familiaSelecionada = ref(String(route.query.raiz_id || ''))
const anoSelecionado = ref(Number(route.query.ano) || null)
const semanaSelecionada = ref(String(route.query.semana_inicio || ''))
const ultimaAtualizacaoSemanal = ref(null)
const visao = ref(['semanal', 'anual'].includes(route.query.visao) ? route.query.visao : 'mensal')
const anosDaVisao = computed(() => visao.value === 'anual' ? anosAnuais.value : anos.value)
const equivalenteSemanal = ref(!['0', 'false'].includes(String(route.query.periodo_equivalente || '1').toLowerCase()))
const equivalenteMensal = ref(['1', 'true'].includes(String(route.query.periodo_equivalente || '').toLowerCase()))
const equivalenteAnual = ref(!['0', 'false'].includes(String(route.query.periodo_equivalente || '1').toLowerCase()))
const metrica = ref(['valor', 'quantidade'].includes(route.query.metrica) ? route.query.metrica : 'valor')
const dados = ref(null)
const loadingInicial = ref(true)
const loading = ref(false)
const erro = ref('')
const conflitos = ref([])
const expandidas = ref(new Set())
const radarAberto = ref(false)
const radarDados = ref(null)
const radarLoading = ref(false)
const radarErro = ref('')
const radarConflitos = ref([])
const marcadas = ref(new Set())
const marcacoesPendentes = ref(new Set())
const erroMarcacao = ref('')
let sequenciaCarga = 0
let sequenciaRadar = 0
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

function formatarVariacao(valor) {
  if (valor === null || valor === undefined) return '—'
  const numero = Number(valor)
  if (!Number.isFinite(numero)) return '—'
  return `${numero > 0 ? '+' : ''}${numero.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`
}

async function carregarOpcoes() {
  loadingInicial.value = true
  erro.value = ''
  try {
    const [resFamilias, resMetadata, resSemanas, resAnual] = await Promise.all([
      fetch(`${API_BASE_URL}/api/cadastros/plano-contas/raizes`),
      fetch(ENDPOINT),
      fetch(ENDPOINT_SEMANAL),
      fetch(ENDPOINT_ANUAL),
    ])
    if (!resFamilias.ok || !resMetadata.ok || !resSemanas.ok || !resAnual.ok) throw new Error('Não foi possível carregar as opções da análise.')
    familias.value = await resFamilias.json()
    const metadata = await resMetadata.json()
    anos.value = metadata.anos_disponiveis ?? []
    anosAnuais.value = (await resAnual.json()).anos_disponiveis ?? []
    if (!anosDaVisao.value.includes(anoSelecionado.value)) anoSelecionado.value = anosDaVisao.value[0] ?? null
    const metadataSemanal = await resSemanas.json()
    semanas.value = metadataSemanal.semanas_disponiveis ?? []
    if (!semanas.value.includes(semanaSelecionada.value)) semanaSelecionada.value = metadataSemanal.semana_inicial ?? semanas.value[0] ?? ''
    ultimaAtualizacaoSemanal.value = metadataSemanal.atualizado_em
    if (!familias.value.some((familia) => String(familia.id_conta) === familiaSelecionada.value)) familiaSelecionada.value = ''
  } catch (e) {
    erro.value = e?.message || 'Falha ao carregar a análise.'
  } finally {
    loadingInicial.value = false
  }
}

async function carregarRelatorio(silencioso = false) {
  const semanal = visao.value === 'semanal'
  const anual = visao.value === 'anual'
  const sequencia = ++sequenciaCarga
  if (!familiaSelecionada.value || (semanal ? !semanaSelecionada.value : !anoSelecionado.value)) {
    dados.value = null
    conflitos.value = []
    return
  }
  if (!silencioso) loading.value = true
  erro.value = ''
  conflitos.value = []
  try {
    const params = new URLSearchParams({
      raiz_id: String(familiaSelecionada.value),
      metrica: metrica.value,
      periodo_equivalente: (semanal ? equivalenteSemanal.value : anual ? equivalenteAnual.value : equivalenteMensal.value) ? '1' : '0',
    })
    if (semanal) params.set('semana_inicio', semanaSelecionada.value)
    else params.set('ano', String(anoSelecionado.value))
    const res = await fetch(`${semanal ? ENDPOINT_SEMANAL : anual ? ENDPOINT_ANUAL : ENDPOINT}?${params}`)
    const payload = await res.json().catch(() => ({}))
    if (sequencia !== sequenciaCarga) return
    if (!res.ok) {
      conflitos.value = payload.produtos_conflitantes ?? []
      throw new Error(payload.detail || `Erro ${res.status}`)
    }
    dados.value = payload
    const abertas = new Set([payload.familia.id_conta])
    const foco = Number(route.query.categoria_id)
    const porId = new Map(payload.linhas.map((linha) => [linha.id_conta, linha]))
    let atual = porId.get(foco)
    if (atual) {
      while (atual?.conta_pai_id) {
        abertas.add(atual.conta_pai_id)
        atual = porId.get(atual.conta_pai_id)
      }
      nextTick(() => document.getElementById(`categoria-venda-${foco}`)?.scrollIntoView({ block: 'center' }))
    }
    expandidas.value = abertas
  } catch (e) {
    if (sequencia !== sequenciaCarga) return
    dados.value = null
    erro.value = e?.message || 'Falha ao processar o relatório.'
  } finally {
    if (sequencia === sequenciaCarga) loading.value = false
  }
}

async function atualizarSemanas(forcar = false) {
  try {
    const response = await fetch(ENDPOINT_SEMANAL)
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
    if ((mudou || forcar) && visao.value === 'semanal') {
      carregarRelatorio(true)
      if (radarAberto.value) carregarRadar()
    }
  } catch (e) {
    if (forcar) erro.value = e?.message || 'Falha ao verificar atualização semanal.'
  }
}

watch([familiaSelecionada, anoSelecionado, semanaSelecionada, metrica, visao, equivalenteSemanal, equivalenteMensal, equivalenteAnual], () => carregarRelatorio())
watch(visao, () => {
  if (visao.value !== 'semanal' && !anosDaVisao.value.includes(anoSelecionado.value)) {
    anoSelecionado.value = anosDaVisao.value[0] ?? null
  }
})
watch([familiaSelecionada, anoSelecionado, semanaSelecionada, visao], () => {
  if (visao.value === 'anual') {
    radarAberto.value = false
    sequenciaRadar += 1
    radarDados.value = null
  } else if (radarAberto.value) carregarRadar()
})
onMounted(() => {
  carregarOpcoes()
  carregarMarcadas()
  intervaloAtualizacao = window.setInterval(() => {
    if (visao.value === 'semanal') atualizarSemanas()
  }, 60000)
})
onUnmounted(() => window.clearInterval(intervaloAtualizacao))

async function carregarMarcadas() {
  try {
    const resposta = await fetch(ENDPOINT_QUARENTENA)
    if (!resposta.ok) throw new Error('Não foi possível consultar a quarentena.')
    const payload = await resposta.json()
    marcadas.value = new Set((payload.categorias ?? []).map((item) => item.id_conta))
    erroMarcacao.value = ''
  } catch (e) {
    erroMarcacao.value = e?.message || 'Falha ao consultar a quarentena.'
  }
}

async function alternarMarcacao(linha) {
  const id = linha.id_conta
  if (marcacoesPendentes.value.has(id)) return
  marcacoesPendentes.value = new Set([...marcacoesPendentes.value, id])
  erroMarcacao.value = ''
  const remover = marcadas.value.has(id)
  try {
    const resposta = await fetch(remover ? `${ENDPOINT_QUARENTENA}${id}/` : ENDPOINT_QUARENTENA, {
      method: remover ? 'DELETE' : 'POST',
      ...(remover ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ categoria_id: id }) }),
    })
    if (!resposta.ok) {
      const payload = await resposta.json().catch(() => ({}))
      throw new Error(payload.detail || 'Não foi possível alterar a quarentena.')
    }
    const novas = new Set(marcadas.value)
    if (remover) novas.delete(id)
    else novas.add(id)
    marcadas.value = novas
  } catch (e) {
    erroMarcacao.value = e?.message || 'Não foi possível alterar a quarentena.'
  } finally {
    const novas = new Set(marcacoesPendentes.value)
    novas.delete(id)
    marcacoesPendentes.value = novas
  }
}

function toggleCategoria(id) {
  const novo = new Set(expandidas.value)
  if (novo.has(id)) novo.delete(id)
  else novo.add(id)
  expandidas.value = novo
}

const linhasVisiveis = computed(() => {
  const linhas = dados.value?.linhas ?? []
  const porId = new Map(linhas.map((linha) => [linha.id_conta, linha]))
  return linhas.filter((linha) => {
    let paiId = linha.conta_pai_id
    while (paiId) {
      if (!expandidas.value.has(paiId)) return false
      paiId = porId.get(paiId)?.conta_pai_id ?? null
    }
    return true
  })
})

const tituloVariacoesAnuais = computed(() => {
  const anos = dados.value?.anos?.map((periodo) => periodo.ano) ?? []
  const transicoes = anos.slice(0, -2).map((ano, indice) => `${ano}→${anos[indice + 1]}`)
  const media = transicoes.length ? `Média das variações ${transicoes.join(' e ')}.` : 'Média histórica indisponível: menos de dois anos anteriores.'
  const recente = anos.length > 1 ? `Recente: ${anos.at(-2)}→${anos.at(-1)}.` : 'Recente indisponível: sem ano anterior.'
  return `${media} ${recente}`
})

const quartisPorLinha = computed(() => new Map(
  (dados.value?.linhas ?? []).map((linha) => [
    linha.id_conta,
    mapaQuartis(
      linha.valores ?? [],
      visao.value === 'mensal'
        ? (dados.value?.periodo_equivalente ? [] : indicesIgnoradosMesAberto(dados.value))
        : visao.value === 'anual'
          ? (dados.value?.ano_parcial && !dados.value?.periodo_equivalente ? [linha.valores.length - 1] : [])
          : (dados.value?.semana_parcial && !dados.value?.periodo_equivalente ? [5] : []),
    ),
  ]),
))

function estiloLinha(linha, valor, indice) {
  return estiloCelulaFinanceira(
    quartisPorLinha.value.get(linha.id_conta),
    valor,
    false,
    visao.value === 'mensal'
      ? (!dados.value?.periodo_equivalente && mesEstaAberto(dados.value, indice))
      : visao.value === 'anual'
        ? (dados.value?.ano_parcial && !dados.value?.periodo_equivalente && indice === dados.value?.anos?.length - 1)
        : (dados.value?.semana_parcial && !dados.value?.periodo_equivalente && indice === 5),
  )
}

async function carregarRadar() {
  const sequencia = ++sequenciaRadar
  const semanal = visao.value === 'semanal'
  radarDados.value = null
  radarErro.value = ''
  radarConflitos.value = []
  if (!radarAberto.value || !familiaSelecionada.value || (semanal ? !semanaSelecionada.value : !anoSelecionado.value)) {
    radarLoading.value = false
    return
  }
  radarLoading.value = true
  try {
    const params = new URLSearchParams({ raiz_id: String(familiaSelecionada.value), visao: visao.value })
    if (semanal) params.set('semana_inicio', semanaSelecionada.value)
    else params.set('ano', String(anoSelecionado.value))
    const response = await fetch(`${ENDPOINT_OSCILACOES}?${params}`)
    const payload = await response.json().catch(() => ({}))
    if (sequencia !== sequenciaRadar) return
    if (!response.ok) {
      radarConflitos.value = payload.produtos_conflitantes ?? []
      throw new Error(payload.detail || `Erro ${response.status}`)
    }
    radarDados.value = payload
  } catch (e) {
    if (sequencia === sequenciaRadar) radarErro.value = e?.message || 'Falha ao carregar as oscilações.'
  } finally {
    if (sequencia === sequenciaRadar) radarLoading.value = false
  }
}

function alternarRadar() {
  radarAberto.value = !radarAberto.value
  if (radarAberto.value) carregarRadar()
  else {
    sequenciaRadar += 1
    radarLoading.value = false
    radarDados.value = null
  }
}

function atualizarAnalise() {
  if (visao.value === 'semanal') atualizarSemanas(true)
  else {
    carregarRelatorio()
    if (radarAberto.value) carregarRadar()
  }
}

function abrirProdutos(linha, peloRadar = false) {
  const semanal = visao.value === 'semanal'
  const anual = visao.value === 'anual'
  const destino = router.resolve({
    name: 'analise-categorias-produtos-vendas',
    query: semanal ? {
      visao: 'semanal',
      raiz_id: familiaSelecionada.value,
      categoria_id: linha.id_conta,
      semana_inicio: semanaSelecionada.value,
      metrica: peloRadar ? 'valor' : metrica.value,
      periodo_equivalente: (peloRadar ? radarDados.value?.previa : equivalenteSemanal.value) ? '1' : '0',
    } : {
      ...(anual ? { visao: 'anual' } : {}),
      raiz_id: familiaSelecionada.value,
      categoria_id: linha.id_conta,
      ano: anoSelecionado.value,
      metrica: peloRadar ? 'valor' : metrica.value,
      periodo_equivalente: (peloRadar ? radarDados.value?.previa : anual ? equivalenteAnual.value : equivalenteMensal.value) ? '1' : '0',
    },
  })
  const novaAba = window.open(destino.href, '_blank', 'noopener,noreferrer')
  if (novaAba) novaAba.opener = null
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-gray-900">Vendas por Categoria</h1>
        <p class="mt-0.5 text-sm text-gray-400">Receita bruta ou quantidade vendida pela hierarquia do plano de contas.</p>
      </div>
      <button v-if="visao !== 'anual'" type="button" class="flex h-[34px] items-center gap-1.5 rounded-md border px-3 text-xs font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50" :class="radarAberto ? 'border-[#373435] bg-[#373435] text-white' : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-100'" :disabled="!familiaSelecionada || (visao === 'semanal' ? !semanaSelecionada : !anoSelecionado)" :aria-expanded="radarAberto" aria-controls="radar-oscilacoes" @click="alternarRadar">
        <TrendingUp class="h-3.5 w-3.5" /> Oscilações relevantes
      </button>
    </div>

    <div class="rounded-xl border border-gray-200 bg-white shadow-sm">
      <div class="flex flex-col gap-3 border-b border-gray-100 bg-gray-50/70 px-4 py-3 sm:flex-row sm:items-end">
        <label class="flex min-w-0 w-full max-w-md flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500 sm:min-w-[260px]">
          Família do plano de contas
          <select v-model="familiaSelecionada" class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium normal-case text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300" :disabled="loadingInicial || (!anos.length && !anosAnuais.length && !semanas.length)">
            <option value="">Selecione uma família</option>
            <option v-for="familia in familias" :key="familia.id_conta" :value="familia.id_conta">
              {{ familia.codigo_hierarquico }} {{ familia.nome_conta }}
            </option>
          </select>
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

            <label v-if="visao === 'semanal' || (visao === 'mensal' && dados?.mes_aberto) || (visao === 'anual' && dados?.ano_parcial)" class="flex h-[34px] cursor-pointer items-center gap-2 rounded-md border border-gray-200 bg-white px-3 text-xs font-medium text-gray-600">
              <input v-if="visao === 'semanal'" v-model="equivalenteSemanal" type="checkbox" class="accent-[#373435]" />
              <input v-else-if="visao === 'anual'" v-model="equivalenteAnual" type="checkbox" class="accent-[#373435]" />
              <input v-else v-model="equivalenteMensal" type="checkbox" class="accent-[#373435]" />
              Períodos equivalentes
            </label>
          </div>
        </div>

        <div class="min-w-0 border-t border-gray-200 pt-3 xl:border-l xl:border-t-0 xl:pl-4 xl:pt-0" role="group" aria-label="Leitura">
          <div class="flex flex-wrap items-end gap-3">
            <div class="flex flex-col gap-1">
              <span class="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Métrica</span>
              <div class="flex h-[34px] overflow-hidden rounded-md border border-gray-200 text-xs font-semibold">
                <button type="button" class="px-3 transition-colors" :class="metrica === 'valor' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" @click="metrica = 'valor'">Valores financeiros</button>
                <button type="button" class="border-l border-gray-200 px-3 transition-colors" :class="metrica === 'quantidade' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" @click="metrica = 'quantidade'">Quantidades</button>
              </div>
            </div>

            <button type="button" class="flex h-[34px] items-center gap-1.5 rounded-md border border-gray-200 bg-white px-3 text-xs font-medium text-gray-600 hover:bg-gray-100" @click="atualizarAnalise">
              <RefreshCw class="h-3.5 w-3.5" /> Atualizar
            </button>
            <SnapshotDetails v-if="dados" :key="visao" :ultima-venda="dados.ultima_data_disponivel" :atualizado-em="dados.atualizado_em" />
          </div>
        </div>
      </div>

      <section v-if="radarAberto" id="radar-oscilacoes" class="border-b border-gray-200 bg-slate-50/80 px-4 py-4" aria-label="Radar de oscilações relevantes">
        <div class="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div>
            <h2 class="text-sm font-bold text-gray-800">Oscilações relevantes</h2>
            <p class="mt-0.5 text-xs text-gray-500">Categorias folha desta família · análise sempre em R$ · índice mínimo {{ radarDados?.limite_indice ?? '15' }}</p>
          </div>
          <div class="flex items-center gap-2">
            <button type="button" class="rounded-md border border-gray-200 bg-white p-1.5 text-gray-600 hover:bg-gray-100" title="Atualizar radar" aria-label="Atualizar radar" @click="carregarRadar"><RefreshCw class="h-4 w-4" /></button>
            <SnapshotDetails v-if="radarDados" :ultima-venda="radarDados.ultima_data_disponivel" :atualizado-em="radarDados.atualizado_em" />
            <button type="button" class="rounded-md border border-gray-200 bg-white p-1.5 text-gray-600 hover:bg-gray-100" title="Fechar radar" aria-label="Fechar radar" @click="alternarRadar"><X class="h-4 w-4" /></button>
          </div>
        </div>
        <div v-if="radarLoading" class="rounded-lg border border-gray-200 bg-white px-4 py-5 text-center text-xs text-gray-500" role="status">Calculando oscilações nos snapshots...</div>
        <div v-else-if="radarErro" class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700" role="alert">
          <p class="font-semibold">{{ radarErro }}</p>
          <ul v-if="radarConflitos.length" class="mt-2 list-disc pl-5">
            <li v-for="produto in radarConflitos.slice(0, 10)" :key="produto.id_produto">{{ produto.id_produto }} — {{ produto.produto }}</li>
            <li v-if="radarConflitos.length > 10">E mais {{ radarConflitos.length - 10 }} produto(s).</li>
          </ul>
        </div>
        <template v-else-if="radarDados">
          <div class="mb-3 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs text-gray-600">
            <span class="font-semibold text-gray-800">{{ radarDados.visao === 'semanal' ? 'Semana' : 'Mês' }} foco:</span>
            {{ dataCurta(radarDados.periodo_foco.inicio) }} a {{ dataCurta(radarDados.periodo_foco.fim) }}
            <span v-if="radarDados.previa" class="ml-1 font-semibold text-amber-700">· Prévia até {{ dataCurta(radarDados.periodo_foco.corte) }}; todos os períodos cortados no mesmo dia.</span>
            <p class="mt-1 text-gray-500">Médias equivalentes a 30 dias: {{ dataCurta(radarDados.janela_referencia.inicio) }}–{{ dataCurta(radarDados.janela_referencia.fim) }} ({{ radarDados.janela_referencia.periodos }} períodos) versus {{ dataCurta(radarDados.janela_recente.inicio) }}–{{ dataCurta(radarDados.janela_recente.fim) }} ({{ radarDados.janela_recente.periodos }} períodos). O índice prioriza a triagem; não indica a causa da mudança.</p>
          </div>
          <div v-if="!radarDados.disponivel" class="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800" role="status">
            <p class="font-semibold">{{ radarDados.motivo === 'HISTORICO_INCOMPLETO' ? 'Histórico insuficiente para o radar.' : 'Há períodos aguardando atualização.' }}</p>
            <p class="mt-1">São necessários snapshots prontos para toda a janela. Períodos pendentes: {{ radarDados.periodos_pendentes.slice(0, 5).map(periodo => `${dataCurta(periodo.inicio)} (${periodo.status})`).join(', ') }}<span v-if="radarDados.periodos_pendentes.length > 5"> e mais {{ radarDados.periodos_pendentes.length - 5 }}</span>.</p>
          </div>
          <div v-else class="grid gap-3 xl:grid-cols-2">
            <div v-for="grupo in [{ chave: 'quedas', titulo: 'Quedas', icone: TrendingDown, cor: 'text-red-700' }, { chave: 'crescimentos', titulo: 'Crescimentos', icone: TrendingUp, cor: 'text-emerald-700' }]" :key="grupo.chave" class="overflow-hidden rounded-lg border border-gray-200 bg-white">
              <div class="flex items-center gap-2 border-b border-gray-100 px-3 py-2" :class="grupo.cor">
                <component :is="grupo.icone" class="h-4 w-4" />
                <h3 class="text-xs font-bold">{{ grupo.titulo }} ({{ radarDados[grupo.chave].length }})</h3>
              </div>
              <p v-if="!radarDados[grupo.chave].length" class="px-3 py-5 text-xs text-gray-500">Nenhuma categoria ultrapassou o índice mínimo neste recorte.</p>
              <ul v-else class="max-h-[440px] divide-y divide-gray-100 overflow-y-auto">
                <li v-for="linha in radarDados[grupo.chave]" :key="linha.id_conta" class="px-3 py-2.5">
                  <div class="flex items-center gap-2">
                    <span class="font-mono text-[10px] text-gray-400">{{ linha.codigo_hierarquico }}</span>
                    <span class="min-w-0 flex-1 truncate text-xs font-semibold text-gray-800" :title="linha.nome_conta">{{ linha.nome_conta }}</span>
                    <span class="text-[10px] font-bold" :class="grupo.cor">Índice {{ formatarValor(linha.indice, 1) }}</span>
                    <QuarentenaBotao v-if="linha.id_conta !== Number(familiaSelecionada)" :nome="linha.nome_conta" :marcada="marcadas.has(linha.id_conta)" :ocupada="marcacoesPendentes.has(linha.id_conta)" @toggle="alternarMarcacao(linha)" />
                    <button type="button" class="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-800" :aria-label="`Detalhar produtos de ${linha.nome_conta}`" title="Abrir produtos em nova aba" @click="abrirProdutos(linha, true)"><ExternalLink class="h-3.5 w-3.5" /></button>
                  </div>
                  <div class="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-gray-600">
                    <span>Referência: R$ {{ formatarValor(linha.media_referencia, 2) }}</span>
                    <span>Recente: R$ {{ formatarValor(linha.media_recente, 2) }}</span>
                    <span class="font-semibold" :class="grupo.cor">Diferença: {{ Number(linha.diferenca) > 0 ? '+' : '−' }}R$ {{ formatarValor(Math.abs(Number(linha.diferenca)), 2) }} ({{ formatarVariacao(linha.percentual) }})</span>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </template>
      </section>

      <div v-if="dados?.desatualizado" class="flex items-start gap-2 border-b border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
        <AlertTriangle class="mt-0.5 h-4 w-4 shrink-0" />
        <span>Existem períodos aguardando atualização. Os últimos valores válidos continuam visíveis.</span>
      </div>
      <div v-if="erroMarcacao" class="border-b border-red-100 bg-red-50 px-4 py-2 text-xs text-red-700" role="alert">{{ erroMarcacao }}</div>

      <div v-if="visao === 'semanal' && dados && (dados.semana_parcial || dados.periodos_considerados_20 < 20 || dados.periodos_considerados_5 < 5)" class="border-b border-gray-100 bg-gray-50/60 px-4 py-2 text-xs text-gray-600">
        <span v-if="dados.semana_parcial" :class="dados.periodo_equivalente ? 'text-gray-700' : 'font-semibold text-amber-700'">Prévia até {{ dataCurta(dados.semanas?.[5]?.data_corte) }}{{ dados.periodo_equivalente ? '; referências cortadas no mesmo dia da semana.' : '; comparação com semanas anteriores completas.' }}</span>
        <span v-if="dados.periodos_considerados_20 < 20 || dados.periodos_considerados_5 < 5" class="ml-1">Histórico: {{ dados.periodos_considerados_20 }}/20 semanas (últimas cinco: {{ dados.periodos_considerados_5 }}/5).</span>
      </div>
      <div v-if="visao === 'mensal' && dados?.periodo_equivalente" class="border-b border-gray-100 bg-gray-50/60 px-4 py-2 text-xs text-gray-600">
        Meses comparados do dia 1 ao dia {{ dados.dia_corte }}; o total soma apenas os valores exibidos.
      </div>
      <div v-if="visao === 'anual' && dados?.ano_parcial" class="border-b border-gray-100 bg-gray-50/60 px-4 py-2 text-xs text-gray-600">
        <span :class="dados.periodo_equivalente ? 'text-gray-700' : 'font-semibold text-amber-700'">Prévia até {{ dataCurta(dados.anos?.at(-1)?.fim) }}{{ dados.periodo_equivalente ? '; anos anteriores cortados no mesmo mês e dia.' : '; comparação recente com ano anterior completo.' }}</span>
      </div>

      <div v-if="erro" class="border-b border-red-100 bg-red-50 px-4 py-3 text-xs text-red-700">
        <p class="font-semibold">{{ erro }}</p>
        <ul v-if="conflitos.length" class="mt-2 list-disc pl-5">
          <li v-for="produto in conflitos.slice(0, 10)" :key="produto.id_produto">
            {{ produto.id_produto }} — {{ produto.produto }}
          </li>
          <li v-if="conflitos.length > 10">E mais {{ conflitos.length - 10 }} produto(s).</li>
        </ul>
      </div>

      <div v-if="loadingInicial || loading" class="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
        <div class="h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-[#373435]" />
        <div>
          <p class="text-sm font-medium text-gray-700">Processando análise</p>
          <p class="mt-1 text-xs text-gray-400">Consultas de grande volume podem levar alguns segundos.</p>
        </div>
      </div>

      <div v-else-if="!(visao === 'semanal' ? semanas.length : anosDaVisao.length) && !erro" class="flex flex-col items-center justify-center px-6 py-16 text-center">
        <div class="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-amber-50">
          <AlertTriangle class="h-5 w-5 text-amber-500" />
        </div>
        <p class="text-sm font-medium text-gray-600">Agregado analítico ainda não construído</p>
        <p class="mt-1 text-xs text-gray-400">Execute a reconstrução inicial para disponibilizar os anos do relatório.</p>
      </div>

      <div v-else-if="!familiaSelecionada && !erro" class="flex flex-col items-center justify-center px-6 py-16 text-center">
        <div class="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-gray-100">
          <Layers3 class="h-5 w-5 text-gray-400" />
        </div>
        <p class="text-sm font-medium text-gray-600">Selecione uma família</p>
        <p class="mt-1 text-xs text-gray-400">A estrutura completa do plano será exibida nesta matriz.</p>
      </div>

      <div v-else-if="dados && visao === 'mensal'" class="app-scrollbar overflow-x-auto">
        <table class="w-full border-collapse text-xs">
          <thead>
            <tr class="border-b border-gray-100 bg-white">
              <th class="sticky left-0 z-20 min-w-[280px] bg-white px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-400 shadow-[1px_0_0_#f3f4f6]">Categoria</th>
              <th v-for="(mes, indice) in MESES" :key="mes" class="min-w-[100px] px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400" :title="tooltipMesAberto(dados, indice)" :aria-label="tooltipMesAberto(dados, indice) || mes">{{ mes }}</th>
              <th class="min-w-[120px] bg-gray-50 px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-600">{{ dados.periodo_equivalente ? 'Total comparável' : 'Total' }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="linha in linhasVisiveis" :id="`categoria-venda-${linha.id_conta}`" :key="linha.id_conta" class="scroll-mt-32 border-b border-gray-50 last:border-0 hover:bg-gray-50/70" :class="linha.id_conta === Number(route.query.categoria_id) ? 'bg-amber-50/70' : linha.nivel === 0 ? 'bg-gray-50/50 font-bold' : ''">
              <td class="sticky left-0 z-10 bg-white px-4 py-2.5 shadow-[1px_0_0_#f3f4f6]" :class="linha.nivel === 0 ? '!bg-gray-50' : ''">
                <div class="flex items-center" :style="{ paddingLeft: `${linha.nivel * 18}px` }">
                  <button v-if="linha.tem_filhos" type="button" class="mr-1 flex h-5 w-5 items-center justify-center rounded text-gray-400 hover:bg-gray-200 hover:text-gray-700" @click="toggleCategoria(linha.id_conta)">
                    <ChevronDown v-if="expandidas.has(linha.id_conta)" class="h-3.5 w-3.5" />
                    <ChevronRight v-else class="h-3.5 w-3.5" />
                  </button>
                  <span v-else class="mr-1 inline-block h-5 w-5" />
                  <span class="mr-2 font-mono text-[10px] text-gray-400">{{ linha.codigo_hierarquico }}</span>
                  <span class="text-gray-700" :class="linha.tem_filhos ? 'font-semibold' : 'font-medium'">{{ linha.nome_conta }}</span>
                  <QuarentenaBotao v-if="!linha.tem_filhos && linha.conta_pai_id" class="ml-auto" :nome="linha.nome_conta" :marcada="marcadas.has(linha.id_conta)" :ocupada="marcacoesPendentes.has(linha.id_conta)" @toggle="alternarMarcacao(linha)" />
                  <button
                    v-if="!linha.tem_filhos"
                    type="button"
                    class="flex h-6 w-6 shrink-0 items-center justify-center rounded text-gray-400 hover:bg-gray-200 hover:text-gray-700"
                    title="Abrir vendas por produto em uma nova aba"
                    :aria-label="`Detalhar produtos de ${linha.nome_conta}`"
                    @click.stop="abrirProdutos(linha)"
                  >
                    <ExternalLink class="h-3.5 w-3.5" />
                  </button>
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
                  <span v-else class="text-gray-300">0</span>
                </td>
                <td class="bg-gray-50 px-4 py-2 text-right align-top font-mono font-semibold tabular-nums text-gray-800">
                  <div v-if="linha.unidades.length" class="space-y-0.5">
                    <div v-for="unidade in linha.unidades" :key="unidade.id_unidade" class="whitespace-nowrap">
                      {{ formatarQuantidade(unidade.total) }} <span class="text-[9px] text-gray-500">{{ unidade.sigla }}</span>
                    </div>
                  </div>
                  <span v-else class="text-gray-300">0</span>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="dados && visao === 'anual'" class="app-scrollbar overflow-x-auto">
        <table class="w-full border-collapse text-xs">
          <thead><tr class="border-b border-gray-100 bg-white">
            <th class="sticky left-0 z-20 min-w-[280px] bg-white px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-400 shadow-[1px_0_0_#f3f4f6]">Categoria</th>
            <th v-for="periodo in dados.anos" :key="periodo.ano" class="min-w-[145px] px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-600" :title="`${dataCurta(periodo.inicio)} a ${dataCurta(periodo.fim)}`">{{ periodo.ano }}<span v-if="periodo.parcial" class="block font-normal normal-case text-amber-700">Parcial</span><span v-else-if="periodo.equivalente" class="block font-normal normal-case text-gray-400">Até {{ dataCurta(periodo.fim).slice(0, 5) }}</span></th>
            <th class="min-w-[135px] bg-gray-50 px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-600" :title="tituloVariacoesAnuais">Variações<span class="block font-normal normal-case">Média / recente</span></th>
          </tr></thead>
          <tbody>
            <tr v-for="linha in linhasVisiveis" :id="`categoria-venda-${linha.id_conta}`" :key="linha.id_conta" class="scroll-mt-32 border-b border-gray-50 last:border-0 hover:bg-gray-50/70" :class="linha.id_conta === Number(route.query.categoria_id) ? 'bg-amber-50/70' : linha.nivel === 0 ? 'bg-gray-50/50 font-bold' : ''">
              <td class="sticky left-0 z-10 bg-white px-4 py-2.5 shadow-[1px_0_0_#f3f4f6]" :class="linha.nivel === 0 ? '!bg-gray-50' : ''">
                <div class="flex items-center" :style="{ paddingLeft: `${linha.nivel * 18}px` }">
                  <button v-if="linha.tem_filhos" type="button" class="mr-1 flex h-5 w-5 items-center justify-center rounded text-gray-400 hover:bg-gray-200 hover:text-gray-700" @click="toggleCategoria(linha.id_conta)"><ChevronDown v-if="expandidas.has(linha.id_conta)" class="h-3.5 w-3.5" /><ChevronRight v-else class="h-3.5 w-3.5" /></button>
                  <span v-else class="mr-1 inline-block h-5 w-5" />
                  <span class="mr-2 font-mono text-[10px] text-gray-400">{{ linha.codigo_hierarquico }}</span>
                  <span class="text-gray-700" :class="linha.tem_filhos ? 'font-semibold' : 'font-medium'">{{ linha.nome_conta }}</span>
                  <QuarentenaBotao v-if="!linha.tem_filhos && linha.conta_pai_id" class="ml-auto" :nome="linha.nome_conta" :marcada="marcadas.has(linha.id_conta)" :ocupada="marcacoesPendentes.has(linha.id_conta)" @toggle="alternarMarcacao(linha)" />
                  <button v-if="!linha.tem_filhos" type="button" class="flex h-6 w-6 shrink-0 items-center justify-center rounded text-gray-400 hover:bg-gray-200 hover:text-gray-700" title="Abrir vendas anuais por produto em uma nova aba" :aria-label="`Detalhar produtos de ${linha.nome_conta}`" @click.stop="abrirProdutos(linha)"><ExternalLink class="h-3.5 w-3.5" /></button>
                </div>
              </td>
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

      <div v-else-if="dados && visao === 'semanal'" class="app-scrollbar overflow-x-auto">
        <table class="w-full border-collapse text-xs">
          <thead>
            <tr class="border-b border-gray-100 bg-white">
              <th class="sticky left-0 z-20 min-w-[280px] bg-white px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-400 shadow-[1px_0_0_#f3f4f6]">Categoria</th>
              <th class="min-w-[125px] bg-gray-50 px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-600">Média 20 semanas</th>
              <th v-for="(periodo, indice) in dados.semanas" :key="periodo.inicio" class="min-w-[120px] px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider" :class="indice === 5 ? 'bg-gray-50 text-[#373435]' : 'text-gray-400'" :title="`${rotuloSemana(periodo.inicio)}${periodo.data_corte ? ` · até ${dataCurta(periodo.data_corte)}` : ''}`">
                <span v-if="indice === 5" class="block">Semana foco</span>
                {{ dataCurta(periodo.inicio).slice(0, 5) }}–{{ dataCurta(periodo.fim).slice(0, 5) }}
              </th>
              <th class="min-w-[135px] bg-gray-50 px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-600" title="Média: média das últimas 5 semanas contra a média de 20. Recente: semana foco contra a média das últimas 5.">Variações<span class="block font-normal normal-case">Média / recente</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="linha in linhasVisiveis" :id="`categoria-venda-${linha.id_conta}`" :key="linha.id_conta" class="scroll-mt-32 border-b border-gray-50 last:border-0 hover:bg-gray-50/70" :class="linha.id_conta === Number(route.query.categoria_id) ? 'bg-amber-50/70' : linha.nivel === 0 ? 'bg-gray-50/50 font-bold' : ''">
              <td class="sticky left-0 z-10 bg-white px-4 py-2.5 shadow-[1px_0_0_#f3f4f6]" :class="linha.nivel === 0 ? '!bg-gray-50' : ''">
                <div class="flex items-center" :style="{ paddingLeft: `${linha.nivel * 18}px` }">
                  <button v-if="linha.tem_filhos" type="button" class="mr-1 flex h-5 w-5 items-center justify-center rounded text-gray-400 hover:bg-gray-200 hover:text-gray-700" :aria-label="`${expandidas.has(linha.id_conta) ? 'Recolher' : 'Expandir'} ${linha.nome_conta}`" @click="toggleCategoria(linha.id_conta)">
                    <ChevronDown v-if="expandidas.has(linha.id_conta)" class="h-3.5 w-3.5" />
                    <ChevronRight v-else class="h-3.5 w-3.5" />
                  </button>
                  <span v-else class="mr-1 inline-block h-5 w-5" />
                  <span class="mr-2 font-mono text-[10px] text-gray-400">{{ linha.codigo_hierarquico }}</span>
                  <span class="text-gray-700" :class="linha.tem_filhos ? 'font-semibold' : 'font-medium'">{{ linha.nome_conta }}</span>
                  <QuarentenaBotao v-if="!linha.tem_filhos && linha.conta_pai_id" class="ml-auto" :nome="linha.nome_conta" :marcada="marcadas.has(linha.id_conta)" :ocupada="marcacoesPendentes.has(linha.id_conta)" @toggle="alternarMarcacao(linha)" />
                  <button
                    v-if="!linha.tem_filhos"
                    type="button"
                    class="flex h-6 w-6 shrink-0 items-center justify-center rounded text-gray-400 hover:bg-gray-200 hover:text-gray-700"
                    title="Abrir vendas semanais por produto em uma nova aba"
                    :aria-label="`Detalhar produtos de ${linha.nome_conta}`"
                    @click.stop="abrirProdutos(linha)"
                  >
                    <ExternalLink class="h-3.5 w-3.5" />
                  </button>
                </div>
              </td>
              <template v-if="metrica === 'valor'">
                <td class="bg-gray-50 px-3 py-2.5 text-right font-mono tabular-nums text-gray-700">{{ formatarValor(linha.media_20) }}</td>
                <td v-for="(valor, indice) in linha.valores" :key="indice" class="px-3 py-2.5 text-right font-mono tabular-nums text-gray-700" :class="indice === 5 ? 'font-semibold' : ''" :style="estiloLinha(linha, valor, indice)">{{ formatarValor(valor) }}</td>
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
    </div>
  </div>
</template>
