<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { AlertCircle, Check, ChevronLeft, ChevronRight, FileUp, RefreshCw, Search, Trash2 } from 'lucide-vue-next'
import BaseModal from '@/components/ui/BaseModal.vue'
import { despesasApi, dinheiro, enviarJson } from '@/services/despesasApi.js'
import { filialAtiva } from '@/stores/filial.js'

const capturas = ref([])
const captura = ref(null)
const resumo = ref(null)
const linhas = ref([])
const totalLinhas = ref(0)
const pagina = ref(1)
const classificacao = ref('')
const busca = ref('')
const termo = ref('')
const arquivo = ref(null)
const processando = ref(false)
const carregando = ref(false)
const erro = ref('')
const aviso = ref('')
const modalLinha = ref(false)
const modalDescarte = ref(false)
const linhaAtual = ref(null)
const buscaTipo = ref('')
const tipos = ref([])
const conflitos = ref([])
const mostrarConflitos = ref(false)
const revisao = reactive({ tipo_id: '', emissao: '', vencimento: '', valor: '', pagamento_data: '', valor_pago: '', movimento_id: '', confirmar_novo: false })

const filtros = [
  { valor: '', nome: 'Todas' },
  { valor: 'EXISTENTE', nome: 'Já existentes' },
  { valor: 'NOVA', nome: 'Novas' },
  { valor: 'ALTERADA', nome: 'Alteradas' },
  { valor: 'AMBIGUA', nome: 'Ambíguas' },
  { valor: 'INVALIDA', nome: 'Inválidas' },
  { valor: 'SEM_CLASSIFICACAO', nome: 'A classificar' },
]
const nomes = { EXISTENTE: 'Já existente', NOVA: 'Nova', ALTERADA: 'Alterada', AMBIGUA: 'Ambígua', INVALIDA: 'Inválida', IGNORADA: 'Ignorada', SEM_CLASSIFICACAO: 'A classificar' }
const estilos = {
  EXISTENTE: 'bg-slate-100 text-slate-700', NOVA: 'bg-sky-50 text-sky-800', ALTERADA: 'bg-violet-50 text-violet-800',
  AMBIGUA: 'bg-amber-50 text-amber-800', INVALIDA: 'bg-red-50 text-red-700', IGNORADA: 'bg-gray-100 text-gray-500', SEM_CLASSIFICACAO: 'bg-gray-100 text-gray-600',
}
const podeConsolidar = computed(() => captura.value && resumo.value && !resumo.value.pendentes && !resumo.value.classificacoes?.AMBIGUA && !resumo.value.classificacoes?.INVALIDA && !resumo.value.classificacoes?.SEM_CLASSIFICACAO && !processando.value && !filialDivergente(captura.value))

