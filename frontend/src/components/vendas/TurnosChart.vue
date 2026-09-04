<script setup>
import { computed } from 'vue'

const props = defineProps({
  series: { type: Array, default: () => [] },
  granularidade: { type: String, default: 'mensal' },
})

const H = 230
const PT = 18
const PB = 30

const fmtPercentual = (valor) => Number(valor).toLocaleString('pt-BR', {
  minimumFractionDigits: 1, maximumFractionDigits: 1,
})

const fmtData = (valor) => {
  if (!valor) return ''
  const [, mes, dia] = valor.split('-')
  return `${dia}/${mes}`
}

function caminhoSuave(pontos) {
  if (!pontos.length) return ''
  return pontos.slice(1).reduce((path, ponto, indice) => {
    const anterior = pontos[indice]
    const controleX = (anterior.x + ponto.x) / 2
    return `${path} C ${controleX} ${anterior.y}, ${controleX} ${ponto.y}, ${ponto.x} ${ponto.y}`
  }, `M ${pontos[0].x} ${pontos[0].y}`)
}

function caminhoComLacunas(itens, campo) {
  const segmentos = []
  let segmento = []
  for (const item of itens) {
    if (item[campo] === null) {
      if (segmento.length) segmentos.push(segmento)
      segmento = []
      continue
    }
    segmento.push({ x: item.cx, y: item[campo] })
  }
  if (segmento.length) segmentos.push(segmento)
  return segmentos.map(caminhoSuave).join(' ')
}

const chart = computed(() => {
  const dados = props.series ?? []
  if (!dados.length) return null
  const width = Math.max(760, dados.length * (props.granularidade === 'semanal' ? 30 : 58))
  const innerH = H - PT - PB
  const baseY = PT + innerH
  const groupW = width / dados.length
  const itens = dados.map((item, indice) => {
    const cx = indice * groupW + groupW / 2
    const faturamentoManha = Number(item.faturamento_manha || 0)
    const faturamentoTarde = Number(item.faturamento_tarde || 0)
    const faturamentoClassificado = faturamentoManha + faturamentoTarde
    const manhaPercentual = faturamentoClassificado > 0
      ? faturamentoManha / faturamentoClassificado * 100
      : null
    const tardePercentual = manhaPercentual === null ? null : 100 - manhaPercentual
    const manhaExibida = manhaPercentual === null ? null : Math.round(manhaPercentual * 10) / 10
    const tardeExibida = manhaExibida === null ? null : Math.round((100 - manhaExibida) * 10) / 10
    return {
      ...item,
      cx,
      area: { x: indice * groupW, y: PT, width: groupW, height: innerH },
      manhaPercentual,
      tardePercentual,
      manhaExibida,
      tardeExibida,
      manhaY: manhaPercentual === null ? null : baseY - manhaPercentual / 100 * innerH,
      tardeY: tardePercentual === null ? null : baseY - tardePercentual / 100 * innerH,
      mostrarLabel: props.granularidade === 'mensal' || indice % 4 === 0 || indice === dados.length - 1,
    }
  })
  return {
    width, baseY, itens,
    manhaPath: caminhoComLacunas(itens, 'manhaY'),
    tardePath: caminhoComLacunas(itens, 'tardeY'),
    grid: [25, 50, 75].map((percentual) => ({
      percentual,
      y: baseY - percentual / 100 * innerH,
    })),
  }
})

const detalheParcial = (item) => item.parcial ? ` · parcial até ${fmtData(item.data_corte)}` : ''
</script>

<template>
  <div v-if="chart" class="app-scrollbar overflow-x-auto pb-1">
    <svg
      :viewBox="`0 0 ${chart.width} ${H}`"
      class="h-[230px] w-full max-w-none"
      :style="granularidade === 'semanal' ? { minWidth: `${chart.width}px` } : undefined"
      preserveAspectRatio="none"
      role="img"
      aria-label="Participação percentual do faturamento por turno e período"
    >
      <line
        v-for="linha in chart.grid"
        :key="linha.percentual"
        x1="0"
        :x2="chart.width"
        :y1="linha.y"
        :y2="linha.y"
        :stroke="linha.percentual === 50 ? '#d1d5db' : '#f3f4f6'"
        :stroke-dasharray="linha.percentual === 50 ? '4 4' : undefined"
      />
      <line x1="0" :x2="chart.width" :y1="chart.baseY" :y2="chart.baseY" stroke="#e5e7eb" />
      <path v-if="chart.manhaPath" :d="chart.manhaPath" fill="none" stroke="#d97706" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      <path v-if="chart.tardePath" :d="chart.tardePath" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      <g v-for="item in chart.itens" :key="item.indice">
        <rect v-if="item.manhaY === null" v-bind="item.area" fill="transparent">
          <title>{{ item.label }}{{ detalheParcial(item) }} · Manhã - · Tarde -</title>
        </rect>
        <circle v-if="item.manhaY !== null" :cx="item.cx" :cy="item.manhaY" r="3.5" :fill="item.parcial ? 'white' : '#d97706'" stroke="#d97706" stroke-width="2">
          <title>{{ item.label }}{{ detalheParcial(item) }} · Manhã {{ fmtPercentual(item.manhaExibida) }}%</title>
        </circle>
        <circle v-if="item.tardeY !== null" :cx="item.cx" :cy="item.tardeY" r="3.5" :fill="item.parcial ? 'white' : '#2563eb'" stroke="#2563eb" stroke-width="2">
          <title>{{ item.label }}{{ detalheParcial(item) }} · Tarde {{ fmtPercentual(item.tardeExibida) }}%</title>
        </circle>
        <text v-if="item.mostrarLabel" :x="item.cx" :y="H - 7" text-anchor="middle" font-size="8" fill="#9ca3af">
          {{ item.label }}{{ item.parcial ? '*' : '' }}
        </text>
      </g>
    </svg>
  </div>
  <p v-else class="py-16 text-center text-xs text-gray-400">Sem dados para o período.</p>
</template>
