<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { BarChart2 } from 'lucide-vue-next'
import { getApiBaseUrl } from '@/services/firebirdSync'

const API_BASE_URL = getApiBaseUrl()

// ── Estado ────────────────────────────────────────────────────────────────────
const anosDisponiveis = ref([])
const anoSelecionado  = ref(null)
const visao           = ref('anual')  // 'anual' | 'mensal'
const dados           = ref(null)
const loading         = ref(true)
const semDados        = ref(false)

// ── Carregamento ──────────────────────────────────────────────────────────────
async function carregarAnos() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/analise/dashboard/dre/`)
    if (res.status === 404) { semDados.value = true; loading.value = false; return }
    if (!res.ok) { loading.value = false; return }
    const json = await res.json()
    anosDisponiveis.value = json.anos_disponiveis ?? []
    if (anosDisponiveis.value.length) {
      anoSelecionado.value = anosDisponiveis.value[0]  // mais recente primeiro
    } else {
      semDados.value = true
      loading.value = false
    }
  } catch {
    loading.value = false
  }
}

async function carregarDre(ano) {
  loading.value = true
  semDados.value = false
  dados.value = null
  try {
    const res = await fetch(`${API_BASE_URL}/api/analise/dashboard/dre/?ano=${ano}`)
    if (res.status === 404) { semDados.value = true; return }
    if (!res.ok) return
    dados.value = await res.json()
  } catch { /* silencioso */ } finally {
    loading.value = false
  }
}

onMounted(carregarAnos)
watch(anoSelecionado, (ano) => { if (ano) carregarDre(ano) })

// ── Formatadores ──────────────────────────────────────────────────────────────
const fmtR = (v) =>
  v === null || v === undefined ? '—'
  : Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })

const fmtRVar = (v) => {
  if (v === null || v === undefined) return '—'
  const n = Number(v)
  return (n > 0 ? '+' : '') + n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}

const fmtP = (v, dec = 1) =>
  v === null || v === undefined ? '—' : `${Number(v).toFixed(dec)}%`

const fmtX = (v) =>
  v === null || v === undefined ? '—' : `${Number(v).toFixed(2)}x`

const sgn = (v) => Number(v) >= 0 ? '+' : ''

// ── Anos ──────────────────────────────────────────────────────────────────────
const anoAtual    = computed(() => anoSelecionado.value ?? '')
const anoAnterior = computed(() => anoAtual.value ? Number(anoAtual.value) - 1 : '')

// ── Cor das variações ─────────────────────────────────────────────────────────
// tipo 'custo': alta é ruim (vermelho); tipo 'normal': alta é boa (verde)
function corVar(tipo, val) {
  if (val === null || val === undefined) return 'text-gray-300'
  const alta = Number(val) >= 0
  if (tipo === 'custo') return alta ? 'text-[#a82631]' : 'text-[#2f6f4f]'
  return alta ? 'text-[#2f6f4f]' : 'text-[#a82631]'
}

// ── Linhas: comparativo anual ─────────────────────────────────────────────────
const linhasAnuais = computed(() => {
  if (!dados.value) return []
  const { receita, custo, margem_bruta, margem_percentual, fator_retorno } = dados.value.visao_anual
  const mgpA = margem_percentual.atual,  mgpB = margem_percentual.anterior
  const fatA = fator_retorno.atual,      fatB = fator_retorno.anterior

  return [
    {
      label: 'Receita Total', tipo: 'normal', bold: false, destaque: false,
      vAnt: fmtR(receita.anterior), vAtu: fmtR(receita.atual),
      nom: { v: receita.var_nominal,  t: fmtRVar(receita.var_nominal) },
      rel: { v: receita.var_relativa, t: receita.var_relativa !== null ? `${sgn(receita.var_relativa)}${Number(receita.var_relativa).toFixed(1)}%` : '—' },
    },
    {
      label: 'Custo Total', tipo: 'custo', bold: false, destaque: false,
      vAnt: fmtR(custo.anterior), vAtu: fmtR(custo.atual),
      nom: { v: custo.var_nominal,  t: fmtRVar(custo.var_nominal) },
      rel: { v: custo.var_relativa, t: custo.var_relativa !== null ? `${sgn(custo.var_relativa)}${Number(custo.var_relativa).toFixed(1)}%` : '—' },
    },
    {
      label: 'Margem Bruta', tipo: 'normal', bold: true, destaque: true,
      vAnt: fmtR(margem_bruta.anterior), vAtu: fmtR(margem_bruta.atual),
      nom: { v: margem_bruta.var_nominal,  t: fmtRVar(margem_bruta.var_nominal) },
      rel: { v: margem_bruta.var_relativa, t: margem_bruta.var_relativa !== null ? `${sgn(margem_bruta.var_relativa)}${Number(margem_bruta.var_relativa).toFixed(1)}%` : '—' },
    },
    {
      label: 'Margem %', tipo: 'normal', bold: false, destaque: false,
      vAnt: fmtP(mgpB), vAtu: fmtP(mgpA),
      nom: { v: null, t: '—' },
      rel: {
        v: mgpA !== null && mgpB !== null ? mgpA - mgpB : null,
        t: mgpA !== null && mgpB !== null ? `${sgn(mgpA - mgpB)}${(mgpA - mgpB).toFixed(1)}%` : '—',
      },
    },
    {
      label: 'Fator de Retorno', tipo: 'normal', bold: false, destaque: false,
      vAnt: fmtX(fatB), vAtu: fmtX(fatA),
      nom: { v: null, t: '—' },
      rel: {
        v: fatA !== null && fatB !== null ? fatA - fatB : null,
        t: fatA !== null && fatB !== null ? `${sgn(fatA - fatB)}${(fatA - fatB).toFixed(2)}x` : '—',
      },
    },
  ]
})

// ── Linhas: evolução mensal ───────────────────────────────────────────────────
const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

const mensal = computed(() => {
  if (!dados.value) return null
  const rec = dados.value.visao_mensal.receita
  const cst = dados.value.visao_mensal.custo

  const mgMeses  = rec.map((r, i) => r !== null && cst[i] !== null ? r - cst[i] : null)
  const mgpMeses = rec.map((r, i) => {
    const m = mgMeses[i]
    return m !== null && r && r !== 0 ? (m / r) * 100 : null
  })
  const fatMeses = rec.map((r, i) => {
    const c = cst[i]
    return r !== null && c !== null && c !== 0 ? r / c : null
  })

  const tRec = rec.reduce((s, v) => s + (v ?? 0), 0)
  const tCst = cst.reduce((s, v) => s + (v ?? 0), 0)
  const tMg  = tRec - tCst
  const tMgP = tRec > 0 ? (tMg / tRec) * 100 : null
  const tFat = tCst > 0 ? tRec / tCst         : null

  return [
    { label: 'Receita Total',    bold: false, destaque: false, meses: rec,      total: tRec,  fmt: fmtR,              fmtT: fmtR },
    { label: 'Custo Total',      bold: false, destaque: false, meses: cst,      total: tCst,  fmt: fmtR,              fmtT: fmtR },
    { label: 'Margem Bruta',     bold: true,  destaque: true,  meses: mgMeses,  total: tMg,   fmt: fmtR,              fmtT: fmtR },
    { label: 'Margem %',         bold: false, destaque: false, meses: mgpMeses, total: tMgP,  fmt: (v) => fmtP(v, 1), fmtT: (v) => fmtP(v, 1) },
    { label: 'Fator de Retorno', bold: false, destaque: false, meses: fatMeses, total: tFat,  fmt: fmtX,              fmtT: fmtX },
  ]
})
</script>

<template>
  <div class="flex flex-col gap-6">

    <!-- Título -->
    <div>
      <h1 class="text-xl font-bold text-gray-900">DRE Gerencial</h1>
      <p class="text-sm text-gray-400 mt-0.5">Demonstrativo de resultado — receita, custo e margem por período.</p>
    </div>

    <!-- Sem dados -->
    <div v-if="semDados && !loading" class="rounded-xl border border-dashed border-gray-200 bg-white px-6 py-8 text-center">
      <div class="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100 mx-auto mb-3">
        <BarChart2 class="h-5 w-5 text-gray-400" />
      </div>
      <p class="text-sm font-medium text-gray-600">Nenhum dado disponível</p>
      <p class="text-xs text-gray-400 mt-1">Execute o sistema para consolidar os dados do DRE.</p>
    </div>

    <!-- Painel principal -->
    <div v-else class="rounded-xl border border-gray-200 bg-white shadow-sm">

      <!-- Cabeçalho com controles -->
      <div class="flex flex-wrap items-center justify-between gap-3 rounded-t-xl bg-gradient-to-r from-gray-50 to-white px-4 py-2.5 border-b border-gray-100">
        <div class="flex items-center gap-2">
          <div class="flex h-5 w-5 items-center justify-center rounded-full bg-[#373435] shadow-sm">
            <BarChart2 class="h-3 w-3 text-white" />
          </div>
          <span class="text-xs font-bold uppercase tracking-wider text-[#373435]">DRE Gerencial</span>
        </div>

        <div class="flex items-center gap-3">
          <!-- Seletor de ano -->
          <select
            v-model="anoSelecionado"
            class="rounded-md border border-gray-200 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300"
          >
            <option v-for="a in anosDisponiveis" :key="a" :value="a">{{ a }}</option>
          </select>

          <!-- Toggle de visão -->
          <div class="flex rounded-md border border-gray-200 overflow-hidden text-[10px] font-semibold">
            <button
              @click="visao = 'anual'"
              class="px-3 py-1 transition-colors"
              :class="visao === 'anual' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-50'"
            >Comparativo Anual</button>
            <button
              @click="visao = 'mensal'"
              class="px-3 py-1 transition-colors"
              :class="visao === 'mensal' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-50'"
            >Evolução Mensal</button>
          </div>
        </div>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="p-4 space-y-2 animate-pulse">
        <div v-for="i in 5" :key="i" class="h-9 bg-gray-100 rounded" />
      </div>

      <!-- Tabela: Comparativo Anual -->
      <div v-else-if="visao === 'anual' && dados" class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-100">
              <th class="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-400 w-40">Métrica</th>
              <th class="px-4 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400">{{ anoAnterior }}</th>
              <th class="px-4 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-500">{{ anoAtual }}</th>
              <th class="px-4 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400">Var. Nominal</th>
              <th class="px-4 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400">Variação</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, idx) in linhasAnuais"
              :key="row.label"
              class="border-b border-gray-50 last:border-0"
              :class="row.destaque ? 'bg-blue-50/40' : idx % 2 !== 0 ? 'bg-gray-50/60' : 'bg-white'"
            >
              <td
                class="px-4 py-2.5 text-xs text-gray-700"
                :class="row.bold ? 'font-bold' : 'font-medium'"
              >{{ row.label }}</td>
              <td class="px-4 py-2.5 text-right font-mono text-xs tabular-nums text-gray-400">{{ row.vAnt }}</td>
              <td
                class="px-4 py-2.5 text-right font-mono text-xs tabular-nums"
                :class="row.bold ? 'font-bold text-gray-800' : 'text-gray-700'"
              >{{ row.vAtu }}</td>
              <td
                class="px-4 py-2.5 text-right font-mono text-xs tabular-nums font-semibold"
                :class="corVar(row.tipo, row.nom.v)"
              >{{ row.nom.t }}</td>
              <td
                class="px-4 py-2.5 text-right font-mono text-xs tabular-nums font-semibold"
                :class="corVar(row.tipo, row.rel.v)"
              >{{ row.rel.t }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Tabela: Evolução Mensal -->
      <div v-else-if="visao === 'mensal' && mensal" class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-100">
              <th class="sticky left-0 z-10 bg-white px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-400 w-36 shadow-[1px_0_0_#f3f4f6]">Métrica</th>
              <th
                v-for="m in MESES"
                :key="m"
                class="px-2 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400 min-w-[72px]"
              >{{ m }}</th>
              <th class="px-4 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-500 min-w-[96px]">Total</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, idx) in mensal"
              :key="row.label"
              class="border-b border-gray-50 last:border-0"
              :class="row.destaque ? 'bg-blue-50/40' : idx % 2 !== 0 ? 'bg-gray-50/60' : 'bg-white'"
            >
              <!-- Coluna fixo ao scroll horizontal -->
              <td
                class="sticky left-0 z-10 px-4 py-2 text-xs text-gray-700 shadow-[1px_0_0_#f3f4f6]"
                :class="[row.destaque ? 'bg-blue-50/40' : idx % 2 !== 0 ? 'bg-gray-50/60' : 'bg-white', row.bold ? 'font-bold' : 'font-medium']"
              >{{ row.label }}</td>
              <td
                v-for="(v, i) in row.meses"
                :key="i"
                class="px-2 py-2 text-right font-mono text-xs tabular-nums"
                :class="v !== null ? 'text-gray-700' : 'text-gray-300'"
              >{{ row.fmt(v) }}</td>
              <td
                class="px-4 py-2 text-right font-mono text-xs tabular-nums"
                :class="row.bold ? 'font-bold text-gray-800' : 'font-semibold text-gray-700'"
              >{{ row.fmtT(row.total) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>

  </div>
</template>
