<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AlertTriangle, BarChart2, TrendingDown, TrendingUp } from 'lucide-vue-next'
import ReceitaComparativaChart from '@/components/vendas/ReceitaComparativaChart.vue'
import TurnosChart from '@/components/vendas/TurnosChart.vue'
import VolumeTicketChart from '@/components/vendas/VolumeTicketChart.vue'
import { getApiBaseUrl } from '@/services/firebirdSync'

const API_BASE_URL = getApiBaseUrl()
const route = useRoute()
const router = useRouter()
const kpis = ref(null)
const loading = ref(true)
const semDados = ref(false)
const granularidade = ref(route.query.granularidade === 'semanal' ? 'semanal' : 'mensal')

async function carregarKpis() {
  loading.value = true
  semDados.value = false
  try {
    const res = await fetch(`${API_BASE_URL}/api/analise/dashboard/kpis/`)
    if (res.status === 404) { semDados.value = true; return }
    if (!res.ok) return
    kpis.value = await res.json()
  } catch { /* O dashboard mantém o estado vazio quando a API estiver indisponível. */ } finally {
    loading.value = false
  }
}

onMounted(carregarKpis)

watch(granularidade, (valor) => {
  router.replace({ query: { ...route.query, granularidade: valor } })
})

watch(() => route.query.granularidade, (valor) => {
  const normalizado = valor === 'semanal' ? 'semanal' : 'mensal'
  if (granularidade.value !== normalizado) granularidade.value = normalizado
})

function fmtMoneyFull(valor) {
  return Number(valor || 0).toLocaleString('pt-BR', {
    style: 'currency', currency: 'BRL', maximumFractionDigits: 0,
  })
}

function fmtDate(valor) {
  if (!valor) return '-'
  const [ano, mes, dia] = valor.split('-')
  return `${dia}/${mes}/${ano}`
}

function calcPct(atual, anterior) {
  const valorAtual = Number(atual || 0)
  const valorAnterior = Number(anterior || 0)
  if (valorAnterior === 0) return null
  return ((valorAtual - valorAnterior) / valorAnterior * 100).toFixed(1)
}

const anoAtual = computed(() => kpis.value?.ultima_data_processada?.split('-')[0] ?? '')
const anoAnterior = computed(() => anoAtual.value ? String(Number(anoAtual.value) - 1) : '')

function cardMedia(k, chave, label, unidadeSingular, unidadePlural) {
  const media = k.faturamento_medio?.[chave]
  const periodos = Number(media?.periodos_considerados || 0)
  const possuiMedia = periodos > 0
  return {
    label,
    sub: possuiMedia ? `${periodos} ${periodos === 1 ? unidadeSingular : unidadePlural} encerrad${periodos === 1 ? 'a' : 'as'}` : 'Nenhum período encerrado',
    valor: possuiMedia ? fmtMoneyFull(media.atual) : '-',
    pct: possuiMedia ? calcPct(media.atual, media.anterior_equivalente) : null,
    tooltip: possuiMedia ? [
      { ano: anoAtual.value, valor: fmtMoneyFull(media.atual), atual: true },
      { ano: anoAnterior.value, valor: fmtMoneyFull(media.anterior_equivalente), atual: false },
    ] : [],
  }
}

const kpiCards = computed(() => {
  if (!kpis.value) return []
  const k = kpis.value
  return [
    {
      label: 'Receita Acumulada',
      sub: `YTD — até ${fmtDate(k.ultima_data_processada)}`,
      valor: fmtMoneyFull(k.ytd_receita_atual),
      pct: calcPct(k.ytd_receita_atual, k.ytd_receita_anterior_equivalente),
      tooltip: [
        { ano: anoAtual.value, valor: fmtMoneyFull(k.ytd_receita_atual), atual: true },
        { ano: anoAnterior.value, valor: fmtMoneyFull(k.ytd_receita_anterior_equivalente), atual: false },
      ],
    },
    {
      label: 'Volume de Vendas',
      sub: 'Documentos acumulados no ano',
      valor: Number(k.ytd_volume_atual).toLocaleString('pt-BR'),
      pct: calcPct(k.ytd_volume_atual, k.ytd_volume_anterior_equivalente),
      tooltip: [
        { ano: anoAtual.value, valor: `${Number(k.ytd_volume_atual).toLocaleString('pt-BR')} docs`, atual: true },
        { ano: anoAnterior.value, valor: `${Number(k.ytd_volume_anterior_equivalente).toLocaleString('pt-BR')} docs`, atual: false },
      ],
    },
    {
      label: 'Ticket Médio',
      sub: 'Receita ÷ Volume YTD',
      valor: fmtMoneyFull(k.ticket_medio_atual),
      pct: calcPct(k.ticket_medio_atual, k.ticket_medio_anterior_equivalente),
      tooltip: [
        { ano: anoAtual.value, valor: fmtMoneyFull(k.ticket_medio_atual), atual: true },
        { ano: anoAnterior.value, valor: fmtMoneyFull(k.ticket_medio_anterior_equivalente), atual: false },
      ],
    },
    cardMedia(k, 'semanal', 'Faturamento Semanal Médio', 'semana', 'semanas'),
    cardMedia(k, 'mensal', 'Faturamento Mensal Médio', 'mês', 'meses'),
  ]
})

