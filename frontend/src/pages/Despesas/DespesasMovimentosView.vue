<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { Search } from 'lucide-vue-next'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import { despesasApi, dinheiro, enviarJson } from '@/services/despesasApi.js'
import { filialAtiva } from '@/stores/filial.js'

const route = useRoute()
const router = useRouter()
const modoBI = computed(() => route.query.bi === '1')
const contextoBI = ref(null)
const movimentos = ref([])
const total = ref(0)
const pagina = ref(Number(route.query.page) || 1)
const carregando = ref(false)
const salvando = ref(false)
const erro = ref('')
const aviso = ref('')
const buscaTipos = ref('')
const tipos = ref([])
const auditoria = ref([])
const buscaFornecedor = ref('')
const fornecedores = ref([])
const detalhe = ref(null)
const pagamentoAtual = ref(null)
const modalDetalhe = ref(false)
const modalMovimento = ref(false)
const modalPagamento = ref(false)
const filtro = reactive({
  busca: '', tipo_id: String(route.query.tipo_id || ''), folha_id: String(route.query.folha_id || ''),
  vencimento_inicio: String(route.query.vencimento_inicio || ''), vencimento_fim: String(route.query.vencimento_fim || ''), situacao: '',
})
const form = reactive({
  tipo: '', fornecedor: '', fornecedor_texto: '', documento: '', observacoes: '',
  emissao: '', vencimento: '', valor: '',
})
const formPagamento = reactive({ data: '', valor: '', forma: '' })
const colunas = [
  { key: 'vencimento', label: 'Vencimento' },
  { key: 'tipo_nome', label: 'Tipo de Despesa' },
  { key: 'observacoes', label: 'Observações' },
  { key: 'valor', label: 'Valor', cellClass: 'text-right' },
  { key: 'saldo', label: 'Saldo', cellClass: 'text-right' },
  { key: 'origem', label: 'Origem' },
]

function dataBR(valor) {
  if (!valor) return '—'
  const [ano, mes, dia] = valor.split('-')
  return `${dia}/${mes}/${ano}`
}

async function carregarTipos() {
  try {
    const resposta = await despesasApi(`tipos/?busca=${encodeURIComponent(buscaTipos.value)}&ativo=1`)
    tipos.value = resposta.results || []
  } catch (e) { erro.value = e.message }
}

async function carregarFornecedores() {
  try {
    const resposta = await fetch(`${filialAtiva.value.apiUrl}/api/cadastros/fornecedores?search=${encodeURIComponent(buscaFornecedor.value)}`)
    if (!resposta.ok) throw new Error('Não foi possível carregar fornecedores.')
    fornecedores.value = (await resposta.json()).results || []
  } catch (e) { erro.value = e.message }
}

async function carregar() {
  carregando.value = true
  erro.value = ''
  try {
    const params = new URLSearchParams({ page: String(pagina.value) })
    if (modoBI.value) {
      for (const chave of ['familia_id', 'folha_id', 'tipo_id', 'visao', 'base', 'ano', 'periodo_equivalente', 'periodo']) if (route.query[chave] != null) params.set(chave, String(route.query[chave]))
    } else for (const [chave, valor] of Object.entries(filtro)) if (valor) params.set(chave, valor)
    const resposta = await despesasApi(`${modoBI.value ? 'bi/movimentos/' : 'movimentos/'}?${params}`)
    movimentos.value = resposta.results || []
    total.value = resposta.count || 0
    if (modoBI.value) contextoBI.value = resposta
    else router.replace({ query: {
      ...(filtro.tipo_id ? { tipo_id: filtro.tipo_id } : {}),
      ...(filtro.folha_id ? { folha_id: filtro.folha_id } : {}),
      ...(filtro.vencimento_inicio ? { vencimento_inicio: filtro.vencimento_inicio } : {}),
      ...(filtro.vencimento_fim ? { vencimento_fim: filtro.vencimento_fim } : {}),
    } })
  } catch (e) { erro.value = e.message }
  finally { carregando.value = false }
}

async function abrirDetalhe(item) {
  try {
    const linhaBI = modoBI.value ? movimentos.value.find((linha) => linha.id === item.id) : null
    if (modoBI.value && !linhaBI) { modalDetalhe.value = false; detalhe.value = null; return }
    detalhe.value = await despesasApi(`movimentos/${item.id}/`)
    if (modoBI.value) { detalhe.value.valor_periodo = linhaBI.valor_periodo; detalhe.value.pagamentos_periodo = linhaBI.pagamentos_periodo || [] }
    auditoria.value = await despesasApi(`auditoria/?entidade=movimento&id=${item.id}`)
    modalDetalhe.value = true
    erro.value = ''
  } catch (e) { erro.value = e.message }
}

