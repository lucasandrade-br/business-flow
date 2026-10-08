<script setup>
import { computed, ref, watch } from 'vue'
import { Search } from 'lucide-vue-next'
import BaseModal from '@/components/ui/BaseModal.vue'
import { despesasApi, enviarJson } from '@/services/despesasApi.js'

const props = defineProps({ modelValue: Boolean, folha: { type: Object, default: null }, familia: { type: Object, default: null } })
const emit = defineEmits(['update:modelValue', 'salvo'])
const busca = ref(''), pagina = ref(1), somenteVinculados = ref(false)
const tipos = ref([]), total = ref(0), vinculados = ref([])
const alteracoes = ref({}), carregando = ref(false), salvando = ref(false), revisando = ref(false), erro = ref('')
let requisicao = 0
let temporizador
const mudancas = computed(() => Object.entries(alteracoes.value).map(([id, item]) => ({ id: Number(id), ...item })))
const inclusoes = computed(() => mudancas.value.filter(item => item.selecionado))
const remocoes = computed(() => mudancas.value.filter(item => !item.selecionado))
const transferencias = computed(() => inclusoes.value.filter(item => item.original != null))
const todosPagina = computed(() => tipos.value.length > 0 && tipos.value.every(estaSelecionado))

watch(() => props.modelValue, async aberto => {
  if (!aberto) { requisicao++; clearTimeout(temporizador); return }
  busca.value = ''; pagina.value = 1; somenteVinculados.value = false
  tipos.value = []; alteracoes.value = {}; revisando.value = false; erro.value = ''
  try {
    const resposta = await despesasApi(`categorias/${props.folha.id}/vinculos/`)
    if (props.modelValue) { vinculados.value = resposta.vinculados_ids; await carregar() }
  } catch (e) { erro.value = e.message }
})
async function carregar() {
  const atual = ++requisicao
  carregando.value = true; erro.value = ''
  try {
    const parametros = new URLSearchParams({ page: pagina.value, busca: busca.value })
    if (somenteVinculados.value) parametros.set('folha_id', props.folha.id)
    const resposta = await despesasApi(`tipos/?${parametros}`)
    if (atual === requisicao) { tipos.value = resposta.results || []; total.value = resposta.count || 0 }
  } catch (e) { if (atual === requisicao) erro.value = e.message }
  finally { if (atual === requisicao) carregando.value = false }
}
function pesquisar() { clearTimeout(temporizador); pagina.value = 1; temporizador = setTimeout(carregar, 300) }
function filtrarVinculados() { pagina.value = 1; carregar() }
function folhaOriginal(tipo) { return tipo.vinculos.find(v => v.familia_id === props.familia.id)?.folha_id ?? null }
function estaSelecionado(tipo) { return alteracoes.value[tipo.id]?.selecionado ?? vinculados.value.includes(tipo.id) }
function marcar(tipo, selecionado) {
  const original = folhaOriginal(tipo)
  const eraVinculado = original === props.folha.id
  const novas = { ...alteracoes.value }
  if (selecionado === eraVinculado) delete novas[tipo.id]
  else novas[tipo.id] = { nome: tipo.nome, original, selecionado }
  alteracoes.value = novas
  revisando.value = false
}
function marcarPagina(selecionado) { tipos.value.forEach(tipo => marcar(tipo, selecionado)) }
async function aplicar() {
  salvando.value = true; erro.value = ''
  try {
    const esperados = Object.fromEntries(mudancas.value.map(item => [item.id, item.original]))
    const resultado = await enviarJson(`categorias/${props.folha.id}/vinculos/`, 'POST', {
      adicionar_ids: inclusoes.value.map(item => item.id), remover_ids: remocoes.value.map(item => item.id), esperados,
    })
    emit('update:modelValue', false)
    emit('salvo', resultado)
  } catch (e) { erro.value = e.message } finally { salvando.value = false }
}
</script>

