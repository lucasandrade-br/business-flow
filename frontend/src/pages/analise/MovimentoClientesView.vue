<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { CalendarDays, ChevronDown, TrendingDown, TrendingUp } from 'lucide-vue-next'
import { getApiBaseUrl } from '@/services/firebirdSync'

const API_BASE_URL = getApiBaseUrl()
const ENDPOINT = `${API_BASE_URL}/api/analise/dashboard/movimento-clientes/`

const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

// ── Estado ────────────────────────────────────────────────────────────────────
const anosDisponiveis  = ref([])
const tiposDisponiveis = ref([])
const anoSelecionado   = ref(null)
const mesSelecionado   = ref(null)
const tiposSelecionados = ref([])   // vazio = todos
const tiposAberto      = ref(false)

const dados    = ref(null)
const loading  = ref(true)
const semDados = ref(false)

// ── Carregamento ──────────────────────────────────────────────────────────────
async function carregarFiltros() {
  try {
    const res = await fetch(ENDPOINT)
    if (res.status === 404) { semDados.value = true; loading.value = false; return }
    if (!res.ok) { loading.value = false; return }
    const json = await res.json()
    anosDisponiveis.value  = json.anos_disponiveis ?? []
    tiposDisponiveis.value = json.tipos_disponiveis ?? []
    if (anosDisponiveis.value.length) {
      anoSelecionado.value = anosDisponiveis.value[0]
    } else {
      semDados.value = true
      loading.value = false
    }
  } catch {
    loading.value = false
  }
}

async function carregarDados() {
  if (!anoSelecionado.value) return
  loading.value = true
  try {
    const params = new URLSearchParams({ ano: anoSelecionado.value })
    if (mesSelecionado.value) params.set('mes', mesSelecionado.value)
    if (tiposSelecionados.value.length) params.set('tipos', tiposSelecionados.value.join(','))

    const res = await fetch(`${ENDPOINT}?${params}`)
    if (!res.ok) return
    const json = await res.json()
    dados.value = json
    mesSelecionado.value = json.mes_consultado
  } catch { /* silencioso */ } finally {
    loading.value = false
  }
}

onMounted(carregarFiltros)
watch(anoSelecionado, () => { mesSelecionado.value = null; carregarDados() })
watch(mesSelecionado, (v, old) => { if (old !== null && v !== null) carregarDados() })
watch(tiposSelecionados, carregarDados, { deep: true })

// ── Filtro de tipos ───────────────────────────────────────────────────────────
function toggleTipo(id) {
  const i = tiposSelecionados.value.indexOf(id)
  if (i === -1) tiposSelecionados.value.push(id)
  else tiposSelecionados.value.splice(i, 1)
}

const rotuloTipos = computed(() => {
  const n = tiposSelecionados.value.length
  if (n === 0) return 'Todos os tipos'
  if (n === 1) return tiposDisponiveis.value.find(t => t.id === tiposSelecionados.value[0])?.descricao ?? '1 tipo'
  return `${n} tipos selecionados`
})

// ── Formatadores ──────────────────────────────────────────────────────────────
const fmtInt = (v) => v === null || v === undefined ? '—' : Number(v).toLocaleString('pt-BR')

const fmtDec = (v) => v === null || v === undefined ? '—'
  : Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

const fmtMoney = (v) => v === null || v === undefined ? '—'
  : Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 0 })

const fmtTicket = (v) => v === null || v === undefined ? '—'
  : Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const fmtDia = (iso) => {
  const [, m, d] = iso.split('-')
  return `${d}/${m}`
}

const anoAnterior = computed(() => anoSelecionado.value ? Number(anoSelecionado.value) - 1 : '')

const mesesDisponiveis = computed(() =>
  (dados.value?.meses_com_dados ?? []).map(m => ({ valor: m, label: MESES[m - 1] }))
)

// ── Modo da matriz semanal ──────────────────────────────────────────────
const modoMatriz = ref('media')   // 'soma' = total do mês | 'media' = média por dia

const linhasMatriz = computed(() => {
  const rows = dados.value?.matriz_semanal ?? []
  const soma = modoMatriz.value === 'soma'
  return rows.map(r => ({
    dia: r.dia,
    label: r.label,
    meses: soma ? r.meses_soma : r.meses_media,
    media: soma ? r.media_soma : r.media_dia,
    variacao: soma ? r.variacao_soma : r.variacao_dia,
  }))
})