const series = computed(() => {
  const novasSeries = kpis.value?.graficos?.[granularidade.value]
  if (novasSeries?.length) return novasSeries
  if (granularidade.value !== 'mensal') return []

  // Compatibilidade durante a implantação, antes da primeira atualização dos novos KPIs.
  const mesAtual = Number(kpis.value?.ultima_data_processada?.split('-')[1] || 0)
  return (kpis.value?.dados_mensais_grafico ?? [])
    .filter((item) => item.mes <= mesAtual)
    .map((item) => {
      const parcial = item.mes === mesAtual
      const receitaAtual = parcial ? kpis.value.mtd_receita_atual : item.receita_atual
      const receitaAnterior = parcial ? kpis.value.mtd_receita_anterior_equivalente : item.receita_anterior
      const volume = Number(item.volume_atual || 0)
      return {
        ...item,
        indice: item.mes,
        parcial,
        data_corte: parcial ? kpis.value.ultima_data_processada : null,
        receita_atual: receitaAtual,
        receita_anterior_equivalente: receitaAnterior,
        volume_atual: volume,
        ticket_medio_atual: volume ? Number(receitaAtual || 0) / volume : null,
        faturamento_manha: 0,
        faturamento_tarde: 0,
      }
    })
})

const serieReceita = computed(() => {
  if (granularidade.value !== 'mensal') return series.value
  const historicoMensal = kpis.value?.dados_mensais_grafico ?? []
  if (!historicoMensal.length) return series.value

  const periodosAtuais = new Map(series.value.map((item) => [Number(item.indice), item]))
  return historicoMensal.map((item, indice) => periodosAtuais.get(indice + 1) ?? {
    indice: indice + 1,
    label: item.label,
    parcial: false,
    futuro: true,
    receita_atual: null,
    receita_anterior_equivalente: item.receita_anterior,
    volume_atual: 0,
    ticket_medio_atual: null,
    faturamento_manha: 0,
    faturamento_tarde: 0,
  })
})

const variacoesMensais = computed(() => {
  if (granularidade.value !== 'mensal') return []
  return series.value.map((item) => {
    const pct = calcPct(item.receita_atual, item.receita_anterior_equivalente)
    return {
      ...item,
      pct,
      positivo: pct !== null && Number(pct) >= 0,
      valorAtual: fmtMoneyFull(item.receita_atual),
      valorAnterior: fmtMoneyFull(item.receita_anterior_equivalente),
    }
  })
})

const vendasSemHorario = computed(() => ({
  quantidade: Number(kpis.value?.vendas_sem_horario?.quantidade || 0),
  faturamento: kpis.value?.vendas_sem_horario?.faturamento || 0,
}))

