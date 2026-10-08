<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ChevronDown, ChevronRight, FolderPlus, Link2, Pencil, Plus, Search } from 'lucide-vue-next'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import ModalCategoriasLote from './ModalCategoriasLote.vue'
import ModalVinculosLote from './ModalVinculosLote.vue'
import { despesasApi, enviarJson } from '@/services/despesasApi.js'

const aba = ref('tipos'), categorias = ref([]), tipos = ref([]), total = ref(0), pagina = ref(1)
const busca = ref(''), somenteAtivos = ref(false), familia = ref(''), expandidos = ref(new Set())
const carregando = ref(false), salvando = ref(false), erro = ref(''), aviso = ref('')
const modalTipo = ref(false), modalNo = ref(false), modalVinculo = ref(false)
const modalLote = ref(false), modalVinculosLote = ref(false), noLote = ref(null)
const tipoAtual = ref(null), noAtual = ref(null)
const formTipo = reactive({ nome: '', ativo: true })
const formNo = reactive({ nome: '' })
const formVinculo = reactive({ familia_id: '', folha_id: '' })
const colunas = [
  { key: 'nome', label: 'Tipo de Despesa' },
  { key: 'vinculos', label: 'Classificação atual' },
  { key: 'ativo', label: 'Situação' },
]
const familias = computed(() => categorias.value.filter(c => c.pai == null))
const mapaNos = computed(() => new Map(categorias.value.map(c => [c.id, c])))
const nosFamilia = computed(() => {
  const raiz = mapaNos.value.get(Number(familia.value))
  if (!raiz) return []
  return categorias.value.filter(c => c.id === raiz.id || c.caminho.startsWith(`${raiz.caminho}\x1f`))
})
const nosVisiveis = computed(() => nosFamilia.value.filter(no => {
  let pai = no.pai
  while (pai) { if (!expandidos.value.has(pai)) return false; pai = mapaNos.value.get(pai)?.pai }
  return true
}))
const folhasVinculo = computed(() => {
  const raiz = mapaNos.value.get(Number(formVinculo.familia_id))
  if (!raiz) return []
  return categorias.value.filter(c => c.caminho.startsWith(`${raiz.caminho}\x1f`) && !categorias.value.some(f => f.pai === c.id))
})
function caminho(no) { return no?.caminho?.split('\x1f').slice(1).join(' › ') || '' }
function temFilhos(no) { return categorias.value.some(c => c.pai === no.id) }
function alternar(no) { const novo = new Set(expandidos.value); novo.has(no.id) ? novo.delete(no.id) : novo.add(no.id); expandidos.value = novo }
function classificar(tipo) { return tipo.vinculos.length ? tipo.vinculos.map(v => `${mapaNos.value.get(v.familia_id)?.nome || 'Família'} › ${caminho(mapaNos.value.get(v.folha_id)) || v.folha}`).join(' · ') : 'Sem vínculo' }
async function carregarCategorias() {
  categorias.value = await despesasApi('categorias/')
  if (!familias.value.some(f => String(f.id) === familia.value)) familia.value = String(familias.value.find(f => f.nome.toUpperCase() === 'DESPESAS')?.id || familias.value[0]?.id || '')
  expandidos.value = new Set([Number(familia.value), ...[...expandidos.value].filter(id => categorias.value.some(no => no.id === id))])
}
async function carregarTipos() {
  carregando.value = true; erro.value = ''
  try { const r = await despesasApi(`tipos/?${new URLSearchParams({ page: pagina.value, busca: busca.value, ...(somenteAtivos.value ? { ativo: '1' } : {}) })}`); tipos.value = r.results || []; total.value = r.count || 0 }
  catch (e) { erro.value = e.message } finally { carregando.value = false }
}
function abrirTipo(tipo = null) { tipoAtual.value = tipo; Object.assign(formTipo, { nome: tipo?.nome || '', ativo: tipo?.ativo ?? true }); modalTipo.value = true; erro.value = '' }
async function salvarTipo() {
  salvando.value = true; erro.value = ''
  try { await enviarJson(tipoAtual.value ? `tipos/${tipoAtual.value.id}/` : 'tipos/', tipoAtual.value ? 'PATCH' : 'POST', formTipo); modalTipo.value = false; aviso.value = 'Tipo salvo.'; await carregarTipos() }
  catch (e) { erro.value = e.message } finally { salvando.value = false }
}
function abrirNo() { noAtual.value = null; formNo.nome = ''; modalNo.value = true; erro.value = '' }
function abrirLote(no) { noLote.value = no; modalLote.value = true; erro.value = '' }
function abrirVinculosLote(no) { noLote.value = no; modalVinculosLote.value = true; erro.value = '' }
function aposLoteCategorias(resultado) {
  aviso.value = `${resultado.total} categorias criadas.`
  carregarCategorias().then(() => {
    const abertos = new Set(expandidos.value)
    let atual = noLote.value
    while (atual) { abertos.add(atual.id); atual = mapaNos.value.get(atual.pai) }
    expandidos.value = abertos
  }).catch(e => { erro.value = e.message })
}
function aposLoteVinculos(resultado) { aviso.value = `${resultado.adicionados} vínculos criados, ${resultado.transferidos} transferidos e ${resultado.removidos} removidos. O histórico usa a classificação atual.`; Promise.all([carregarCategorias(), carregarTipos()]).catch(e => { erro.value = e.message }) }
function raizDe(no) { let atual = no; while (atual?.pai) atual = mapaNos.value.get(atual.pai); return atual }
function editarNo(no) { noAtual.value = no; formNo.nome = no.nome; modalNo.value = true; erro.value = '' }
async function salvarNo() {
  salvando.value = true; erro.value = ''
  try { await enviarJson(noAtual.value ? `categorias/${noAtual.value.id}/` : 'categorias/', noAtual.value ? 'PATCH' : 'POST', noAtual.value ? { nome: formNo.nome } : { nome: formNo.nome, pai: null }); modalNo.value = false; aviso.value = noAtual.value ? 'Categoria atualizada.' : 'Família criada.'; await carregarCategorias() }
  catch (e) { erro.value = e.message } finally { salvando.value = false }
}
function abrirVinculo(tipo) { tipoAtual.value = tipo; formVinculo.familia_id = String(familias.value.find(f => f.nome.toUpperCase() === 'DESPESAS')?.id || familias.value[0]?.id || ''); formVinculo.folha_id = String(tipo.vinculos.find(v => v.familia_id === Number(formVinculo.familia_id))?.folha_id || ''); modalVinculo.value = true; erro.value = '' }
watch(() => formVinculo.familia_id, () => { formVinculo.folha_id = String(tipoAtual.value?.vinculos.find(v => v.familia_id === Number(formVinculo.familia_id))?.folha_id || '') })
async function salvarVinculo() {
  salvando.value = true; erro.value = ''
  try { await enviarJson(`tipos/${tipoAtual.value.id}/vinculo/`, 'PUT', { familia_id: Number(formVinculo.familia_id), folha_id: Number(formVinculo.folha_id) }); modalVinculo.value = false; aviso.value = 'Vínculo atualizado. O histórico usa a nova classificação.'; await carregarTipos() }
  catch (e) { erro.value = e.message } finally { salvando.value = false }
}
async function removerVinculo() {
  salvando.value = true; erro.value = ''
  try { await despesasApi(`tipos/${tipoAtual.value.id}/vinculo/?familia_id=${formVinculo.familia_id}`, { method: 'DELETE' }); modalVinculo.value = false; aviso.value = 'Vínculo removido.'; await carregarTipos() }
  catch (e) { erro.value = e.message } finally { salvando.value = false }
}
onMounted(async () => { try { await carregarCategorias(); await carregarTipos() } catch (e) { erro.value = e.message } })
</script>

