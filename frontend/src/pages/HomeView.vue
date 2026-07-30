<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowRight, ArrowRightLeft, BarChart2, CheckSquare, ClipboardList, TrendingDown, TrendingUp } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import { getApiBaseUrl } from '@/services/firebirdSync'

const API_BASE_URL = getApiBaseUrl()
const kpis = ref(null)
const loading = ref(true)
const semDados = ref(false)
const kpisCompras = ref(null)
const loadingCompras = ref(true)
const semDadosCompras = ref(false)

async function carregarKpis() {
  loading.value = true
  semDados.value = false
  try {
    const res = await fetch(`${API_BASE_URL}/api/analise/dashboard/kpis/`)
    if (res.status === 404) { semDados.value = true; return }
    if (!res.ok) return
    kpis.value = await res.json()
  } catch { /* silencioso */ } finally {
    loading.value = false
  }
}

async function carregarKpisCompras() {
  loadingCompras.value = true
  semDadosCompras.value = false
  try {
    const res = await fetch(`${API_BASE_URL}/api/analise/dashboard/kpis-compras/`)
    if (res.status === 404) { semDadosCompras.value = true; return }
    if (!res.ok) return
    kpisCompras.value = await res.json()
  } catch { /* silencioso */ } finally {
    loadingCompras.value = false
  }
}

onMounted(() => { carregarKpis(); carregarKpisCompras() })

function fmtMoneyFull(v) {
  return Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}

function fmtDate(v) {
  if (!v) return '-'
  const [y, m, d] = v.split('-')
  return `${d}/${m}/${y}`
}

function fmtFator(v) {
  return `${Number(v || 0).toFixed(2)}x`
}

function calcPct(atual, anterior) {
  const a = Number(atual || 0)
  const b = Number(anterior || 0)
  if (b === 0) return null
  return ((a - b) / b * 100).toFixed(1)
}

// ── Anos ────────────────────────────────────────────────────────────────────
const anoAtual = computed(() => kpis.value?.ultima_data_processada?.split('-')[0] ?? '')
const anoAnterior = computed(() => anoAtual.value ? String(Number(anoAtual.value) - 1) : '')

// ── KPI cards ─────────────────────────────────────────────────────────────────
const kpiCards = computed(() => {
  if (!kpis.value) return []
  const k = kpis.value
  const ya = anoAtual.value, yb = anoAnterior.value
  return [
    {
      label: 'Receita Acumulada',
      sub: `YTD — até ${fmtDate(k.ultima_data_processada)}`,
      valor: fmtMoneyFull(k.ytd_receita_atual),
      pct: calcPct(k.ytd_receita_atual, k.ytd_receita_anterior_equivalente),
      tooltip: [
        { ano: ya, valor: fmtMoneyFull(k.ytd_receita_atual),                atual: true  },
        { ano: yb, valor: fmtMoneyFull(k.ytd_receita_anterior_equivalente), atual: false },
      ],
    },
    {
      label: 'Volume de Vendas',
      sub: 'Documentos acumulados no ano',
      valor: Number(k.ytd_volume_atual).toLocaleString('pt-BR'),
      pct: calcPct(k.ytd_volume_atual, k.ytd_volume_anterior_equivalente),
      tooltip: [
        { ano: ya, valor: Number(k.ytd_volume_atual).toLocaleString('pt-BR') + ' docs',                atual: true  },
        { ano: yb, valor: Number(k.ytd_volume_anterior_equivalente).toLocaleString('pt-BR') + ' docs', atual: false },
      ],
    },
    {
      label: 'Ticket Médio',
      sub: 'Receita ÷ Volume YTD',
      valor: fmtMoneyFull(k.ticket_medio_atual),
      pct: calcPct(k.ticket_medio_atual, k.ticket_medio_anterior_equivalente),
      tooltip: [
        { ano: ya, valor: fmtMoneyFull(k.ticket_medio_atual),                atual: true  },
        { ano: yb, valor: fmtMoneyFull(k.ticket_medio_anterior_equivalente), atual: false },
      ],
    },
  ]
})

const anoAtualCompras   = computed(() => kpisCompras.value?.ultima_data_processada?.split('-')[0] ?? '')
const anoAnteriorCompras = computed(() => anoAtualCompras.value ? String(Number(anoAtualCompras.value) - 1) : '')