<template>
  <BaseModal :model-value="modelValue" title="Gerenciar tipos da categoria" :description="folha?.caminho?.split('\x1f').join(' › ') || ''" @update:model-value="emit('update:modelValue', $event)">
    <div class="space-y-4">
      <p class="text-xs text-gray-600">Selecione tipos em quantas páginas precisar. A revisão confirma todas as alterações de uma vez.</p>
      <div class="flex flex-wrap items-center gap-2">
        <label class="flex min-w-[14rem] flex-1 items-center gap-2 rounded-md border border-gray-200 px-3 py-2"><Search class="h-4 w-4 text-gray-400" /><input v-model="busca" class="w-full bg-transparent text-sm outline-none" placeholder="Buscar tipos de despesa" aria-label="Buscar tipos de despesa" @input="pesquisar" /></label>
        <label class="flex items-center gap-2 text-xs text-gray-700"><input v-model="somenteVinculados" type="checkbox" @change="filtrarVinculados" /> Só vinculados</label>
      </div>
      <div class="flex items-center justify-between text-xs text-gray-600"><span>{{ total }} tipos encontrados · {{ vinculados.length }} vinculados nesta folha</span><span>{{ mudancas.length }} {{ mudancas.length === 1 ? 'alteração' : 'alterações' }}</span></div>
      <div class="rounded-md border border-gray-200">
        <label class="flex items-center gap-2 border-b bg-gray-50 px-3 py-2 text-xs font-medium"><input type="checkbox" :checked="todosPagina" :disabled="!tipos.length" @change="marcarPagina($event.target.checked)" /> Selecionar esta página</label>
        <div class="max-h-64 overflow-y-auto">
          <p v-if="carregando" class="px-3 py-4 text-xs text-gray-500">Carregando tipos…</p>
          <p v-else-if="!tipos.length" class="px-3 py-4 text-xs text-gray-500">Nenhum tipo encontrado.</p>
          <label v-for="tipo in tipos" :key="tipo.id" class="flex cursor-pointer items-center gap-3 border-b border-gray-100 px-3 py-2 text-xs hover:bg-gray-50">
            <input type="checkbox" :checked="estaSelecionado(tipo)" @change="marcar(tipo, $event.target.checked)" />
            <span class="flex-1 font-medium text-[#373435]">{{ tipo.nome }}</span>
            <span v-if="!tipo.ativo" class="text-gray-400">Inativo</span>
            <span v-if="folhaOriginal(tipo) && folhaOriginal(tipo) !== folha.id" class="text-amber-700">Vinculado a outra folha</span>
          </label>
        </div>
      </div>
      <div class="flex items-center justify-between text-xs"><button type="button" class="rounded border px-3 py-1.5 disabled:opacity-40" :disabled="pagina === 1 || carregando" @click="pagina--; carregar()">Anterior</button><span>Página {{ pagina }} de {{ Math.max(1, Math.ceil(total / 100)) }}</span><button type="button" class="rounded border px-3 py-1.5 disabled:opacity-40" :disabled="pagina * 100 >= total || carregando" @click="pagina++; carregar()">Próxima</button></div>
      <section v-if="revisando" class="space-y-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900" aria-label="Resumo das alterações">
        <p class="font-semibold">Revisar alterações</p>
        <p>{{ inclusoes.length - transferencias.length }} novos vínculos · {{ transferencias.length }} transferências · {{ remocoes.length }} remoções</p>
        <p v-if="transferencias.length">Transferir tipos muda a classificação de todo o histórico na família.</p>
        <ul class="max-h-28 list-disc overflow-y-auto pl-4"><li v-for="item in mudancas" :key="item.id">{{ item.nome }} — {{ item.selecionado ? (item.original ? 'transferir para esta folha' : 'vincular') : 'remover' }}</li></ul>
      </section>
      <p v-if="erro" role="alert" class="text-xs text-red-700">{{ erro }}</p>
    </div>
    <template #footer>
      <button type="button" class="rounded-md border px-3 py-2 text-xs" :disabled="salvando" @click="emit('update:modelValue', false)">Cancelar</button>
      <button v-if="!revisando" type="button" class="rounded-md bg-[#373435] px-3 py-2 text-xs text-white disabled:opacity-50" :disabled="!mudancas.length || carregando" @click="revisando = true">Revisar {{ mudancas.length }} {{ mudancas.length === 1 ? 'alteração' : 'alterações' }}</button>
      <button v-else type="button" class="rounded-md bg-[#373435] px-3 py-2 text-xs text-white disabled:opacity-50" :disabled="salvando || !mudancas.length" @click="aplicar">{{ salvando ? 'Aplicando…' : 'Confirmar alterações' }}</button>
    </template>
  </BaseModal>
</template>