const fmtCel = (v) => v === null || v === undefined ? '—' : Math.round(v).toLocaleString('pt-BR')

// Escala de cor da coluna Média: vermelho (menores) → amarelo → verde (maiores).
const ESCALA_MEDIA = [
  [168, 38, 49],   // #a82631
  [217, 119, 6],   // #d97706
  [47, 111, 79],   // #2f6f4f
]

// Posição relativa (0..1) por ranking, não por amplitude: um zero isolado
// vira apenas o último colocado, sem comprimir os demais no topo da escala.
function mapaRanking(vals) {
  const unicos = [...new Set(vals)].sort((a, b) => a - b)
  if (unicos.length < 2) return null
  return new Map(unicos.map((v, i) => [v, i / (unicos.length - 1)]))
}

const rankMedia = computed(() =>
  mapaRanking(linhasMatriz.value.map(r => r.media).filter(v => v !== null && v !== undefined))
)

function estiloMedia(v) {
  if (v === null || v === undefined || !rankMedia.value) return {}
  const t = rankMedia.value.get(v)
  if (t === undefined) return {}
  const [de, para] = t < 0.5 ? [ESCALA_MEDIA[0], ESCALA_MEDIA[1]] : [ESCALA_MEDIA[1], ESCALA_MEDIA[2]]
  const k = t < 0.5 ? t * 2 : (t - 0.5) * 2
  const rgb = de.map((c, i) => Math.round(c + (para[i] - c) * k))
  return { backgroundColor: `rgba(${rgb.join(', ')}, 0.28)` }
}

// Células dos meses: ranking independente por linha, pintando só os extremos.
const LIMIAR_EXTREMO = 0.25

function estiloCelula(row, v) {
  if (v === null || v === undefined) return {}
  const vals = row.meses.filter(x => x !== null && x !== undefined)
  // Menos de 3 meses não forma ranking com significado.
  if (vals.length < 3) return {}

  const mapa = mapaRanking(vals)
  if (!mapa) return {}
  const t = mapa.get(v)
  if (t === undefined) return {}

  if (t >= 1 - LIMIAR_EXTREMO) {
    const k = (t - (1 - LIMIAR_EXTREMO)) / LIMIAR_EXTREMO
    return { backgroundColor: `rgba(47, 111, 79, ${(0.10 + k * 0.20).toFixed(3)})` }
  }
  if (t <= LIMIAR_EXTREMO) {
    const k = (LIMIAR_EXTREMO - t) / LIMIAR_EXTREMO
    return { backgroundColor: `rgba(168, 38, 49, ${(0.10 + k * 0.20).toFixed(3)})` }
  }
  return {}
}
</script>