const kpiCardsCompras = computed(() => {
  if (!kpisCompras.value) return []
  const k = kpisCompras.value
  const ya = anoAtualCompras.value, yb = anoAnteriorCompras.value
  return [
    {
      label: 'Custo Total',
      tipo: 'custo',
      sub: `YTD — até ${fmtDate(k.ultima_data_processada)}`,
      valor: fmtMoneyFull(k.ytd_custo_atual),
      pct: calcPct(k.ytd_custo_atual, k.ytd_custo_anterior_equivalente),
      tooltip: [
        { ano: ya, valor: fmtMoneyFull(k.ytd_custo_atual),                atual: true  },
        { ano: yb, valor: fmtMoneyFull(k.ytd_custo_anterior_equivalente), atual: false },
      ],
    },
    {
      label: 'Fator de Retorno',
      tipo: 'fator',
      sub: 'Receita ÷ Custo YTD',
      valor: fmtFator(k.fator_retorno_atual),
      pct: calcPct(k.fator_retorno_atual, k.fator_retorno_anterior),
      tooltip: [
        { ano: ya, valor: fmtFator(k.fator_retorno_atual),    atual: true  },
        { ano: yb, valor: fmtFator(k.fator_retorno_anterior), atual: false },
      ],
    },
    {
      label: 'Volume de Itens',
      tipo: 'volume',
      sub: 'Itens comprados no período',
      valor: Number(k.volume_itens_atual).toLocaleString('pt-BR'),
      pct: calcPct(k.volume_itens_atual, k.volume_itens_anterior),
      tooltip: [
        { ano: ya, valor: Number(k.volume_itens_atual).toLocaleString('pt-BR') + ' itens',    atual: true  },
        { ano: yb, valor: Number(k.volume_itens_anterior).toLocaleString('pt-BR') + ' itens', atual: false },
      ],
    },
  ]
})

</script>

