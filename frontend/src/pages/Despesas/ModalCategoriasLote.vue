<script setup>
import { nextTick, ref, watch } from 'vue'
import { Plus, Trash2 } from 'lucide-vue-next'
import BaseModal from '@/components/ui/BaseModal.vue'
import { enviarJson } from '@/services/despesasApi.js'

const props = defineProps({ modelValue: Boolean, pai: { type: Object, default: null } })
const emit = defineEmits(['update:modelValue', 'salvo'])
const linhas = ref([{ id: 1, nome: '' }])
const entradas = ref([])
const erro = ref('')
const salvando = ref(false)
let proximoId = 2

watch(() => props.modelValue, aberto => {
  if (aberto) { linhas.value = [{ id: 1, nome: '' }]; proximoId = 2; erro.value = '' }
})
async function adicionar() {
  linhas.value.push({ id: proximoId++, nome: '' })
  await nextTick()
  entradas.value[linhas.value.length - 1]?.focus()
}
function remover(indice) {
  if (linhas.value.length === 1) linhas.value[0].nome = ''
  else linhas.value.splice(indice, 1)
}
async function salvar() {
  const nomes = linhas.value.map(linha => linha.nome.trim()).filter(Boolean)
  if (!nomes.length) { erro.value = 'Informe ao menos uma categoria.'; return }
  salvando.value = true; erro.value = ''
  try {
    const resultado = await enviarJson('categorias/lote/', 'POST', { pai_id: props.pai.id, nomes })
    emit('update:modelValue', false)
    emit('salvo', resultado)
  } catch (e) { erro.value = e.message } finally { salvando.value = false }
}
</script>

<template>
  <BaseModal :model-value="modelValue" title="Cadastrar categorias em lote" :description="`Categoria mãe: ${pai?.nome || ''}`" @update:model-value="emit('update:modelValue', $event)">
    <form id="despesas-lote-categorias" class="space-y-4" @submit.prevent="salvar">
      <p class="text-xs text-gray-600">Digite uma categoria por linha. Enter abre a próxima linha. Todas serão criadas juntas.</p>
      <div class="max-h-80 space-y-2 overflow-auto">
        <div v-for="(linha, indice) in linhas" :key="linha.id" class="flex items-center gap-2">
          <label :for="`despesa-nova-${linha.id}`" class="sr-only">Categoria {{ indice + 1 }}</label>
          <input :id="`despesa-nova-${linha.id}`" :ref="el => { if (el) entradas[indice] = el }" v-model="linha.nome" maxlength="180" class="min-w-0 flex-1 rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-[#373435] focus:outline-none" :placeholder="`Categoria ${indice + 1}`" @keydown.enter.prevent="adicionar" />
          <button type="button" class="rounded-md border border-gray-200 p-2 text-red-700 hover:bg-red-50 focus-visible:outline focus-visible:outline-2" :aria-label="`Remover linha ${indice + 1}`" @click="remover(indice)"><Trash2 class="h-4 w-4" /></button>
        </div>
      </div>
      <button type="button" class="inline-flex items-center gap-1 rounded-md border border-gray-200 px-3 py-2 text-xs hover:bg-gray-50" @click="adicionar"><Plus class="h-4 w-4" /> Adicionar linha</button>
      <p v-if="erro" role="alert" class="text-xs text-red-700">{{ erro }}</p>
    </form>
    <template #footer>
      <button type="button" class="rounded-md border px-3 py-2 text-xs" :disabled="salvando" @click="emit('update:modelValue', false)">Cancelar</button>
      <button form="despesas-lote-categorias" class="rounded-md bg-[#373435] px-3 py-2 text-xs text-white disabled:opacity-50" :disabled="salvando">{{ salvando ? 'Salvando…' : 'Criar categorias' }}</button>
    </template>
  </BaseModal>
</template>