function abrirMovimento(item) {
  Object.assign(form, {
    tipo: item.tipo, fornecedor: item.fornecedor || '', fornecedor_texto: item.fornecedor_texto || '',
    documento: item.documento || '', observacoes: item.observacoes || '', emissao: item.emissao || '',
    vencimento: item.vencimento || '', valor: item.valor ?? '',
  })
  modalDetalhe.value = false
  modalMovimento.value = true
  erro.value = ''
  buscaTipos.value = ''
  buscaFornecedor.value = ''
  carregarTipos()
  carregarFornecedores()
}

async function salvarMovimento() {
  salvando.value = true
  erro.value = ''
  try {
    const corpo = { ...form, tipo: Number(form.tipo), fornecedor: form.fornecedor ? Number(form.fornecedor) : null, emissao: form.emissao || null }
    const atualizado = await enviarJson(`movimentos/${detalhe.value.id}/`, 'PATCH', corpo)
    modalMovimento.value = false
    aviso.value = 'Movimentação atualizada.'
    await carregar()
    await abrirDetalhe(atualizado)
  } catch (e) { erro.value = e.message }
  finally { salvando.value = false }
}

function abrirPagamento(item) {
  pagamentoAtual.value = item
  Object.assign(formPagamento, { data: item.data, valor: item.valor, forma: item.forma || '' })
  modalDetalhe.value = false
  modalPagamento.value = true
  erro.value = ''
}

async function salvarPagamento() {
  salvando.value = true
  erro.value = ''
  try {
    await enviarJson(`pagamentos/${pagamentoAtual.value.id}/`, 'PATCH', formPagamento)
    modalPagamento.value = false
    aviso.value = 'Pagamento atualizado.'
    await carregar()
    await abrirDetalhe({ id: detalhe.value.id })
  } catch (e) { erro.value = e.message }
  finally { salvando.value = false }
}

async function excluirPagamento(item) {
  if (!confirm('Excluir este pagamento? Uma nova importação poderá trazê-lo novamente conforme a fonte.')) return
  try {
    await despesasApi(`pagamentos/${item.id}/`, { method: 'DELETE' })
    aviso.value = 'Pagamento excluído.'
    await carregar()
    await abrirDetalhe({ id: detalhe.value.id })
  } catch (e) { erro.value = e.message }
}

async function excluirMovimento() {
  if (!detalhe.value || !confirm('Excluir esta movimentação e seu pagamento? Uma nova importação poderá trazê-los novamente conforme a fonte.')) return
  try {
    await despesasApi(`movimentos/${detalhe.value.id}/`, { method: 'DELETE' })
    modalDetalhe.value = false
    detalhe.value = null
    aviso.value = 'Movimentação excluída.'
    await carregar()
  } catch (e) { erro.value = e.message }
}

onMounted(carregar)
watch(() => route.query.page, (novo) => { if (modoBI.value) { pagina.value = Number(novo) || 1; carregar() } })
watch(() => filialAtiva.value.id, () => {
  if (modoBI.value) router.replace({ path: '/analise/despesas', query: { visao: route.query.visao, base: route.query.base, ano: route.query.ano, periodo_equivalente: route.query.periodo_equivalente } })
  else { pagina.value = 1; carregar() }
})
function mudarPagina(nova) { if (modoBI.value) router.push({ query: { ...route.query, page: String(nova) } }); else { pagina.value = nova; carregar() } }
</script>