<template>
  <div class="flex flex-col gap-6">

    <!-- Título -->
    <div>
      <h1 class="text-xl font-bold text-gray-900">Painel de Controle</h1>
      <p class="text-sm text-gray-400 mt-0.5">
        Bem-vindo ao <span class="font-medium text-gray-600">PadariaDigital</span>. Selecione uma área para começar.
      </p>
    </div>

    <!-- ════════════ CARDS DE NAVEGAÇÃO ════════════ -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-5">

      <RouterLink
        to="/validacao/produtos"
        class="group flex flex-col bg-white border border-gray-200 shadow-sm rounded-lg overflow-hidden hover:shadow-md transition-shadow"
      >
        <div class="flex-1 flex flex-col items-center justify-center p-8 gap-3">
          <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#373435] text-white shadow-sm">
            <CheckSquare class="h-6 w-6" />
          </div>
          <div class="text-center">
            <p class="font-semibold text-gray-800">Integração de Dados</p>
            <p class="text-xs text-gray-400 mt-1">Produtos pendentes de validação e conferência de cadastro</p>
          </div>
        </div>
        <div class="bg-[#373435] group-hover:bg-[#4b4948] text-white text-xs font-medium py-2.5 flex items-center justify-center gap-2 transition-colors">
          Acessar <ArrowRight class="h-3.5 w-3.5" />
        </div>
      </RouterLink>

      <RouterLink
        to="/validacao/reconciliacao"
        class="group flex flex-col bg-white border border-gray-200 shadow-sm rounded-lg overflow-hidden hover:shadow-md transition-shadow"
      >
        <div class="flex-1 flex flex-col items-center justify-center p-8 gap-3">
          <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#373435] text-white shadow-sm">
            <ArrowRightLeft class="h-6 w-6" />
          </div>
          <div class="text-center">
            <p class="font-semibold text-gray-800">Integração de Vendas</p>
            <p class="text-xs text-gray-400 mt-1">Sincronização e reconciliação das vendas do sistema legado</p>
          </div>
        </div>
        <div class="bg-[#373435] group-hover:bg-[#4b4948] text-white text-xs font-medium py-2.5 flex items-center justify-center gap-2 transition-colors">
          Acessar <ArrowRight class="h-3.5 w-3.5" />
        </div>
      </RouterLink>

      <RouterLink
        to="/compras/reconciliacao"
        class="group flex flex-col bg-white border border-gray-200 shadow-sm rounded-lg overflow-hidden hover:shadow-md transition-shadow"
      >
        <div class="flex-1 flex flex-col items-center justify-center p-8 gap-3">
          <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#373435] text-white shadow-sm">
            <ClipboardList class="h-6 w-6" />
          </div>
          <div class="text-center">
            <p class="font-semibold text-gray-800">Integração de Compras</p>
            <p class="text-xs text-gray-400 mt-1">Importação e conciliação das notas fiscais de entrada</p>
          </div>
        </div>
        <div class="bg-[#373435] group-hover:bg-[#4b4948] text-white text-xs font-medium py-2.5 flex items-center justify-center gap-2 transition-colors">
          Acessar <ArrowRight class="h-3.5 w-3.5" />
        </div>
      </RouterLink>

    </div>

    <!-- ════════════════ VISÃO GERAL ════════════════ -->
    <div class="flex flex-col lg:flex-row items-stretch gap-4">

      <!-- Card de redirecionamento para o módulo Análises -->
      <RouterLink
        to="/analise"
        class="group flex flex-col bg-white border border-gray-200 shadow-sm rounded-lg overflow-hidden hover:shadow-md transition-shadow lg:w-52 shrink-0"
      >
        <div class="flex-1 flex flex-col items-center justify-center p-6 gap-3">
          <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#373435] text-white shadow-sm">
            <BarChart2 class="h-5 w-5" />
          </div>
          <div class="text-center">
            <p class="font-semibold text-gray-800">Análises</p>
            <p class="text-xs text-gray-400 mt-1">Painel gerencial de vendas e compras</p>
          </div>
        </div>
        <div class="bg-[#373435] group-hover:bg-[#4b4948] text-white text-xs font-medium py-2.5 flex items-center justify-center gap-2 transition-colors">
          Ver análises <ArrowRight class="h-3.5 w-3.5" />
        </div>
      </RouterLink>

      <!-- Coluna direita: vendas (linha 1) e compras (linha 2) -->
      <div class="flex-1 flex flex-col gap-4">

        <!-- Linha 1: KPIs de Vendas -->
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-2 px-0.5">Vendas</p>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <template v-if="loading">
              <div v-for="i in 3" :key="i" class="rounded-lg border border-gray-200 bg-white shadow-sm p-4 animate-pulse space-y-2">
                <div class="h-3 bg-gray-100 rounded w-1/2" />
                <div class="h-6 bg-gray-100 rounded w-3/4" />
                <div class="h-3 bg-gray-100 rounded w-1/3" />
              </div>
            </template>
            <template v-else-if="kpis">
              <div
                v-for="card in kpiCards"
                :key="card.label"
                class="group relative rounded-lg border border-gray-200 bg-white shadow-sm p-4 cursor-default"
              >
                <p class="text-[10px] uppercase tracking-wide text-gray-400 font-semibold">{{ card.label }}</p>
                <div class="mt-2 flex items-end justify-between gap-2">
                  <p class="text-xl font-bold text-[#373435] leading-none">{{ card.valor }}</p>
                  <span
                    v-if="card.pct !== null"
                    class="inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-[10px] font-bold leading-none"
                    :class="Number(card.pct) >= 0 ? 'bg-[#d7fce1] text-[#2f6f4f]' : 'bg-red-50 text-[#a82631]'"
                  >
                    <TrendingUp v-if="Number(card.pct) >= 0" class="h-2.5 w-2.5" />
                    <TrendingDown v-else class="h-2.5 w-2.5" />
                    {{ Number(card.pct) >= 0 ? '+' : '' }}{{ card.pct }}%
                  </span>
                  <span v-else class="text-[10px] text-gray-300">N/A</span>
                </div>
                <p class="text-[10px] text-gray-400 mt-1">{{ card.sub }}</p>
                <div class="pointer-events-none absolute top-full left-1/2 -translate-x-1/2 mt-2 hidden group-hover:block z-20">
                  <div class="relative bg-gray-900 text-white rounded-lg px-3 py-2.5 text-[11px] shadow-xl whitespace-nowrap min-w-[180px]">
                    <div class="absolute bottom-full left-1/2 -translate-x-1/2 border-[5px] border-transparent border-b-gray-900" />
                    <div v-for="row in card.tooltip" :key="row.ano" class="flex items-center justify-between gap-6 py-0.5">
                      <span :class="row.atual ? 'text-emerald-400 font-semibold' : 'text-gray-400'">{{ row.ano }}</span>
                      <span :class="row.atual ? 'font-bold text-white' : 'text-gray-300'">{{ row.valor }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <template v-else>
              <div v-for="i in 3" :key="i" class="rounded-lg border border-dashed border-gray-100 bg-gray-50 p-4 flex flex-col justify-center gap-1">
                <p class="text-[10px] uppercase tracking-wide text-gray-300 font-semibold">—</p>
                <p class="text-xl font-bold text-gray-200">—</p>
                <p class="text-[10px] text-gray-300">Aguardando dados</p>
              </div>
            </template>
          </div>
        </div>

        <!-- Linha 2: KPIs de Compras -->
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-2 px-0.5">Compras</p>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <template v-if="loadingCompras">
              <div v-for="i in 3" :key="i" class="rounded-lg border border-gray-200 bg-white shadow-sm p-4 animate-pulse space-y-2">
                <div class="h-3 bg-gray-100 rounded w-1/2" />
                <div class="h-6 bg-gray-100 rounded w-3/4" />
                <div class="h-3 bg-gray-100 rounded w-1/3" />
              </div>
            </template>
            <template v-else-if="kpisCompras">
              <div
                v-for="card in kpiCardsCompras"
                :key="card.label"
                class="group relative rounded-lg border border-gray-200 bg-white shadow-sm p-4 cursor-default"
              >
                <p class="text-[10px] uppercase tracking-wide text-gray-400 font-semibold">{{ card.label }}</p>
                <div class="mt-2 flex items-end justify-between gap-2">
                  <p class="text-xl font-bold text-[#373435] leading-none">{{ card.valor }}</p>
                  <span
                    v-if="card.pct !== null"
                    class="inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-[10px] font-bold leading-none"
                    :class="card.tipo === 'volume'
                      ? 'bg-slate-100 text-slate-600'
                      : card.tipo === 'custo'
                        ? (Number(card.pct) >= 0 ? 'bg-red-50 text-[#a82631]' : 'bg-[#d7fce1] text-[#2f6f4f]')
                        : (Number(card.pct) >= 0 ? 'bg-[#d7fce1] text-[#2f6f4f]' : 'bg-red-50 text-[#a82631]')"
                  >
                    <TrendingUp v-if="Number(card.pct) >= 0" class="h-2.5 w-2.5" />
                    <TrendingDown v-else class="h-2.5 w-2.5" />
                    {{ Number(card.pct) >= 0 ? '+' : '' }}{{ card.pct }}%
                  </span>
                  <span v-else class="text-[10px] text-gray-300">N/A</span>
                </div>
                <p class="text-[10px] text-gray-400 mt-1">{{ card.sub }}</p>
                <div class="pointer-events-none absolute top-full left-1/2 -translate-x-1/2 mt-2 hidden group-hover:block z-20">
                  <div class="relative bg-gray-900 text-white rounded-lg px-3 py-2.5 text-[11px] shadow-xl whitespace-nowrap min-w-[180px]">
                    <div class="absolute bottom-full left-1/2 -translate-x-1/2 border-[5px] border-transparent border-b-gray-900" />
                    <div v-for="row in card.tooltip" :key="row.ano" class="flex items-center justify-between gap-6 py-0.5">
                      <span :class="row.atual ? 'text-emerald-400 font-semibold' : 'text-gray-400'">{{ row.ano }}</span>
                      <span :class="row.atual ? 'font-bold text-white' : 'text-gray-300'">{{ row.valor }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <template v-else>
              <div v-for="i in 3" :key="i" class="rounded-lg border border-dashed border-gray-100 bg-gray-50 p-4 flex flex-col justify-center gap-1">
                <p class="text-[10px] uppercase tracking-wide text-gray-300 font-semibold">—</p>
                <p class="text-xl font-bold text-gray-200">—</p>
                <p class="text-[10px] text-gray-300">Aguardando dados</p>
              </div>
            </template>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>