<template>
  <div class="flex flex-col gap-6">

    <!-- Título -->
    <div>
      <h1 class="text-xl font-bold text-gray-900">Movimento de Clientes</h1>
      <p class="text-sm text-gray-400 mt-0.5">Frequência de vendas por dia da semana e evolução diária do mês.</p>
    </div>

    <!-- Sem dados -->
    <div v-if="semDados && !loading" class="rounded-xl border border-dashed border-gray-200 bg-white px-6 py-8 text-center">
      <div class="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100 mx-auto mb-3">
        <CalendarDays class="h-5 w-5 text-gray-400" />
      </div>
      <p class="text-sm font-medium text-gray-600">Nenhum dado disponível</p>
      <p class="text-xs text-gray-400 mt-1">Execute o sistema para consolidar o movimento diário.</p>
    </div>

    <template v-else>
      <!-- ════════ Barra de filtros ════════ -->
      <div class="flex flex-wrap items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm">
        <div class="flex items-center gap-2">
          <label class="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Ano</label>
          <select
            v-model="anoSelecionado"
            class="rounded-md border border-gray-200 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300"
          >
            <option v-for="a in anosDisponiveis" :key="a" :value="a">{{ a }}</option>
          </select>
        </div>

        <div class="flex items-center gap-2">
          <label class="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Mês</label>
          <select
            v-model="mesSelecionado"
            class="rounded-md border border-gray-200 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300"
          >
            <option v-for="m in mesesDisponiveis" :key="m.valor" :value="m.valor">{{ m.label }}</option>
          </select>
        </div>

        <!-- Multi-select de tipos -->
        <div class="relative">
          <button
            type="button"
            class="flex items-center gap-2 rounded-md border border-gray-200 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            @click="tiposAberto = !tiposAberto"
          >
            {{ rotuloTipos }}
            <ChevronDown class="h-3 w-3 text-gray-400 transition-transform" :class="tiposAberto ? 'rotate-180' : ''" />
          </button>

          <div
            v-if="tiposAberto"
            class="absolute left-0 top-full mt-1.5 z-30 w-56 rounded-md border border-gray-200 bg-white shadow-lg overflow-hidden"
          >
            <button
              type="button"
              class="w-full px-3 py-2 text-left text-xs font-medium border-b border-gray-100 hover:bg-gray-50"
              :class="tiposSelecionados.length === 0 ? 'text-[#2f6f4f]' : 'text-gray-500'"
              @click="tiposSelecionados = []"
            >Todos os tipos</button>
            <label
              v-for="t in tiposDisponiveis"
              :key="t.id"
              class="flex items-center gap-2 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 cursor-pointer"
            >
              <input
                type="checkbox"
                class="h-3 w-3 accent-[#373435]"
                :checked="tiposSelecionados.includes(t.id)"
                @change="toggleTipo(t.id)"
              />
              {{ t.descricao }}
            </label>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="space-y-4">
        <div class="rounded-xl border border-gray-200 bg-white p-4 space-y-2 animate-pulse">
          <div v-for="i in 7" :key="i" class="h-8 bg-gray-100 rounded" />
        </div>
      </div>

      <template v-else-if="dados">
        <!-- ════════ Matriz semanal ════════ -->
        <div class="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div class="flex items-center justify-between rounded-t-xl bg-gradient-to-r from-gray-50 to-white px-4 py-2.5 border-b border-gray-100">
            <div class="flex items-center gap-2">
              <div class="flex h-5 w-5 items-center justify-center rounded-full bg-[#373435] shadow-sm">
                <CalendarDays class="h-3 w-3 text-white" />
              </div>
              <span class="text-xs font-bold uppercase tracking-wider text-[#373435]">Vendas por Dia da Semana</span>
            </div>

            <div class="flex items-center gap-3">
              <div class="flex rounded-md border border-gray-200 overflow-hidden text-[10px] font-semibold">
                <button
                  @click="modoMatriz = 'soma'"
                  class="px-3 py-1 transition-colors"
                  :class="modoMatriz === 'soma' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-50'"
                >Total do Mês</button>
                <button
                  @click="modoMatriz = 'media'"
                  class="px-3 py-1 transition-colors"
                  :class="modoMatriz === 'media' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-50'"
                >Média por Dia</button>
              </div>
              <span class="text-[10px] text-gray-400">vs {{ anoAnterior }}</span>
            </div>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-gray-100">
                  <th class="sticky left-0 z-10 bg-white px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-400 w-20 shadow-[1px_0_0_#f3f4f6]">Dia</th>
                  <th
                    v-for="m in MESES" :key="m"
                    class="px-2 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400 min-w-[60px]"
                  >{{ m }}</th>
                  <th class="px-3 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-500 min-w-[80px] bg-gray-50">Média</th>
                  <th class="px-3 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400 min-w-[80px]">vs {{ anoAnterior }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(row, idx) in linhasMatriz"
                  :key="row.dia"
                  class="border-b border-gray-50 last:border-0"
                  :class="idx % 2 !== 0 ? 'bg-gray-50/60' : 'bg-white'"
                >
                  <td
                    class="sticky left-0 z-10 px-4 py-2 text-xs font-bold text-gray-700 shadow-[1px_0_0_#f3f4f6]"
                    :class="idx % 2 !== 0 ? 'bg-gray-50/60' : 'bg-white'"
                  >{{ row.label }}</td>
                  <td
                    v-for="(v, i) in row.meses" :key="i"
                    class="px-2 py-2 text-right font-mono text-xs tabular-nums"
                    :class="v !== null ? 'text-gray-700' : 'text-gray-300'"
                    :style="estiloCelula(row, v)"
                  >{{ fmtCel(v) }}</td>
                  <td
                    class="px-3 py-2 text-right font-mono text-xs tabular-nums font-bold text-gray-800"
                    :style="estiloMedia(row.media)"
                  >{{ fmtCel(row.media) }}</td>
                  <td
                    class="px-3 py-2 text-right font-mono text-xs tabular-nums font-semibold"
                    :class="row.variacao === null ? 'text-gray-300'
                      : row.variacao >= 0 ? 'text-[#2f6f4f]' : 'text-[#a82631]'"
                  >
                    <span v-if="row.variacao === null">—</span>
                    <span v-else class="inline-flex items-center gap-0.5 justify-end">
                      <TrendingUp v-if="row.variacao >= 0" class="h-3 w-3" />
                      <TrendingDown v-else class="h-3 w-3" />
                      {{ row.variacao >= 0 ? '+' : '' }}{{ row.variacao }}%
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- ════════ Detalhe do mês ════════ -->
        <div class="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div class="flex items-center justify-between rounded-t-xl bg-gradient-to-r from-gray-50 to-white px-4 py-2.5 border-b border-gray-100">
            <div class="flex items-center gap-2">
              <div class="flex h-5 w-5 items-center justify-center rounded-full bg-[#373435] shadow-sm">
                <CalendarDays class="h-3 w-3 text-white" />
              </div>
              <span class="text-xs font-bold uppercase tracking-wider text-[#373435]">
                Detalhe de {{ MESES[(dados.mes_consultado ?? 1) - 1] }} / {{ dados.ano_consultado }}
              </span>
            </div>
          </div>

          <!-- gap-px sobre fundo cinza cria separadores de 1px nas duas direções do grid -->
          <div class="grid grid-cols-1 xl:grid-cols-2 gap-px bg-gray-100">
            <div v-for="grupo in dados.detalhe_mensal" :key="grupo.dia" class="bg-white p-4">
              <p class="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-2">{{ grupo.label }}</p>

              <p v-if="!grupo.ocorrencias.length" class="text-xs text-gray-300">Sem ocorrências no mês</p>

              <div v-else class="overflow-x-auto">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="border-b border-gray-100">
                      <th class="sticky left-0 z-10 bg-white px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-400 w-32 shadow-[1px_0_0_#f3f4f6]">Métrica</th>
                      <th
                        v-for="o in grupo.ocorrencias" :key="o.data"
                        class="px-2 py-2 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400 min-w-[76px]"
                      >{{ fmtDia(o.data) }}</th>
                      <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-500 min-w-[90px] bg-blue-50/40">Média</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr class="border-b border-gray-50 bg-white">
                      <td class="sticky left-0 z-10 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 shadow-[1px_0_0_#f3f4f6]">Qtd de Vendas</td>
                      <td v-for="o in grupo.ocorrencias" :key="o.data" class="px-2 py-1.5 text-right font-mono text-xs tabular-nums text-gray-700">{{ fmtInt(o.qtd) }}</td>
                      <td class="px-3 py-1.5 text-right font-mono text-xs tabular-nums font-semibold text-gray-800 bg-blue-50/40">{{ fmtDec(grupo.media_qtd) }}</td>
                    </tr>
                    <tr class="border-b border-gray-50 bg-gray-50/60">
                      <td class="sticky left-0 z-10 bg-gray-50/60 px-3 py-1.5 text-xs font-medium text-gray-700 shadow-[1px_0_0_#f3f4f6]">Valor Total</td>
                      <td v-for="o in grupo.ocorrencias" :key="o.data" class="px-2 py-1.5 text-right font-mono text-xs tabular-nums text-gray-700">{{ fmtMoney(o.valor) }}</td>
                      <td class="px-3 py-1.5 text-right font-mono text-xs tabular-nums font-semibold text-gray-800 bg-blue-50/40">{{ fmtMoney(grupo.media_valor) }}</td>
                    </tr>
                    <tr class="bg-white">
                      <td class="sticky left-0 z-10 bg-white px-3 py-1.5 text-xs font-bold text-gray-700 shadow-[1px_0_0_#f3f4f6]">Ticket Médio</td>
                      <td v-for="o in grupo.ocorrencias" :key="o.data" class="px-2 py-1.5 text-right font-mono text-xs tabular-nums font-bold text-gray-800">{{ fmtTicket(o.ticket) }}</td>
                      <td class="px-3 py-1.5 text-right font-mono text-xs tabular-nums font-bold text-gray-800 bg-blue-50/40">{{ fmtTicket(grupo.media_ticket) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </template>
    </template>

  </div>
</template>