<template>
  <div class="mx-auto max-w-[1500px] space-y-5">
    <header>
      <h1 class="text-xl font-semibold text-[#373435]">Movimentações de despesas</h1>
      <p class="mt-1 text-xs text-gray-500">{{ modoBI ? `Composição de ${contextoBI?.tipo?.nome || 'Tipo de Despesa'} em ${contextoBI?.periodo?.periodo || 'período selecionado'}.` : 'Consulte lançamentos recebidos da fonte e corrija seus dados quando necessário.' }}</p>
    </header>

    <div v-if="modoBI && contextoBI" class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-gray-200 bg-white px-4 py-3 text-xs"><div><strong>{{ contextoBI.base === 'PAGAMENTO' ? 'Pagamentos no período' : 'Obrigações no período' }}: {{ dinheiro(contextoBI.total_filtrado) }}</strong><span class="ml-2 text-gray-500">Agregado da célula: {{ dinheiro(contextoBI.total_agregado) }} · {{ contextoBI.periodo?.intervalos_detalhe?.length }} {{ contextoBI.periodo?.intervalos_detalhe?.length === 1 ? 'intervalo utilizado' : 'intervalos utilizados' }}</span></div><RouterLink :to="{ path: '/analise/despesas/tipos', query: { familia_id: route.query.familia_id, categoria_id: route.query.tipos_categoria_id || undefined, folha_id: route.query.tipos_categoria_id ? undefined : route.query.folha_id, busca: route.query.tipos_busca || undefined, page: route.query.tipos_page || undefined, visao: route.query.visao, base: route.query.base, ano: route.query.ano, periodo_equivalente: route.query.periodo_equivalente, periodo: route.query.periodo } }" class="font-semibold text-gray-700 hover:underline focus-visible:outline focus-visible:outline-2">Voltar aos tipos</RouterLink></div>
    <details v-if="modoBI && contextoBI" class="rounded-md border border-gray-200 bg-white px-4 py-2 text-xs text-gray-600"><summary class="cursor-pointer font-medium">Datas incluídas na célula</summary><p v-for="(intervalo, indice) in contextoBI.periodo?.intervalos_detalhe || []" :key="indice" class="py-0.5">{{ dataBR(intervalo.inicio) }} a {{ dataBR(intervalo.fim) }}</p></details>
    <p v-if="modoBI && contextoBI && !contextoBI.conciliado" role="alert" class="rounded-md border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800">O total oficial filtrado difere do agregado da análise. Atualize a consolidação deste período antes de interpretar a célula.</p>

    <p v-if="erro && !modalMovimento && !modalPagamento" role="alert" class="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-xs text-red-700">{{ erro }}</p>
    <p v-if="aviso" role="status" class="rounded-md border border-green-200 bg-green-50 px-4 py-2 text-xs text-green-700">{{ aviso }}</p>

    <BaseTable
      title="Lançamentos"
      :subtitle="modoBI ? 'Somente os lançamentos ou pagamentos que compõem a célula selecionada' : 'Abra uma linha para consultar o pagamento informado e o histórico'"
      :columns="modoBI ? colunas.map(c => c.key === 'valor' ? { ...c, label: contextoBI?.base === 'PAGAMENTO' ? 'Pago no período' : 'Valor no período' } : c) : colunas" :rows="movimentos" :count="total" :loading="carregando" :error="erro"
      :previous="pagina > 1 ? 'sim' : ''" :next="pagina * 100 < total ? 'sim' : ''"
      empty-text="Nenhuma movimentação encontrada."
      @previous="mudarPagina(pagina - 1)" @next="mudarPagina(pagina + 1)"
    >
      <template #header-extra>
        <form v-if="!modoBI" class="flex flex-wrap items-center gap-2" @submit.prevent="pagina = 1; carregar()">
          <label class="flex items-center gap-2 rounded-md border border-gray-200 px-2 py-1.5">
            <Search class="h-4 w-4 text-gray-400" />
            <input v-model="filtro.busca" class="w-44 bg-transparent text-xs outline-none" placeholder="Tipo, documento, observações" aria-label="Buscar movimentação" />
          </label>
          <input v-model="filtro.vencimento_inicio" type="date" class="rounded-md border border-gray-200 px-2 py-1.5 text-xs" aria-label="Vencimento inicial" />
          <input v-model="filtro.vencimento_fim" type="date" class="rounded-md border border-gray-200 px-2 py-1.5 text-xs" aria-label="Vencimento final" />
          <select v-model="filtro.situacao" class="rounded-md border border-gray-200 px-2 py-1.5 text-xs" aria-label="Situação">
            <option value="">Todas</option><option value="ABERTO">Em aberto</option>
          </select>
          <button class="rounded-md border border-gray-200 px-3 py-2 text-xs hover:bg-gray-50">Filtrar</button>
        </form>
      </template>
      <template #cell-vencimento="{ row }">{{ dataBR(row.vencimento) }}</template>
      <template #cell-tipo_nome="{ row }"><span class="font-medium">{{ row.tipo_nome }}</span></template>
      <template #cell-observacoes="{ row }"><span class="block max-w-[26rem] truncate" :title="row.observacoes || ''">{{ row.observacoes || '—' }}</span></template>
      <template #cell-valor="{ row }"><span class="font-mono tabular-nums">{{ dinheiro(modoBI ? row.valor_periodo : row.valor) }}</span></template>
      <template #cell-saldo="{ row }"><span class="font-mono tabular-nums" :class="Number(row.saldo) > 0 ? 'text-amber-700' : 'text-green-700'">{{ dinheiro(row.saldo) }}</span></template>
      <template #cell-origem="{ row }"><span class="rounded-full bg-gray-100 px-2 py-1 text-[10px]">{{ row.origem === 'XLSX' ? 'Importada' : 'Manual' }}</span></template>
      <template #actions="{ row }"><button type="button" class="rounded-md border border-gray-200 px-3 py-1.5 text-xs hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#373435]" @click="abrirDetalhe(row)">Detalhes</button></template>
    </BaseTable>

    <BaseModal v-model="modalDetalhe" :title="`Movimentação #${detalhe?.id || ''}`" :description="detalhe ? `${detalhe.tipo_nome} · vence em ${dataBR(detalhe.vencimento)}` : ''">
      <template v-if="detalhe">
        <div class="grid gap-3 rounded-md bg-gray-50 p-4 text-xs sm:grid-cols-3">
          <div><span class="text-gray-500">{{ modoBI ? 'No período selecionado' : 'Valor' }}</span><p class="mt-1 font-mono text-base font-semibold">{{ dinheiro(modoBI ? detalhe.valor_periodo : detalhe.valor) }}</p></div>
          <div><span class="text-gray-500">Pago</span><p class="mt-1 font-mono text-base font-semibold">{{ dinheiro(Number(detalhe.valor) - Number(detalhe.saldo)) }}</p></div>
          <div><span class="text-gray-500">Saldo</span><p class="mt-1 font-mono text-base font-semibold">{{ dinheiro(detalhe.saldo) }}</p></div>
        </div>
        <dl class="mt-4 grid gap-2 text-xs sm:grid-cols-2">
          <div><dt class="text-gray-500">Fornecedor</dt><dd>{{ detalhe.fornecedor_texto || 'Não informado' }}</dd></div>
          <div><dt class="text-gray-500">Documento</dt><dd>{{ detalhe.documento || 'Não informado' }}</dd></div>
          <div><dt class="text-gray-500">Emissão</dt><dd>{{ dataBR(detalhe.emissao) }}</dd></div>
          <div><dt class="text-gray-500">Origem</dt><dd>{{ detalhe.origem }}</dd></div>
        </dl>
        <p v-if="detalhe.observacoes" class="mt-3 whitespace-pre-wrap text-xs text-gray-600">{{ detalhe.observacoes }}</p>
        <h4 class="mt-5 border-b pb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Pagamento informado <span v-if="modoBI && contextoBI?.base === 'PAGAMENTO'" class="font-normal normal-case">· {{ detalhe.pagamentos_periodo.length }} no período selecionado</span></h4>
        <p v-if="!detalhe.pagamentos.length" class="py-3 text-xs text-gray-500">Nenhum pagamento informado pela fonte.</p>
        <div v-for="p in detalhe.pagamentos" :key="p.id" class="flex flex-wrap items-center justify-between gap-2 border-b py-2 text-xs" :class="modoBI && contextoBI?.base === 'PAGAMENTO' && !detalhe.pagamentos_periodo.some(item => item.id === p.id) ? 'opacity-45' : ''">
          <span>{{ dataBR(p.data) }} · <strong>{{ dinheiro(p.valor) }}</strong> · {{ p.forma || 'Forma não informada' }}</span>
          <span class="flex gap-2">
            <button type="button" class="text-[#2f6f4f] hover:underline focus-visible:outline focus-visible:outline-2" @click="abrirPagamento(p)">Editar</button>
            <button type="button" class="text-red-700 hover:underline focus-visible:outline focus-visible:outline-2" @click="excluirPagamento(p)">Excluir</button>
          </span>
        </div>
        <details class="mt-4 text-xs">
          <summary class="cursor-pointer font-semibold text-gray-600">Histórico de alterações</summary>
          <div v-for="a in auditoria" :key="a.criado_em" class="border-b py-2">
            <strong>{{ a.acao }}</strong> · {{ dataBR(a.criado_em?.slice(0, 10)) }} · {{ a.operador || 'sem usuário identificado' }}
            <pre class="mt-1 whitespace-pre-wrap text-gray-500">{{ a.depois }}</pre>
          </div>
        </details>
      </template>
      <template #footer>
        <button type="button" class="mr-auto rounded-md border border-red-200 px-3 py-2 text-xs text-red-700" @click="excluirMovimento">Excluir</button>
        <button type="button" class="rounded-md border px-3 py-2 text-xs" @click="modalDetalhe = false">Fechar</button>
        <button type="button" class="rounded-md bg-[#373435] px-3 py-2 text-xs text-white" @click="abrirMovimento(detalhe)">Editar lançamento</button>
      </template>
    </BaseModal>

    <BaseModal v-model="modalMovimento" :title="`Editar movimentação #${detalhe?.id || ''}`" description="O vínculo do tipo determina a classificação no BI.">
      <form id="movimento-despesa-form" class="grid gap-3 sm:grid-cols-2" @submit.prevent="salvarMovimento">
        <p class="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 sm:col-span-2">Esta é uma correção local. Uma nova importação poderá trazer novamente os valores da fonte.</p>
        <label class="text-xs font-medium text-gray-600">Buscar tipo<input v-model="buscaTipos" class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" placeholder="Digite o nome" @input="carregarTipos" /></label>
        <label class="text-xs font-medium text-gray-600">Tipo de Despesa<select v-model="form.tipo" required class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm"><option value="">Selecione</option><option v-if="detalhe && !tipos.some(t => t.id === Number(form.tipo))" :value="form.tipo">{{ detalhe.tipo_nome }}</option><option v-for="t in tipos" :key="t.id" :value="t.id">{{ t.nome }}</option></select></label>
        <label class="text-xs font-medium text-gray-600">Emissão<input v-model="form.emissao" type="date" class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label>
        <label class="text-xs font-medium text-gray-600">Vencimento<input v-model="form.vencimento" type="date" required class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label>
        <label class="text-xs font-medium text-gray-600">Valor<input v-model="form.valor" type="number" min="0" step="0.01" required class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label>
        <label class="text-xs font-medium text-gray-600">Documento<input v-model="form.documento" class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label>
        <label class="text-xs font-medium text-gray-600">Fornecedor original<input v-model="form.fornecedor_texto" class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label>
        <label class="text-xs font-medium text-gray-600">Buscar fornecedor cadastrado<input v-model="buscaFornecedor" class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" placeholder="Digite o nome" @input="carregarFornecedores" /></label>
        <label class="text-xs font-medium text-gray-600">Fornecedor vinculado (opcional)<select v-model="form.fornecedor" class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm"><option value="">Sem vínculo</option><option v-if="form.fornecedor && !fornecedores.some(f => f.id_fornecedor === Number(form.fornecedor))" :value="form.fornecedor">Fornecedor atual #{{ form.fornecedor }}</option><option v-for="f in fornecedores" :key="f.id_fornecedor" :value="f.id_fornecedor">{{ f.nome_gerencial || f.nome_fornecedor }}</option></select></label>
        <label class="text-xs font-medium text-gray-600 sm:col-span-2">Observações<textarea v-model="form.observacoes" rows="2" class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label>
        <p v-if="erro" role="alert" class="text-xs text-red-600 sm:col-span-2">{{ erro }}</p>
      </form>
      <template #footer>
        <button type="button" class="rounded-md border px-3 py-2 text-xs" @click="modalMovimento = false; modalDetalhe = true">Cancelar</button>
        <button form="movimento-despesa-form" :disabled="salvando" class="rounded-md bg-[#373435] px-3 py-2 text-xs text-white disabled:opacity-50">Salvar correção</button>
      </template>
    </BaseModal>

    <BaseModal v-model="modalPagamento" title="Editar pagamento informado" :description="detalhe ? `${detalhe.tipo_nome} · saldo ${dinheiro(detalhe.saldo)}` : ''">
      <form id="pagamento-despesa-form" class="grid gap-3 sm:grid-cols-3" @submit.prevent="salvarPagamento">
        <p class="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 sm:col-span-3">Esta é uma correção local. Uma nova importação poderá trazer novamente os valores da fonte.</p>
        <label class="text-xs font-medium text-gray-600">Data<input v-model="formPagamento.data" type="date" required class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label>
        <label class="text-xs font-medium text-gray-600">Valor<input v-model="formPagamento.valor" type="number" min="0.01" step="0.01" required class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label>
        <label class="text-xs font-medium text-gray-600">Forma (opcional)<input v-model="formPagamento.forma" class="mt-1 w-full rounded-md border border-gray-200 px-3 py-2 text-sm" /></label>
        <p v-if="erro" role="alert" class="text-xs text-red-600 sm:col-span-3">{{ erro }}</p>
      </form>
      <template #footer>
        <button type="button" class="rounded-md border px-3 py-2 text-xs" @click="modalPagamento = false; modalDetalhe = true">Cancelar</button>
        <button form="pagamento-despesa-form" :disabled="salvando" class="rounded-md bg-[#373435] px-3 py-2 text-xs text-white disabled:opacity-50">Salvar correção</button>
      </template>
    </BaseModal>
  </div>
</template>