function dataBR(valor) {
  if (!valor) return '—'
  const [ano, mes, dia] = valor.slice(0, 10).split('-')
  return `${dia}/${mes}/${ano}`
}
function filialDivergente(item) {
  const nome = String(item?.nome_arquivo || '').toUpperCase()
  return (nome.includes('CENTRO') && filialAtiva.value.id !== 'centro') || (nome.includes('HENRIQ') && filialAtiva.value.id !== 'henriques')
}
async function carregar() {
  carregando.value = true
  try {
    const [ativas, pendencias] = await Promise.all([despesasApi('lotes/'), despesasApi('conflitos/')])
    capturas.value = ativas
    conflitos.value = pendencias
    const id = captura.value?.id
    captura.value = ativas.find(item => item.id === id) || ativas[0] || null
    if (captura.value) await carregarResumoELinhas()
    else { resumo.value = null; linhas.value = []; totalLinhas.value = 0 }
  } finally { carregando.value = false }
}
async function carregarResumoELinhas() {
  if (!captura.value) return
  const id = captura.value.id
  const [novoResumo] = await Promise.all([despesasApi(`lotes/${id}/resumo/`), carregarLinhas()])
  if (captura.value?.id === id) resumo.value = novoResumo
}
async function carregarLinhas() {
  if (!captura.value) return
  const id = captura.value.id
  const parametros = new URLSearchParams({ page: String(pagina.value) })
  if (classificacao.value) parametros.set('classificacao', classificacao.value)
  if (termo.value) parametros.set('busca', termo.value)
  const resultado = await despesasApi(`lotes/${id}/linhas/?${parametros}`)
  if (captura.value?.id !== id) return
  linhas.value = resultado.results || []
  totalLinhas.value = resultado.count || 0
}
async function selecionar(item) {
  captura.value = item
  pagina.value = 1
  termo.value = ''
  busca.value = ''
  classificacao.value = ''
  try { await carregarResumoELinhas() } catch (e) { erro.value = e.message }
}
async function filtrar() {
  pagina.value = 1
  termo.value = busca.value.trim()
  try { await carregarLinhas() } catch (e) { erro.value = e.message }
}
async function alterarFiltro(valor) {
  classificacao.value = valor
  pagina.value = 1
  try { await carregarLinhas() } catch (e) { erro.value = e.message }
}
async function mudarPagina(nova) {
  pagina.value = nova
  try { await carregarLinhas() } catch (e) { erro.value = e.message }
}
async function enviar() {
  if (!arquivo.value || capturas.value.length) return
  processando.value = true; erro.value = ''; aviso.value = ''
  try {
    if (filialDivergente({ nome_arquivo: arquivo.value.name })) throw new Error('O nome do arquivo indica outra filial. Selecione a filial correta.')
    const corpo = new FormData()
    corpo.append('arquivo', arquivo.value)
    const nova = await despesasApi('lotes/', { method: 'POST', body: corpo })
    arquivo.value = null
    await carregar()
    await selecionar(capturas.value.find(item => item.id === nova.id) || nova)
    aviso.value = `Captura validada: ${nova.prontas} linhas prontas, ${nova.pendentes} pendentes. Nenhuma movimentação oficial foi gravada.`
  } catch (e) { erro.value = e.message } finally { processando.value = false }
}
async function revalidar() {
  if (!captura.value || filialDivergente(captura.value)) return
  processando.value = true; erro.value = ''
  try {
    await enviarJson(`lotes/${captura.value.id}/revalidar/`, 'POST', {})
    await carregar()
    aviso.value = 'Arquivo revalidado. Confira novamente as linhas e as decisões antes de consolidar.'
  } catch (e) { erro.value = e.message } finally { processando.value = false }
}
async function descartar() {
  if (!captura.value) return
  processando.value = true; erro.value = ''
  try {
    await despesasApi(`lotes/${captura.value.id}/`, { method: 'DELETE' })
    modalDescarte.value = false
    captura.value = null
    await carregar()
    aviso.value = 'Captura temporária descartada. As movimentações oficiais não foram alteradas.'
  } catch (e) { erro.value = e.message } finally { processando.value = false }
}
async function consolidar() {
  if (!podeConsolidar.value) return
  processando.value = true; erro.value = ''
  try {
    const resultado = await enviarJson(`lotes/${captura.value.id}/consolidar/`, 'POST', {})
    captura.value = null
    await carregar()
    aviso.value = resultado.ja_consolidado ? 'Esta captura já estava consolidada.' : `Consolidação concluída. ${resultado.conflitos || 0} conflitos registrados para revisão.`
  } catch (e) { erro.value = e.message } finally { processando.value = false }
}
async function carregarTipos() {
  try { const resposta = await despesasApi(`tipos/?busca=${encodeURIComponent(buscaTipo.value)}`); tipos.value = resposta.results || [] }
  catch (e) { erro.value = e.message }
}
function abrirLinha(linha) {
  linhaAtual.value = linha
  Object.assign(revisao, { tipo_id: linha.dados.tipo_id || '', emissao: linha.dados.emissao || '', vencimento: linha.dados.vencimento || '', valor: linha.dados.valor || '', pagamento_data: linha.dados.pagamento_data || '', valor_pago: linha.dados.valor_pago || '0', movimento_id: '', confirmar_novo: false })
  erro.value = ''; buscaTipo.value = ''; modalLinha.value = true; carregarTipos()
}
async function salvarLinha() {
  processando.value = true; erro.value = ''
  try {
    const dados = { tipo_id: Number(revisao.tipo_id), emissao: revisao.emissao || null, vencimento: revisao.vencimento, valor: revisao.valor, pagamento_data: revisao.pagamento_data || null, valor_pago: revisao.valor_pago }
    if (linhaAtual.value.dados.classificacao === 'AMBIGUA') {
      if (revisao.movimento_id) dados.movimento_id = Number(revisao.movimento_id)
      else if (revisao.confirmar_novo) dados.confirmar_novo = true
      else throw new Error('Escolha um lançamento existente ou confirme que é uma nova movimentação.')
    }
    await enviarJson(`lotes/${captura.value.id}/linhas/${linhaAtual.value.id}/`, 'PATCH', dados)
    modalLinha.value = false
    await carregar()
    aviso.value = 'Linha revisada. Confira o resumo antes de consolidar.'
  } catch (e) { erro.value = e.message } finally { processando.value = false }
}
async function resolverConflito(item, decisao) {
  erro.value = ''
  try { await enviarJson(`conflitos/${item.id}/resolver/`, 'POST', { decisao }); await carregar(); aviso.value = 'Conflito resolvido.' }
  catch (e) { erro.value = e.message }
}
watch(() => filialAtiva.value.id, async () => {
  captura.value = null; resumo.value = null; erro.value = ''; aviso.value = ''; pagina.value = 1
  try { await carregar() } catch (e) { erro.value = e.message }
})
onMounted(async () => { try { await carregar() } catch (e) { erro.value = e.message } })
</script>

