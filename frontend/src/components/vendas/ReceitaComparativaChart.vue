<script setup>
import { computed } from 'vue'

const props = defineProps({
  series: { type: Array, default: () => [] },
  granularidade: { type: String, default: 'mensal' },
  anoAtual: { type: String, default: '' },
  anoAnterior: { type: String, default: '' },
})

const H = 280
const PT = 14
const PB = 30

const fmtMoney = (valor) => Number(valor || 0).toLocaleString('pt-BR', {
  style: 'currency', currency: 'BRL', maximumFractionDigits: 0,
})

const fmtData = (valor) => {
  if (!valor) return ''
  const [, mes, dia] = valor.split('-')
  return `${dia}/${mes}`
}

const chart = computed(() => {
  const dados = props.series ?? []
  if (!dados.length) return null
  const width = Math.max(760, dados.length * (props.granularidade === 'semanal' ? 32 : 60))
  const innerH = H - PT - PB
  const max = Math.max(1, ...dados.flatMap((item) => [
    Number(item.receita_atual || 0),
    Number(item.receita_anterior_equivalente || 0),
  ])) * 1.08
  const groupW = width / dados.length
  const barW = Math.max(10, Math.min(36, groupW * 0.58))
  const baseY = PT + innerH
  const altura = (valor) => Math.max(0, Number(valor || 0) / max * innerH)
  const bars = dados.map((item, indice) => {
    const cx = indice * groupW + groupW / 2
    const atualH = altura(item.receita_atual)
    const anteriorH = altura(item.receita_anterior_equivalente)
    return {
      ...item,
      cx,
      mostrarLabel: props.granularidade === 'mensal' || indice % 4 === 0 || indice === dados.length - 1,
      atual: { x: cx - barW / 2, y: baseY - atualH, height: atualH, width: barW },
      anterior: { x: cx - barW / 2, y: baseY - anteriorH, height: anteriorH, width: barW },
    }
  })
  return {
    width,
    baseY,
    bars,
    gridY: [1, 2, 3, 4].map((indice) => PT + indice / 4 * innerH),
  }
})

function tooltip(item, valor, ano) {
  const parcial = item.parcial ? ` · parcial até ${fmtData(item.data_corte)}` : ''
  return `${item.label}${parcial}\n${ano}: ${fmtMoney(valor)}`
}
</script>

<template>
  <div v-if="chart" class="app-scrollbar overflow-x-auto pb-1">
    <svg
      :viewBox="`0 0 ${chart.width} ${H}`"
      class="h-[280px] w-full max-w-none"
      :style="granularidade === 'semanal' ? { minWidth: `${chart.width}px` } : undefined"
      preserveAspectRatio="none"
      role="img"
      aria-label="Comparativo de faturamento por período"
    >
      <line v-for="y in chart.gridY" :key="y" x1="0" :x2="chart.width" :y1="y" :y2="y" stroke="#f3f4f6" />
      <line x1="0" :x2="chart.width" :y1="chart.baseY" :y2="chart.baseY" stroke="#e5e7eb" />
      <g v-for="bar in chart.bars" :key="bar.indice">
        <!-- Ano anterior primeiro: a barra cinza permanece atrás da barra atual. -->
        <rect v-if="bar.anterior.height" v-bind="bar.anterior" fill="#9ca3af" fill-opacity="0.48" rx="2">
          <title>{{ tooltip(bar, bar.receita_anterior_equivalente, anoAnterior) }}</title>
        </rect>
        <rect
          v-if="bar.atual.height"
          v-bind="bar.atual"
          fill="#2f6f4f"
          :fill-opacity="bar.parcial ? 0.45 : 1"
          :stroke="bar.parcial ? '#2f6f4f' : 'none'"
          :stroke-dasharray="bar.parcial ? '3 2' : undefined"
          rx="2"
        >
          <title>{{ tooltip(bar, bar.receita_atual, anoAtual) }}</title>
        </rect>
        <text v-if="bar.mostrarLabel" :x="bar.cx" :y="H - 7" text-anchor="middle" font-size="8" fill="#9ca3af">
          {{ bar.label }}{{ bar.parcial ? '*' : '' }}
        </text>
      </g>
    </svg>
  </div>
  <p v-else class="py-16 text-center text-xs text-gray-400">Sem dados para o período.</p>
</template>
