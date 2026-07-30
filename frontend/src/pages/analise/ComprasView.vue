<script setup>
import { computed, onMounted, ref } from 'vue'
import { BarChart2, TrendingDown, TrendingUp } from 'lucide-vue-next'
import { getApiBaseUrl } from '@/services/firebirdSync'

const API_BASE_URL = getApiBaseUrl()
const kpis = ref(null)
const loading = ref(true)
const semDados = ref(false)

async function carregarKpis() {
  loading.value = true
  semDados.value = false
  try {
    const res = await fetch(`${API_BASE_URL}/api/analise/dashboard/kpis-compras/`)
    if (res.status === 404) { semDados.value = true; return }
    if (!res.ok) return
    kpis.value = await res.json()
  } catch { /* silencioso */ } finally {
    loading.value = false
  }
}

onMounted(carregarKpis)

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

// ── Anos ────────────────────────────────────────────────────────────────────────────
const anoAtual    = computed(() => kpis.value?.ultima_data_processada?.split('-')[0] ?? '')
const anoAnterior = computed(() => anoAtual.value ? String(Number(anoAtual.value) - 1) : '')

// ── KPI cards ───────────────────────────────────────────────────────────────────
const kpiCards = computed(() => {
  if (!kpis.value) return []
  const k = kpis.value
  const ya = anoAtual.value, yb = anoAnterior.value
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

// ── Bar Chart ─────────────────────────────────────────────────────────────────
const BC_W = 560, BC_H = 180
const BC_PL = 8, BC_PR = 8, BC_PT = 10, BC_PB = 24
const BC_IW = BC_W - BC_PL - BC_PR  // 544
const BC_IH = BC_H - BC_PT - BC_PB  // 146

const barChart = computed(() => {
  const dados = kpis.value?.dados_mensais_grafico
  if (!dados?.length) return null

  const vals = dados.flatMap(d => [d.custo_atual, d.custo_anterior]).filter(v => v != null && v > 0)
  if (!vals.length) return null

  const maxVal = Math.max(...vals) * 1.1
  const n = dados.length
  const groupW = BC_IW / n
  const antW = Math.max(groupW * 0.38, 4)
  const atuW = Math.max(groupW * 0.38, 3)
  const baseY = BC_PT + BC_IH

  const bh = v => v != null && v > 0 ? Math.max((v / maxVal) * BC_IH, 1) : 0

  const bars = dados.map((d, i) => {
    const cx   = BC_PL + i * groupW + groupW / 2
    const hAnt = bh(d.custo_anterior)
    const hAtu = bh(d.custo_atual)
    return {
      ant: { x: +(cx - antW / 2).toFixed(2), y: +(baseY - hAnt).toFixed(2), w: +antW.toFixed(2), h: +hAnt.toFixed(2) },
      atu: { x: +(cx - atuW / 2).toFixed(2), y: +(baseY - hAtu).toFixed(2), w: +atuW.toFixed(2), h: +hAtu.toFixed(2) },
      labelX: +cx.toFixed(2),
      labelY: BC_H - 6,
      label: d.label,
    }
  })

  const gridY = [1, 2, 3, 4].map(i => +(BC_PT + (i / 4) * BC_IH).toFixed(2))

  return { bars, gridY, baseY: +baseY.toFixed(2) }
})

// ── Ticker mensal ──────────────────────────────────────────────────────────────
const mesAtualNum = computed(() => {
  if (!kpis.value?.ultima_data_processada) return -1
  return parseInt(kpis.value.ultima_data_processada.split('-')[1])
})

const ticker = computed(() => {
  const dados = kpis.value?.dados_mensais_grafico
  if (!dados?.length) return []
  const ya = anoAtual.value, yb = anoAnterior.value
  return dados.map(d => {
    const isAtual = d.mes === mesAtualNum.value
    const ca = isAtual ? Number(kpis.value.mtd_custo_atual || 0)                : (d.custo_atual    ?? null)
    const cb = isAtual ? Number(kpis.value.mtd_custo_anterior_equivalente || 0) : (d.custo_anterior ?? null)
    const pct = ca != null && cb != null ? calcPct(ca, cb) : null
    return {
      label: d.label, mes: d.mes, pct, isAtual,
      // custo menor = positivo (bom)
      positivo: pct != null && Number(pct) < 0,
      show: ca != null,
      valorAtual:    ca != null ? fmtMoneyFull(ca) : null,
      valorAnterior: cb != null ? fmtMoneyFull(cb) : null,
      anoAtual: ya, anoAnterior: yb,
    }
  }).filter(d => d.show)
})
</script>

<template>
  <div class="flex flex-col gap-6">

    <!-- Título -->
    <div>
      <h1 class="text-xl font-bold text-gray-900">Análise de Compras</h1>
      <p class="text-sm text-gray-400 mt-0.5">Custo acumulado, fator de retorno e volume de itens comprados no ano.</p>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm animate-pulse">
      <div class="h-10 bg-gray-50 border-b border-gray-100" />
      <div class="grid grid-cols-1 lg:grid-cols-[260px_1fr] divide-x divide-gray-100 p-4 gap-4">
        <div class="space-y-3">
          <div v-for="i in 3" :key="i" class="rounded-lg border border-gray-100 p-3 space-y-2">
            <div class="h-3 bg-gray-100 rounded w-1/2" />
            <div class="h-6 bg-gray-100 rounded w-3/4" />
            <div class="h-3 bg-gray-100 rounded w-1/3" />
          </div>
        </div>
        <div class="space-y-2 pl-4">
          <div class="h-3 bg-gray-100 rounded w-1/4" />
          <div class="h-40 bg-gray-100 rounded" />
          <div class="flex gap-1.5">
            <div v-for="i in 7" :key="i" class="h-5 bg-gray-100 rounded w-10" />
          </div>
        </div>
      </div>
    </div>

    <!-- Sem dados -->
    <div v-else-if="semDados" class="rounded-xl border border-dashed border-gray-200 bg-white px-6 py-8 text-center">
      <div class="flex h-10 w-10 items-center justify-center rounded-full bg-amber-50 mx-auto mb-3">
        <BarChart2 class="h-5 w-5 text-amber-400" />
      </div>
      <p class="text-sm font-medium text-gray-600">KPIs de compras ainda não calculados</p>
      <p class="text-xs text-gray-400 mt-1">Execute o sistema ou consolide compras para gerar o painel.</p>
    </div>

    <!-- Dashboard com dados -->
    <div v-else-if="kpis" class="rounded-xl border border-gray-200 bg-white shadow-sm">

      <!-- Cabeçalho -->
      <div class="flex items-center justify-between rounded-t-xl bg-gradient-to-r from-amber-50 to-white px-4 py-2.5 border-b border-amber-100">
        <div class="flex items-center gap-2">
          <div class="flex h-5 w-5 items-center justify-center rounded-full bg-amber-600 shadow-sm">
            <BarChart2 class="h-3 w-3 text-white" />
          </div>
          <span class="text-xs font-bold uppercase tracking-wider text-amber-800">Painel de Compras</span>
        </div>
        <span class="text-[10px] text-gray-400">Dados até {{ fmtDate(kpis.ultima_data_processada) }}</span>
      </div>

      <!-- Corpo: KPIs + Gráfico -->
      <div class="grid grid-cols-1 lg:grid-cols-[260px_1fr] divide-y lg:divide-y-0 lg:divide-x divide-gray-100">

        <!-- KPIs YTD -->
        <div class="p-4 space-y-2.5">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Acumulado do Ano</p>
          <div
            v-for="card in kpiCards"
            :key="card.label"
            class="group relative rounded-lg border border-gray-100 bg-gray-50/50 px-3 py-2.5 cursor-default"
          >
            <p class="text-[10px] uppercase tracking-wide text-gray-400 font-semibold">{{ card.label }}</p>
            <div class="mt-1 flex items-end justify-between gap-2">
              <p class="text-lg font-bold text-[#373435] leading-none">{{ card.valor }}</p>
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

            <!-- Tooltip com valores absolutos de ambos os anos -->
            <div class="pointer-events-none absolute top-full left-1/2 -translate-x-1/2 mt-2 hidden group-hover:block z-20">
              <div class="relative bg-gray-900 text-white rounded-lg px-3 py-2.5 text-[11px] shadow-xl whitespace-nowrap min-w-[180px]">
                <div class="absolute bottom-full left-1/2 -translate-x-1/2 border-[5px] border-transparent border-b-gray-900" />
                <div v-for="row in card.tooltip" :key="row.ano" class="flex items-center justify-between gap-6 py-0.5">
                  <span :class="row.atual ? 'text-amber-400 font-semibold' : 'text-gray-400'">{{ row.ano }}</span>
                  <span :class="row.atual ? 'font-bold text-white' : 'text-gray-300'">{{ row.valor }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Gráfico + Ticker -->
        <div class="p-4 flex flex-col gap-3">

          <!-- Legenda -->
          <div class="flex items-center justify-between">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Custo Mensal</p>
            <div class="flex items-center gap-4">
              <div class="flex items-center gap-1.5">
                <div class="h-2.5 w-2.5 rounded-sm bg-gray-300" />
                <span class="text-[10px] text-gray-400">{{ anoAnterior }}</span>
              </div>
              <div class="flex items-center gap-1.5">
                <div class="h-2.5 w-2.5 rounded-sm" style="background:#d97706" />
                <span class="text-[10px] text-gray-500 font-medium">{{ anoAtual }}</span>
              </div>
            </div>
          </div>

          <!-- Bar Chart -->
          <div v-if="barChart" class="flex-1 min-h-[120px]">
            <svg
              viewBox="0 0 560 180"
              class="w-full h-full"
              preserveAspectRatio="none"
            >
              <line
                v-for="y in barChart.gridY" :key="y"
                :x1="BC_PL" :x2="BC_W - BC_PR"
                :y1="y" :y2="y"
                stroke="#f3f4f6" stroke-width="1"
              />
              <line
                :x1="BC_PL" :x2="BC_W - BC_PR"
                :y1="barChart.baseY" :y2="barChart.baseY"
                stroke="#e5e7eb" stroke-width="1"
              />
              <g v-for="b in barChart.bars" :key="b.label">
                <rect
                  v-if="b.atu.h > 0"
                  :x="b.atu.x" :y="b.atu.y"
                  :width="b.atu.w" :height="b.atu.h"
                  fill="#d97706" rx="1.5" ry="1.5"
                />
                <rect
                  v-if="b.ant.h > 0"
                  :x="b.ant.x" :y="b.ant.y"
                  :width="b.ant.w" :height="b.ant.h"
                  fill="#d97706" fill-opacity="0.3"
                  rx="1.5" ry="1.5"
                />
                <text
                  :x="b.labelX" :y="b.labelY"
                  text-anchor="middle"
                  font-size="8" fill="#9ca3af"
                >{{ b.label }}</text>
              </g>
            </svg>
          </div>

          <!-- Ticker mensal -->
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="t in ticker" :key="t.mes"
              class="group relative inline-flex items-center gap-0.5 rounded-md px-2 py-1 text-[10px] font-semibold cursor-default"
              :class="t.isAtual
                ? 'ring-1 ring-inset ring-gray-300 bg-white text-gray-700'
                : t.pct === null
                  ? 'bg-gray-50 text-gray-400'
                  : t.positivo
                    ? 'bg-[#d7fce1] text-[#2f6f4f]'
                    : 'bg-red-50 text-[#a82631]'"
            >
              {{ t.label }}
              <template v-if="t.pct !== null">
                {{ Number(t.pct) >= 0 ? '+' : '' }}{{ t.pct }}%
              </template>
              <span v-if="t.isAtual" class="ml-0.5 text-gray-400">*</span>

              <!-- Tooltip com custo de ambos os anos -->
              <div class="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-20">
                <div class="relative bg-gray-900 text-white rounded-lg px-3 py-2 text-[11px] shadow-xl whitespace-nowrap min-w-[160px]">
                  <div class="absolute top-full left-1/2 -translate-x-1/2 border-[5px] border-transparent border-t-gray-900" />
                  <p class="text-gray-400 text-[10px] mb-1 font-semibold">{{ t.label }}{{ t.isAtual ? ' · MTD' : '' }}</p>
                  <div class="flex items-center justify-between gap-6">
                    <span class="text-amber-400 font-semibold">{{ t.anoAtual }}</span>
                    <span class="font-bold text-white">{{ t.valorAtual }}</span>
                  </div>
                  <div v-if="t.valorAnterior" class="flex items-center justify-between gap-6">
                    <span class="text-gray-400">{{ t.anoAnterior }}</span>
                    <span class="text-gray-300">{{ t.valorAnterior }}</span>
                  </div>
                </div>
              </div>
            </span>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>
