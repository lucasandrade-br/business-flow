<script setup>
import { computed } from 'vue'

const props = defineProps({
  series: { type: Array, default: () => [] },
  granularidade: { type: String, default: 'mensal' },
})

const H = 230
const PT = 22
const PB = 30
const BADGE_H = 16
const BADGE_GAP = 7

const fmtNumero = (valor) => Number(valor || 0).toLocaleString('pt-BR')
const fmtMoney = (valor) => Number(valor || 0).toLocaleString('pt-BR', {
  style: 'currency', currency: 'BRL', minimumFractionDigits: 2, maximumFractionDigits: 2,
})
const fmtTicket = (valor) => Number(valor).toLocaleString('pt-BR', {
  minimumFractionDigits: 2, maximumFractionDigits: 2,
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

const chart = computed(() => {
  const dados = props.series ?? []
  if (!dados.length) return null
  const width = Math.max(760, dados.length * (props.granularidade === 'semanal' ? 30 : 58))
  const innerH = H - PT - PB
  const baseY = PT + innerH
  const maxVolume = Math.max(1, ...dados.map((item) => Number(item.volume_atual || 0))) * 1.1
  const tickets = dados.map((item) => Number(item.ticket_medio_atual)).filter(Number.isFinite)
  const maxTicket = Math.max(1, ...tickets) * 1.1
  const groupW = width / dados.length
  const barW = Math.max(7, Math.min(24, groupW * 0.45))
  const itens = dados.map((item, indice) => {
    const cx = indice * groupW + groupW / 2
    const volumeH = Number(item.volume_atual || 0) / maxVolume * innerH
    const ticket = item.ticket_medio_atual === null ? null : Number(item.ticket_medio_atual)
    const ticketY = ticket === null ? null : baseY - ticket / maxTicket * innerH
    const badgeTexto = ticket === null ? '' : fmtTicket(ticket)
    const badgeW = Math.max(34, badgeTexto.length * 5.2 + 10)
    const badgeX = Math.max(2, Math.min(width - badgeW - 2, cx - badgeW / 2))
    return {
      ...item,
      cx,
      bar: { x: cx - barW / 2, y: baseY - volumeH, height: volumeH, width: barW },
      ticketY,
      badge: ticketY === null ? null : {
        x: badgeX,
        y: Math.max(2, ticketY - BADGE_H - BADGE_GAP),
        width: badgeW,
        height: BADGE_H,
        texto: badgeTexto,
      },
      mostrarBadge: ticketY !== null && (
        props.granularidade === 'mensal' || indice % 2 === 0 || indice === dados.length - 1
      ),
      mostrarLabel: props.granularidade === 'mensal' || indice % 4 === 0 || indice === dados.length - 1,
    }
  })
  const segmentos = []
  let segmento = []
  for (const item of itens) {
    if (item.ticketY === null) {
      if (segmento.length) segmentos.push(segmento)
      segmento = []
      continue
    }
    segmento.push({ x: item.cx, y: item.ticketY })
  }
  if (segmento.length) segmentos.push(segmento)
  const path = segmentos.map(caminhoSuave).join(' ')
  return {
    width, baseY, itens, path,
    gridY: [1, 2, 3, 4].map((indice) => PT + indice / 4 * innerH),
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
      aria-label="Volume de vendas e ticket médio por período"
    >
      <line v-for="y in chart.gridY" :key="y" x1="0" :x2="chart.width" :y1="y" :y2="y" stroke="#f3f4f6" />
      <line x1="0" :x2="chart.width" :y1="chart.baseY" :y2="chart.baseY" stroke="#e5e7eb" />
      <path v-if="chart.path" :d="chart.path" fill="none" stroke="#2f6f4f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      <g v-for="item in chart.itens" :key="item.indice">
        <rect
          v-if="item.bar.height"
          v-bind="item.bar"
          fill="#9ca3af"
          :fill-opacity="item.parcial ? 0.35 : 0.7"
          :stroke="item.parcial ? '#6b7280' : 'none'"
          :stroke-dasharray="item.parcial ? '3 2' : undefined"
          rx="2"
        >
          <title>{{ item.label }}{{ detalheParcial(item) }} · {{ fmtNumero(item.volume_atual) }} documentos</title>
        </rect>
        <circle
          v-if="item.ticketY !== null"
          :cx="item.cx"
          :cy="item.ticketY"
          r="3.5"
          :fill="item.parcial ? 'white' : '#2f6f4f'"
          stroke="#2f6f4f"
          stroke-width="2"
        >
          <title>{{ item.label }}{{ detalheParcial(item) }} · Ticket médio {{ fmtMoney(item.ticket_medio_atual) }}</title>
        </circle>
        <g v-if="item.mostrarBadge && item.badge" aria-hidden="true">
          <rect
            :x="item.badge.x"
            :y="item.badge.y"
            :width="item.badge.width"
            :height="item.badge.height"
            rx="4"
            fill="white"
            fill-opacity="0.94"
            stroke="#d1d5db"
            stroke-width="0.75"
          />
          <text
            :x="item.badge.x + item.badge.width / 2"
            :y="item.badge.y + 11"
            text-anchor="middle"
            font-size="8"
            font-weight="600"
            fill="#2f6f4f"
          >{{ item.badge.texto }}</text>
        </g>
        <text v-if="item.mostrarLabel" :x="item.cx" :y="H - 7" text-anchor="middle" font-size="8" fill="#9ca3af">
          {{ item.label }}{{ item.parcial ? '*' : '' }}
        </text>
      </g>
    </svg>
  </div>
  <p v-else class="py-16 text-center text-xs text-gray-400">Sem dados para o período.</p>
</template>