<template>
  <div class="mx-auto max-w-[1500px] space-y-5 pb-8">
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-xl font-semibold text-[#373435]">Captura e validação de despesas</h1>
        <p class="mt-1 text-sm text-gray-500">Confira o que a fonte já contém, o que mudou e o que precisa de decisão antes de consolidar.</p>
      </div>
      <span class="rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600">{{ filialAtiva.nome }}</span>
    </header>

    <p v-if="erro && !modalLinha" role="alert" class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{{ erro }}</p>
    <p v-if="aviso" role="status" class="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">{{ aviso }}</p>

    <section v-if="!capturas.length" class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div class="flex items-start gap-3"><div class="rounded-lg bg-[#edf3ef] p-2 text-[#2f6f4f]"><FileUp class="h-5 w-5" /></div><div><h2 class="text-base font-semibold text-[#373435]">Importar planilha</h2><p class="mt-1 text-sm text-gray-500">A planilha será analisada nesta página. Nada será gravado nas movimentações até a confirmação.</p></div></div>
      <form class="mt-5 flex flex-wrap items-end gap-3" @submit.prevent="enviar">
        <label class="min-w-[260px] flex-1 text-xs font-semibold text-gray-600">Arquivo XLSX ou XLSM
          <input type="file" accept=".xlsx,.xlsm" class="mt-2 block w-full rounded-lg border border-gray-200 bg-white p-2.5 text-sm text-gray-700 file:mr-3 file:rounded-md file:border-0 file:bg-gray-100 file:px-3 file:py-1.5 file:text-xs file:font-semibold" @change="arquivo = $event.target.files?.[0]" />
        </label>
        <button type="submit" :disabled="!arquivo || processando" class="inline-flex items-center gap-2 rounded-lg bg-[#373435] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#4b4948] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2f6f4f] disabled:opacity-50"><FileUp class="h-4 w-4" />{{ processando ? 'Analisando arquivo…' : 'Analisar arquivo' }}</button>
      </form>
      <p class="mt-4 text-xs text-gray-500">Lê a aba pgtdia, com DESPESA, VALOR e VENCIMENTO na linha 4. Emissão, fornecedor, documento, observações e pagamento enriquecem a validação. O arquivo não precisa de ID.</p>
    </section>

    <template v-else>
      <div v-if="capturas.length > 1" class="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"><AlertCircle class="mr-2 inline h-4 w-4" />Existem {{ capturas.length }} capturas antigas abertas nesta filial. Revise ou descarte cada uma antes de importar outro arquivo.</div>
      <section class="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div><span class="text-[11px] font-semibold uppercase tracking-wider text-[#2f6f4f]">Captura em validação</span><h2 class="mt-1 text-lg font-semibold text-[#373435]">{{ captura?.nome_arquivo }}</h2><p class="mt-1 text-xs text-gray-500">Captura #{{ captura?.id }} · Recebida em {{ dataBR(captura?.criado_em) }} · Apenas uma captura ativa por filial</p></div>
          <div class="flex flex-wrap gap-2">
            <button type="button" :disabled="processando || filialDivergente(captura)" title="Reanalisa o arquivo original e substitui as revisões feitas nesta captura" class="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-[#2f6f4f] disabled:opacity-50" @click="revalidar"><RefreshCw class="h-3.5 w-3.5" />Revalidar original</button>
            <button type="button" :disabled="processando" class="inline-flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-2 text-xs font-medium text-red-700 hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-red-500 disabled:opacity-50" @click="modalDescarte = true"><Trash2 class="h-3.5 w-3.5" />Descartar captura</button>
          </div>
        </div>
        <div v-if="capturas.length > 1" class="mt-4 flex flex-wrap gap-2"><button v-for="item in capturas" :key="item.id" type="button" :aria-pressed="captura?.id === item.id" class="rounded-full px-3 py-1.5 text-xs font-medium" :class="captura?.id === item.id ? 'bg-[#373435] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'" @click="selecionar(item)">{{ item.nome_arquivo }} · #{{ item.id }}</button></div>
        <p v-if="filialDivergente(captura)" role="alert" class="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">O nome do arquivo indica outra filial. Revalidação e consolidação estão bloqueadas nesta tela.</p>
      </section>

      <section v-if="resumo" aria-label="Resumo da validação" class="grid gap-3 sm:grid-cols-3 xl:grid-cols-7">
        <div v-for="item in [{ rotulo: 'Já existentes', chave: 'EXISTENTE' }, { rotulo: 'Novas', chave: 'NOVA' }, { rotulo: 'Alteradas', chave: 'ALTERADA' }, { rotulo: 'Ambíguas', chave: 'AMBIGUA' }, { rotulo: 'Inválidas', chave: 'INVALIDA' }, { rotulo: 'Ignoradas', chave: 'IGNORADA' }, { rotulo: 'A classificar', chave: 'SEM_CLASSIFICACAO' }]" :key="item.chave" class="rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm"><div class="text-xs text-gray-500">{{ item.rotulo }}</div><div class="mt-1 text-2xl font-semibold tabular-nums text-[#373435]">{{ resumo.classificacoes?.[item.chave] || 0 }}</div></div>
      </section>
      <p v-if="resumo?.classificacoes?.SEM_CLASSIFICACAO" role="status" class="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">Esta captura foi recebida antes da classificação por ocorrência. Use <strong>Revalidar original</strong> para conferir existentes, novas e alterações. Isso substitui as revisões temporárias já feitas neste arquivo.</p>

      <section v-if="resumo" class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-5 py-4"><div><h2 class="text-sm font-semibold text-[#373435]">Linhas da planilha</h2><p class="mt-1 text-xs text-gray-500">{{ resumo.total }} linhas analisadas · {{ resumo.prontas }} prontas · {{ resumo.pendentes }} pedem revisão</p></div><form class="flex items-center gap-2" @submit.prevent="filtrar"><label class="sr-only" for="busca-linhas-despesa">Buscar tipo, documento ou observação</label><input id="busca-linhas-despesa" v-model="busca" class="w-48 rounded-lg border border-gray-200 px-3 py-2 text-xs focus-visible:outline-2 focus-visible:outline-[#2f6f4f] sm:w-64" placeholder="Buscar na captura" /><button type="submit" aria-label="Buscar linhas" title="Buscar linhas" class="rounded-lg border border-gray-200 p-2 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-[#2f6f4f]"><Search class="h-4 w-4" /></button></form></div>
        <div class="flex flex-wrap gap-2 border-b border-gray-100 px-5 py-3" aria-label="Filtrar linhas por situação"><button v-for="filtro in filtros" :key="filtro.valor" type="button" :aria-pressed="classificacao === filtro.valor" class="rounded-full px-3 py-1.5 text-xs font-medium focus-visible:outline-2 focus-visible:outline-[#2f6f4f]" :class="classificacao === filtro.valor ? 'bg-[#373435] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'" @click="alterarFiltro(filtro.valor)">{{ filtro.nome }} <span v-if="filtro.valor && resumo.classificacoes?.[filtro.valor] != null" class="ml-1 opacity-70">{{ resumo.classificacoes[filtro.valor] }}</span></button></div>
        <div class="overflow-x-auto"><table class="min-w-[850px] w-full text-left text-xs"><thead class="bg-gray-50 text-[11px] uppercase tracking-wide text-gray-500"><tr><th scope="col" class="px-4 py-3">Linha</th><th scope="col" class="px-4 py-3">Despesa / documento</th><th scope="col" class="px-4 py-3">Vencimento</th><th scope="col" class="px-4 py-3 text-right">Valor</th><th scope="col" class="px-4 py-3">Situação</th><th scope="col" class="px-4 py-3">Revisão</th></tr></thead><tbody><tr v-for="linha in linhas" :key="linha.id" class="border-t border-gray-100 hover:bg-gray-50/70"><td class="px-4 py-3 tabular-nums text-gray-500">{{ linha.numero }}</td><td class="px-4 py-3"><span class="font-semibold text-[#373435]">{{ linha.dados.nome_tipo_origem || '—' }}</span><span v-if="linha.dados.documento" class="mt-0.5 block text-gray-500">{{ linha.dados.documento }}</span><span v-if="linha.dados.observacoes" class="mt-0.5 block max-w-[340px] truncate text-gray-400" :title="linha.dados.observacoes">{{ linha.dados.observacoes }}</span></td><td class="px-4 py-3 tabular-nums">{{ dataBR(linha.dados.vencimento) }}</td><td class="px-4 py-3 text-right font-medium tabular-nums">{{ dinheiro(linha.dados.valor) }}</td><td class="px-4 py-3"><span class="rounded-full px-2 py-1 text-[11px] font-semibold" :class="estilos[linha.dados.classificacao || (linha.status === 'IGNORADO' ? 'IGNORADA' : 'SEM_CLASSIFICACAO')]">{{ nomes[linha.dados.classificacao || (linha.status === 'IGNORADO' ? 'IGNORADA' : 'SEM_CLASSIFICACAO')] }}</span><span v-if="linha.erros.length" class="mt-1.5 block max-w-[280px] text-amber-700" :title="linha.erros.join(' · ')">{{ linha.erros[0] }}</span></td><td class="px-4 py-3"><button v-if="linha.status === 'PENDENTE'" type="button" class="rounded-md px-2 py-1.5 font-semibold text-[#2f6f4f] hover:bg-green-50 focus-visible:outline-2 focus-visible:outline-[#2f6f4f]" @click="abrirLinha(linha)">Revisar</button><Check v-else-if="linha.status === 'PRONTO'" class="h-4 w-4 text-green-600" aria-label="Pronta" /></td></tr><tr v-if="!linhas.length"><td colspan="6" class="px-4 py-10 text-center text-sm text-gray-500">Nenhuma linha neste filtro.</td></tr></tbody></table></div>
        <div class="flex items-center justify-between border-t border-gray-100 px-5 py-3 text-xs text-gray-500"><span>{{ totalLinhas }} linhas encontradas · página {{ pagina }} de {{ Math.max(1, Math.ceil(totalLinhas / 100)) }}</span><div class="flex gap-1"><button type="button" :disabled="pagina <= 1" aria-label="Página anterior" class="rounded-md border border-gray-200 p-2 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-[#2f6f4f] disabled:opacity-40" @click="mudarPagina(pagina - 1)"><ChevronLeft class="h-4 w-4" /></button><button type="button" :disabled="pagina * 100 >= totalLinhas" aria-label="Próxima página" class="rounded-md border border-gray-200 p-2 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-[#2f6f4f] disabled:opacity-40" @click="mudarPagina(pagina + 1)"><ChevronRight class="h-4 w-4" /></button></div></div>
      </section>

      <div v-if="resumo?.motivos?.length" class="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-xs text-amber-900"><strong>Motivos que exigem atenção</strong><div class="mt-2 flex flex-wrap gap-2"><span v-for="motivo in resumo.motivos" :key="motivo.motivo" class="rounded-full bg-white px-2.5 py-1">{{ motivo.motivo }} · {{ motivo.quantidade }}</span></div></div>
      <section class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-sm"><div><h2 class="text-sm font-semibold text-[#373435]">Confirmar captura</h2><p class="mt-1 text-xs text-gray-500">A consolidação só deve começar quando todas as linhas aproveitáveis estiverem resolvidas.</p></div><button type="button" :disabled="!podeConsolidar" class="rounded-lg bg-[#2f6f4f] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#275e43] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2f6f4f] disabled:opacity-50" @click="consolidar">{{ processando ? 'Consolidando…' : 'Consolidar linhas prontas' }}</button></section>
    </template>

    <section class="rounded-xl border border-gray-200 bg-white shadow-sm"><button type="button" :aria-expanded="mostrarConflitos" class="flex w-full items-center justify-between px-5 py-4 text-left text-sm font-semibold text-[#373435] focus-visible:outline-2 focus-visible:outline-[#2f6f4f]" @click="mostrarConflitos = !mostrarConflitos"><span>Conflitos de cargas anteriores</span><span class="rounded-full bg-amber-50 px-2 py-1 text-xs text-amber-800">{{ conflitos.length }}</span></button><div v-if="mostrarConflitos" class="border-t border-gray-100"><p v-if="!conflitos.length" class="p-5 text-sm text-gray-500">Nenhum conflito pendente.</p><div v-for="item in conflitos" :key="item.id" class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-5 py-3 text-xs"><div><strong>Movimentação #{{ item.movimento_id }} · {{ item.campo }}</strong><p class="mt-1 text-gray-600">Atual: {{ item.valor_atual }} · Planilha: {{ item.valor_origem }}</p></div><div class="flex gap-2"><button type="button" class="rounded-md border px-2 py-1 hover:bg-gray-50" @click="resolverConflito(item, 'MANTER_MANUAL')">Manter correção</button><button type="button" class="rounded-md border px-2 py-1 hover:bg-gray-50" @click="resolverConflito(item, 'USAR_ORIGEM')">Usar planilha</button></div></div></div></section>

    <BaseModal v-model="modalDescarte" title="Descartar captura?" description="O arquivo e as linhas temporárias serão removidos. Movimentações oficiais não serão alteradas."><p class="text-sm text-gray-600">{{ captura?.nome_arquivo }}</p><p v-if="erro" role="alert" class="mt-3 text-xs text-red-700">{{ erro }}</p><template #footer><button type="button" class="rounded-lg border px-3 py-2 text-xs" @click="modalDescarte = false">Cancelar</button><button type="button" :disabled="processando" class="rounded-lg bg-red-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50" @click="descartar">Descartar captura</button></template></BaseModal>
    <BaseModal v-model="modalLinha" :title="`Revisar linha ${linhaAtual?.numero || ''}`" description="A revisão fica auditada. Confira a identidade quando a correspondência for ambígua."><form id="revisao-despesa-form" class="grid gap-3 sm:grid-cols-2" @submit.prevent="salvarLinha"><label class="text-xs font-medium text-gray-600">Buscar tipo<input v-model="buscaTipo" class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" placeholder="Nome do tipo" @input="carregarTipos" /></label><label class="text-xs font-medium text-gray-600">Tipo de despesa<select v-model="revisao.tipo_id" required class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm"><option value="">Selecione</option><option v-if="linhaAtual?.dados.tipo_id && !tipos.some(t => t.id === Number(revisao.tipo_id))" :value="revisao.tipo_id">{{ linhaAtual.dados.nome_tipo_origem }}</option><option v-for="tipo in tipos" :key="tipo.id" :value="tipo.id">{{ tipo.nome }}</option></select></label><label class="text-xs font-medium text-gray-600">Emissão<input v-model="revisao.emissao" type="date" class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label><label class="text-xs font-medium text-gray-600">Vencimento<input v-model="revisao.vencimento" type="date" required class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label><label class="text-xs font-medium text-gray-600">Valor<input v-model="revisao.valor" type="number" min="0" step="0.01" required class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label><label class="text-xs font-medium text-gray-600">Valor pago<input v-model="revisao.valor_pago" type="number" min="0" step="0.01" class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label><label class="text-xs font-medium text-gray-600">Data do pagamento<input v-model="revisao.pagamento_data" type="date" class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label><div v-if="linhaAtual?.dados.classificacao === 'AMBIGUA'" class="rounded-md bg-amber-50 p-3 text-xs sm:col-span-2"><strong>Conciliação ambígua</strong><p class="my-2">Escolha o lançamento correspondente ou confirme que esta é uma nova despesa.</p><label v-for="candidato in linhaAtual.dados.candidatos || []" :key="candidato.movimento_id" class="mt-1 flex gap-2"><input v-model="revisao.movimento_id" type="radio" :value="String(candidato.movimento_id)" @change="revisao.confirmar_novo = false" /><span>#{{ candidato.movimento_id }} · {{ candidato.tipo }} · {{ dataBR(candidato.vencimento) }} · {{ dinheiro(candidato.valor) }}</span></label><label class="mt-2 flex gap-2"><input v-model="revisao.confirmar_novo" type="checkbox" @change="revisao.movimento_id = ''" />É uma nova movimentação</label></div><p v-if="erro" role="alert" class="text-xs text-red-700 sm:col-span-2">{{ erro }}</p></form><template #footer><button type="button" class="rounded-md border px-3 py-2 text-xs" @click="modalLinha = false">Cancelar</button><button form="revisao-despesa-form" :disabled="processando" class="rounded-md bg-[#373435] px-3 py-2 text-xs text-white disabled:opacity-50">Salvar revisão</button></template></BaseModal>
  </div>
</template>