const dadosExpandidosDisponiveis = computed(() => Boolean(kpis.value?.graficos?.mensal?.length))
const tituloPeriodo = computed(() => granularidade.value === 'semanal' ? 'Semanal' : 'Mensal')
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-gray-900">Análise de Vendas</h1>
        <p class="mt-0.5 text-sm text-gray-400">Receita, volume, ticket médio e distribuição do faturamento por turno.</p>
      </div>
      <div class="flex flex-col gap-1">
        <span class="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Granularidade dos gráficos</span>
        <div class="flex h-[34px] overflow-hidden rounded-md border border-gray-200 text-xs font-semibold">
          <button type="button" class="px-4 transition-colors" :class="granularidade === 'mensal' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" @click="granularidade = 'mensal'">Mensal</button>
          <button type="button" class="border-l border-gray-200 px-4 transition-colors" :class="granularidade === 'semanal' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" @click="granularidade = 'semanal'">Semanal</button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm animate-pulse">
      <div class="h-10 border-b border-gray-100 bg-gray-50" />
      <div class="grid grid-cols-1 gap-4 p-4 lg:grid-cols-[300px_1fr]">
        <div class="space-y-2.5"><div v-for="i in 5" :key="i" class="h-20 rounded-lg bg-gray-100" /></div>
        <div class="h-64 rounded-lg bg-gray-100" />
      </div>
    </div>

    <div v-else-if="semDados" class="rounded-xl border border-dashed border-gray-200 bg-white px-6 py-8 text-center">
      <div class="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-gray-100"><BarChart2 class="h-5 w-5 text-gray-400" /></div>
      <p class="text-sm font-medium text-gray-600">KPIs ainda não calculados</p>
      <p class="mt-1 text-xs text-gray-400">Execute o sistema ou consolide vendas para gerar o painel.</p>
    </div>

    <template v-else-if="kpis">
      <section class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <div class="flex items-center justify-between border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white px-4 py-2.5">
          <div class="flex items-center gap-2">
            <div class="flex h-5 w-5 items-center justify-center rounded-full bg-[#373435] shadow-sm"><BarChart2 class="h-3 w-3 text-white" /></div>
            <span class="text-xs font-bold uppercase tracking-wider text-[#373435]">Visão geral de vendas</span>
          </div>
          <span class="text-[10px] text-gray-400">Dados até {{ fmtDate(kpis.ultima_data_processada) }}</span>
        </div>

        <div class="grid grid-cols-1 divide-y divide-gray-100 lg:grid-cols-[300px_1fr] lg:divide-x lg:divide-y-0">
          <div class="space-y-2.5 p-4">
            <p class="mb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400">Indicadores</p>
            <div v-for="card in kpiCards" :key="card.label" class="group relative cursor-default rounded-lg border border-gray-100 bg-gray-50/50 px-3 py-2.5">
              <p class="text-[10px] font-semibold uppercase tracking-wide text-gray-400">{{ card.label }}</p>
              <div class="mt-1 flex items-end justify-between gap-2">
                <p class="text-lg font-bold leading-none text-[#373435]">{{ card.valor }}</p>
                <span v-if="card.pct !== null" class="inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-[10px] font-bold leading-none" :class="Number(card.pct) >= 0 ? 'bg-[#d7fce1] text-[#2f6f4f]' : 'bg-red-50 text-[#a82631]'">
                  <TrendingUp v-if="Number(card.pct) >= 0" class="h-2.5 w-2.5" />
                  <TrendingDown v-else class="h-2.5 w-2.5" />
                  {{ Number(card.pct) >= 0 ? '+' : '' }}{{ card.pct }}%
                </span>
                <span v-else class="text-[10px] text-gray-300">N/A</span>
              </div>
              <p class="mt-1 text-[10px] text-gray-400">{{ card.sub }}</p>
              <div v-if="card.tooltip.length" class="pointer-events-none absolute left-1/2 top-full z-20 mt-2 hidden -translate-x-1/2 group-hover:block">
                <div class="relative min-w-[180px] whitespace-nowrap rounded-lg bg-gray-900 px-3 py-2.5 text-[11px] text-white shadow-xl">
                  <div class="absolute bottom-full left-1/2 -translate-x-1/2 border-[5px] border-transparent border-b-gray-900" />
                  <div v-for="row in card.tooltip" :key="row.ano" class="flex items-center justify-between gap-6 py-0.5">
                    <span :class="row.atual ? 'font-semibold text-emerald-400' : 'text-gray-400'">{{ row.ano }}</span>
                    <span :class="row.atual ? 'font-bold text-white' : 'text-gray-300'">{{ row.valor }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <section class="rounded-xl border border-gray-200 bg-white shadow-sm">
            <div class="flex min-w-0 flex-col gap-3 p-4">
              <div class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-4 py-3">
                <div>
                  <p class="text-[10px] font-semibold uppercase tracking-wider text-gray-500">Receita {{ tituloPeriodo }}</p>
                  <p class="text-[10px] text-gray-400">Comparação com período equivalente do ano anterior</p>
                </div>
                <div class="flex items-center gap-4">
                  <div class="flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-sm bg-gray-300" /><span class="text-[10px] text-gray-400">{{ anoAnterior }}</span></div>
                  <div class="flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-sm bg-[#2f6f4f]" /><span class="text-[10px] font-medium text-gray-500">{{ anoAtual }}</span></div>
                </div>
              </div>
              <ReceitaComparativaChart :series="serieReceita" :granularidade="granularidade" :ano-atual="anoAtual" :ano-anterior="anoAnterior" />

              <div v-if="variacoesMensais.length" class="flex flex-wrap gap-1.5">
                <span v-for="item in variacoesMensais" :key="item.indice" class="group relative inline-flex cursor-default items-center gap-0.5 rounded-md px-2 py-1 text-[10px] font-semibold" :class="item.parcial ? 'bg-white text-gray-700 ring-1 ring-inset ring-gray-300' : item.pct === null ? 'bg-gray-50 text-gray-400' : item.positivo ? 'bg-[#d7fce1] text-[#2f6f4f]' : 'bg-red-50 text-[#a82631]'">
                  {{ item.label }}<template v-if="item.pct !== null"> {{ item.positivo ? '+' : '' }}{{ item.pct }}%</template><span v-if="item.parcial" class="ml-0.5 text-gray-400">*</span>
                  <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden -translate-x-1/2 group-hover:block">
                    <span class="block min-w-[170px] whitespace-nowrap rounded-lg bg-gray-900 px-3 py-2 text-[11px] text-white shadow-xl">
                      <span class="mb-1 block text-[10px] font-semibold text-gray-400">{{ item.label }}{{ item.parcial ? ` · parcial até ${fmtDate(item.data_corte)}` : '' }}</span>
                      <span class="flex justify-between gap-6"><b class="text-emerald-400">{{ anoAtual }}</b><b>{{ item.valorAtual }}</b></span>
                      <span class="flex justify-between gap-6 text-gray-300"><span class="text-gray-400">{{ anoAnterior }}</span><span>{{ item.valorAnterior }}</span></span>
                    </span>
                  </span>
                </span>
              </div>
              <p v-if="series.some((item) => item.parcial)" class="text-[10px] text-gray-400">* Período parcial até {{ fmtDate(kpis.ultima_data_processada) }}.</p>
            </div>

            <div class="grid min-w-0 grid-cols-1 gap-4 xl:grid-cols-2">
              <section class="flex min-w-0 flex-col rounded-xl border border-gray-200 bg-white shadow-sm">
                <div class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-4 py-3">
                  <div><h2 class="text-sm font-bold text-gray-800">Volume de Vendas × Ticket Médio</h2><p class="mt-0.5 text-xs text-gray-400">Quantidade de documentos e valor médio por venda no ano {{ anoAtual }}.</p></div>
                  <div class="flex items-center gap-4 text-[10px] text-gray-500"><span class="flex items-center gap-1.5"><i class="h-2.5 w-2.5 rounded-sm bg-gray-400" />Volume</span><span class="flex items-center gap-1.5"><i class="h-0.5 w-4 bg-[#2f6f4f]" />Ticket médio</span></div>
                </div>
                <div class="flex-1 p-4"><VolumeTicketChart :series="dadosExpandidosDisponiveis ? series : []" :granularidade="granularidade" /></div>
              </section>

              <section class="flex min-w-0 flex-col rounded-xl border border-gray-200 bg-white shadow-sm">
                <div class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-4 py-3">
                  <div><h2 class="text-sm font-bold text-gray-800">Participação do Faturamento por Turno</h2><p class="mt-0.5 text-xs text-gray-400">Participação sobre as vendas com horário: manhã até 12:59:59 e tarde a partir de 13:00:00, no ano {{ anoAtual }}.</p></div>
                  <div class="flex items-center gap-4 text-[10px] text-gray-500"><span class="flex items-center gap-1.5"><i class="h-0.5 w-4 bg-amber-600" />Manhã</span><span class="flex items-center gap-1.5"><i class="h-0.5 w-4 bg-blue-600" />Tarde</span></div>
                </div>
                <div class="flex-1 p-4">
                  <TurnosChart :series="dadosExpandidosDisponiveis ? series : []" :granularidade="granularidade" />
                  <div v-if="vendasSemHorario.quantidade" class="mt-3 flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                    <AlertTriangle class="mt-0.5 h-4 w-4 shrink-0" />
                    <span>{{ vendasSemHorario.quantidade.toLocaleString('pt-BR') }} venda(s) ({{ fmtMoneyFull(vendasSemHorario.faturamento) }}) sem horário não aparecem neste gráfico.</span>
                  </div>
                </div>
              </section>
            </div>



          </section>

        </div>
      </section>


    </template>
  </div>
</template>
