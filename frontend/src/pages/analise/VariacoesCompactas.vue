<script setup>
defineProps({
  media: { type: [String, Number], default: null },
  recente: { type: [String, Number], default: null },
  sigla: { type: String, default: '' },
  recenteNeutra: { type: Boolean, default: false },
  invertido: { type: Boolean, default: false },
})

function formatar(valor) {
  if (valor === null || valor === undefined) return '—'
  const numero = Number(valor)
  if (!Number.isFinite(numero)) return '—'
  return `${numero > 0 ? '+' : ''}${numero.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`
}

function cor(valor, invertido) {
  if (valor === null || valor === undefined) return 'text-gray-400'
  return (Number(valor) >= 0) !== invertido ? 'text-[#2f6f4f]' : 'text-[#a82631]'
}
</script>

<template>
  <div class="whitespace-nowrap text-right font-mono tabular-nums leading-4">
    <div class="text-[11px] font-bold" :class="cor(media, invertido)">Média · {{ formatar(media) }}<span v-if="sigla" class="ml-1 text-[9px] font-medium text-gray-500">{{ sigla }}</span></div>
    <div class="text-[10px] font-medium" :class="recenteNeutra ? 'text-gray-500' : cor(recente, invertido)">Recente · {{ formatar(recente) }}</div>
  </div>
</template>