<template>
  <div class="mx-auto max-w-[1500px] space-y-5">
    <header class="flex flex-wrap items-end justify-between gap-3"><div><h1 class="text-xl font-semibold text-[#373435]">Plano e tipos de despesas</h1><p class="mt-1 text-xs text-gray-500">Cadastre tipos e organize os vínculos por família.</p></div><button type="button" class="inline-flex items-center gap-2 rounded-md bg-[#373435] px-3 py-2 text-xs font-medium text-white hover:bg-[#4b4948]" @click="aba === 'tipos' ? abrirTipo() : abrirNo()"><Plus class="h-4 w-4" />{{ aba === 'tipos' ? 'Novo tipo' : 'Nova família' }}</button></header>
    <p v-if="erro && !modalTipo && !modalNo && !modalVinculo && !modalLote && !modalVinculosLote" role="alert" class="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-xs text-red-700">{{ erro }}</p><p v-if="aviso" role="status" class="rounded-md border border-green-200 bg-green-50 px-4 py-2 text-xs text-green-700">{{ aviso }}</p>
    <div class="flex gap-1 border-b border-gray-200 text-sm"><button v-for="item in [{ id:'tipos', nome:'Tipos de Despesa' }, { id:'plano', nome:'Plano de Contas' }]" :key="item.id" type="button" class="px-4 py-2" :class="aba === item.id ? 'border-b-2 border-[#373435] font-semibold text-[#373435]' : 'text-gray-500 hover:text-gray-800'" @click="aba = item.id">{{ item.nome }}</button></div>
    <BaseTable v-if="aba === 'tipos'" title="Tipos cadastrados" :subtitle="`${total} tipos nesta filial`" :columns="colunas" :rows="tipos" :count="total" :loading="carregando" :error="erro" :previous="pagina > 1 ? 'sim' : ''" :next="pagina * 100 < total ? 'sim' : ''" empty-text="Nenhum tipo encontrado." @previous="pagina--; carregarTipos()" @next="pagina++; carregarTipos()">
      <template #header-extra><div class="flex flex-wrap items-center gap-2"><label class="flex items-center gap-2 rounded-md border border-gray-200 px-2 py-1.5"><Search class="h-4 w-4 text-gray-400" /><input v-model="busca" class="w-48 bg-transparent text-xs outline-none" placeholder="Buscar tipo" aria-label="Buscar tipo" @keyup.enter="pagina = 1; carregarTipos()" /></label><button type="button" class="rounded-md border border-gray-200 px-3 py-2 text-xs hover:bg-gray-50" @click="pagina = 1; carregarTipos()">Buscar</button><label class="flex items-center gap-1 text-xs text-gray-600"><input v-model="somenteAtivos" type="checkbox" @change="pagina = 1; carregarTipos()" /> Apenas ativos</label></div></template>
      <template #cell-nome="{ row }"><span class="font-medium text-[#373435]">{{ row.nome }}</span></template>
      <template #cell-vinculos="{ row }"><span class="text-xs text-gray-600">{{ classificar(row) }}</span></template>
      <template #cell-ativo="{ row }"><span class="rounded-full px-2 py-1 text-[10px] font-semibold" :class="row.ativo ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'">{{ row.ativo ? 'Ativo' : 'Inativo' }}</span></template>
      <template #actions="{ row }"><div class="inline-flex items-center justify-end gap-2"><button type="button" class="rounded-md border border-gray-200 bg-white p-1.5 text-gray-600 transition-colors hover:bg-gray-50 hover:text-[#373435] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2f6f4f] focus-visible:ring-offset-1" :aria-label="`Editar tipo ${row.nome}`" :title="`Editar tipo ${row.nome}`" @click="abrirTipo(row)"><Pencil class="h-3.5 w-3.5" aria-hidden="true" /></button><button type="button" class="rounded-md border border-gray-200 bg-white p-1.5 text-gray-600 transition-colors hover:bg-gray-50 hover:text-[#2f6f4f] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2f6f4f] focus-visible:ring-offset-1" :aria-label="`Gerenciar vínculos do tipo ${row.nome}`" :title="`Gerenciar vínculos do tipo ${row.nome}`" @click="abrirVinculo(row)"><Link2 class="h-3.5 w-3.5" aria-hidden="true" /></button></div></template>
    </BaseTable>
    <article v-else class="overflow-hidden rounded-md border border-gray-200 bg-white">
      <header class="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
        <div><h2 class="text-sm font-semibold">Famílias e categorias</h2><p class="mt-1 text-xs text-gray-500">Expanda a árvore. Cadastre filhas em lote e gerencie os tipos diretamente em cada folha.</p></div>
        <select v-model="familia" class="rounded-md border border-gray-200 px-3 py-2 text-xs" aria-label="Família" @change="expandidos = new Set([Number(familia)])"><option v-for="f in familias" :key="f.id" :value="String(f.id)">{{ f.nome }}</option></select>
      </header>
      <div v-if="!nosFamilia.length" class="p-6 text-sm text-gray-500">Nenhuma família cadastrada.</div>
      <div v-else class="max-h-[65vh] overflow-auto">
        <table class="w-full text-sm">
          <thead class="sticky top-0 bg-gray-50 text-left text-[10px] uppercase tracking-wide text-gray-500"><tr><th class="px-4 py-3">Categoria</th><th class="px-4 py-3">Nível</th><th class="px-4 py-3 text-right">Ações</th></tr></thead>
          <tbody>
            <tr v-for="no in nosVisiveis" :key="no.id" class="border-t border-gray-100 hover:bg-gray-50">
              <td class="px-4 py-2"><div class="flex items-center gap-1" :style="{ paddingLeft: `${no.nivel * 18}px` }"><button v-if="temFilhos(no)" type="button" class="rounded p-1 hover:bg-gray-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2f6f4f]" :aria-label="`${expandidos.has(no.id) ? 'Recolher' : 'Expandir'} ${no.nome}`" @click="alternar(no)"><ChevronDown v-if="expandidos.has(no.id)" class="h-3.5 w-3.5" /><ChevronRight v-else class="h-3.5 w-3.5" /></button><span v-else class="w-5" /><span :class="no.nivel === 0 ? 'font-semibold' : ''">{{ no.nome }}</span></div></td>
              <td class="px-4 py-2 text-xs text-gray-500">{{ no.nivel === 0 ? 'Família' : temFilhos(no) ? 'Grupo' : 'Folha' }}<span v-if="no.tipos_vinculados_count" class="ml-2 text-[#2f6f4f]">{{ no.tipos_vinculados_count }} tipos</span></td>
              <td class="px-4 py-2 text-right">
                <div class="inline-flex items-center justify-end gap-2">
                  <button type="button" class="rounded-md border border-gray-200 bg-white p-1.5 text-gray-600 transition-colors hover:bg-gray-50 hover:text-[#373435] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2f6f4f] focus-visible:ring-offset-1" :aria-label="`Editar categoria ${no.nome}`" :title="`Editar categoria ${no.nome}`" @click="editarNo(no)"><Pencil class="h-3.5 w-3.5" aria-hidden="true" /></button>
                  <button v-if="!no.tipos_vinculados_count" type="button" class="rounded-md border border-gray-200 bg-white p-1.5 text-gray-600 transition-colors hover:bg-gray-50 hover:text-[#2f6f4f] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2f6f4f] focus-visible:ring-offset-1" :aria-label="`Cadastrar filhas de ${no.nome}`" :title="`Cadastrar filhas de ${no.nome}`" @click="abrirLote(no)"><FolderPlus class="h-3.5 w-3.5" aria-hidden="true" /></button>
                  <button v-if="no.nivel > 0 && !temFilhos(no)" type="button" class="rounded-md border border-gray-200 bg-white p-1.5 text-gray-600 transition-colors hover:bg-gray-50 hover:text-[#2f6f4f] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2f6f4f] focus-visible:ring-offset-1" :aria-label="`Gerenciar tipos de ${no.nome}`" :title="`Gerenciar tipos de ${no.nome}`" @click="abrirVinculosLote(no)"><Link2 class="h-3.5 w-3.5" aria-hidden="true" /></button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>
    <ModalCategoriasLote v-model="modalLote" :pai="noLote" @salvo="aposLoteCategorias" />
    <ModalVinculosLote v-model="modalVinculosLote" :folha="noLote" :familia="raizDe(noLote)" @salvo="aposLoteVinculos" />
    <BaseModal v-model="modalTipo" :title="tipoAtual ? 'Editar Tipo de Despesa' : 'Novo Tipo de Despesa'" description="O tipo identifica a despesa nos lançamentos e pode participar de várias famílias."><form id="tipo-despesa-form" class="space-y-4" @submit.prevent="salvarTipo"><label class="block text-xs font-medium text-gray-600">Nome do tipo<input v-model="formTipo.nome" required maxlength="220" class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label><label class="flex items-center gap-2 text-xs text-gray-600"><input v-model="formTipo.ativo" type="checkbox" /> Tipo ativo</label><p v-if="erro" role="alert" class="text-xs text-red-600">{{ erro }}</p></form><template #footer><button type="button" class="rounded-md border px-3 py-2 text-xs" @click="modalTipo = false">Cancelar</button><button form="tipo-despesa-form" :disabled="salvando" class="rounded-md bg-[#373435] px-3 py-2 text-xs text-white disabled:opacity-50">Salvar tipo</button></template></BaseModal>
    <BaseModal v-model="modalNo" :title="noAtual ? 'Editar categoria' : 'Nova família'" :description="noAtual ? 'A alteração do nome atualiza o caminho de todas as categorias filhas.' : 'Crie uma família para classificar os tipos em outra estrutura.'"><form id="categoria-despesa-form" class="space-y-3" @submit.prevent="salvarNo"><label class="block text-xs font-medium text-gray-600">Nome<input v-model="formNo.nome" required maxlength="180" class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label><p v-if="erro" role="alert" class="text-xs text-red-600">{{ erro }}</p></form><template #footer><button type="button" class="rounded-md border px-3 py-2 text-xs" @click="modalNo = false">Cancelar</button><button form="categoria-despesa-form" :disabled="salvando" class="rounded-md bg-[#373435] px-3 py-2 text-xs text-white disabled:opacity-50">{{ noAtual ? 'Salvar' : 'Criar' }}</button></template></BaseModal>
    <BaseModal v-model="modalVinculo" title="Classificar Tipo de Despesa" :description="tipoAtual?.nome || ''"><form id="vinculo-despesa-form" class="space-y-4" @submit.prevent="salvarVinculo"><label class="block text-xs font-medium text-gray-600">Família<select v-model="formVinculo.familia_id" required class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm"><option v-for="f in familias" :key="f.id" :value="String(f.id)">{{ f.nome }}</option></select></label><label class="block text-xs font-medium text-gray-600">Categoria folha<select v-model="formVinculo.folha_id" required class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm"><option value="">Selecione uma folha</option><option v-for="f in folhasVinculo" :key="f.id" :value="String(f.id)">{{ caminho(f) }}</option></select></label><p class="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">Alterar o vínculo também muda a classificação do histórico deste tipo.</p><p v-if="erro" role="alert" class="text-xs text-red-600">{{ erro }}</p></form><template #footer><button v-if="tipoAtual?.vinculos.some(v => v.familia_id === Number(formVinculo.familia_id))" type="button" class="mr-auto rounded-md border px-3 py-2 text-xs text-red-700" @click="removerVinculo">Remover vínculo</button><button type="button" class="rounded-md border px-3 py-2 text-xs" @click="modalVinculo = false">Cancelar</button><button form="vinculo-despesa-form" :disabled="salvando" class="rounded-md bg-[#373435] px-3 py-2 text-xs text-white disabled:opacity-50">Salvar vínculo</button></template></BaseModal>
  </div>
</template>
