<script setup>
import { Info } from 'lucide-vue-next'

defineProps({
  ultimaVenda: { type: String, default: null },
  atualizadoEm: { type: String, default: null },
})

function dataCurta(valor) {
  if (!valor) return '—'
  const [ano, mes, dia] = valor.split('-')
  return `${dia}/${mes}/${ano}`
}
</script>

<template>
  <details class="relative shrink-0 text-xs text-gray-600">
    <summary class="flex h-[34px] w-[34px] cursor-pointer list-none items-center justify-center rounded-md border border-gray-200 bg-white text-gray-500 hover:bg-gray-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#373435] [&::-webkit-details-marker]:hidden" aria-label="Detalhes da atualização" title="Detalhes da atualização">
      <Info class="h-4 w-4" aria-hidden="true" />
    </summary>
    <div class="absolute right-0 z-30 mt-1 w-64 rounded-lg border border-gray-200 bg-white p-3 shadow-lg">
      <p class="font-semibold text-gray-800">Atualização dos dados</p>
      <p class="mt-2">Última venda: {{ dataCurta(ultimaVenda) }}</p>
      <p>Snapshot: {{ atualizadoEm ? new Date(atualizadoEm).toLocaleString('pt-BR') : '—' }}</p>
    </div>
  </details>
</template>
