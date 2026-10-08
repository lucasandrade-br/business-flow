<script setup>
import { BookmarkCheck, BookmarkPlus } from 'lucide-vue-next'

defineProps({
  nome: { type: String, required: true },
  marcada: { type: Boolean, default: false },
  ocupada: { type: Boolean, default: false },
})
defineEmits(['toggle'])
</script>

<template>
  <button
    type="button"
    class="flex h-6 w-6 shrink-0 items-center justify-center rounded hover:bg-amber-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-600 disabled:opacity-50"
    :class="marcada ? 'text-amber-700' : 'text-gray-400 hover:text-amber-700'"
    :disabled="ocupada"
    :aria-pressed="marcada"
    :aria-label="`${marcada ? 'Remover da' : 'Colocar em'} quarentena: ${nome}`"
    :title="marcada ? 'Remover da quarentena' : 'Colocar em quarentena'"
    @click.stop="$emit('toggle')"
  >
    <BookmarkCheck v-if="marcada" class="h-3.5 w-3.5" aria-hidden="true" />
    <BookmarkPlus v-else class="h-3.5 w-3.5" aria-hidden="true" />
  </button>
</template>
