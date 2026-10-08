<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { AlertTriangle, ChevronDown, ChevronRight, ExternalLink, Info, Layers3, RefreshCw } from 'lucide-vue-next'
import { MESES, mapaQuartis, numeroFinanceiro } from '@/pages/analise/analiseMensalUtils.js'
import { despesasApi } from '@/services/despesasApi.js'
import { filialAtiva } from '@/stores/filial.js'

const route = useRoute()
const router = useRouter()
const familias = ref([])
const familiasCarregadas = ref(false)
const dados = ref(null)
const erro = ref('')
const carregando = ref(false)
const expandidos = ref(new Set())
let sequencia = 0
let sequenciaFamilias = 0

const anoCorrente = new Date().getFullYear()
const familiaId = computed(() => String(route.query.familia_id || ''))
const visao = computed(() => route.query.visao === 'anual' ? 'anual' : 'mensal')
const base = computed(() => route.query.base === 'VENCIMENTO' ? 'VENCIMENTO' : 'PAGAMENTO')
const ano = computed(() => {
  const selecionado = Number(route.query.ano)
  return Number.isInteger(selecionado) && selecionado >= 1900 && selecionado <= 2200 ? selecionado : anoCorrente
})
const equivalente = computed(() => route.query.periodo_equivalente === undefined
  ? visao.value === 'anual' && ano.value === anoCorrente
  : String(route.query.periodo_equivalente) === '1')
const podeEquivaler = computed(() => ano.value === anoCorrente && (visao.value === 'anual' ? dados.value?.ano_parcial : dados.value?.mes_aberto))
const anos = computed(() => [...new Set([anoCorrente, ano.value, ...(dados.value?.anos_disponiveis || [])])].sort((a, b) => b - a))
const periodos = computed(() => dados.value?.periodos || [])
const categorias = computed(() => dados.value?.categorias || [])
const categoriasPorId = computed(() => new Map(categorias.value.map((no) => [no.id, no])))
const filhos = computed(() => {
  const mapa = new Map()
  for (const no of categorias.value) {
    if (!mapa.has(no.pai_id)) mapa.set(no.pai_id, [])
    mapa.get(no.pai_id).push(no)
  }
  return mapa
})
const linhas = computed(() => {
  const raiz = categoriasPorId.value.get(dados.value?.familia?.id)
  if (!raiz) return []
  const resultado = []
  function visitar(no) {
    resultado.push({ chave: `c-${no.id}`, no, nivel: no.nivel, expansivel: !no.folha })
    if (!expandidos.value.has(no.id)) return
    for (const filho of filhos.value.get(no.id) || []) visitar(filho)
  }
  visitar(raiz)
  return resultado
})
const colunasIgnoradas = computed(() => periodos.value.flatMap((p, i) =>
  p.estado === 'PRONTO' || p.estado === 'PARCIAL'
    ? p.posicao_calendario === 'FUTURO' || (p.posicao_calendario === 'CORRENTE' && !dados.value?.periodo_equivalente) ? [i] : []
    : [i]))
const quartis = computed(() => new Map(
  categorias.value.map((no) => [`c-${no.id}`, no])
    .map(([chave, no]) => [chave, mapaQuartis(periodos.value.map((p) => no.valores?.[p.periodo]), colunasIgnoradas.value)]),
))
const faltantes = computed(() => periodos.value.filter((p) => p.posicao_calendario !== 'FUTURO' && !['PRONTO', 'PARCIAL'].includes(p.estado)))
const semDiario = computed(() => faltantes.value.some((p) => p.estado_snapshot === 'DIARIO_AUSENTE'))
const raiz = computed(() => categoriasPorId.value.get(dados.value?.familia?.id))
const naoClassificados = computed(() => dados.value?.nao_classificados)
const tituloVariacoes = computed(() => {
  const pares = periodos.value.slice(0, -2).map((p, i) => `${p.periodo}→${periodos.value[i + 1].periodo}`)
  const media = pares.length ? `Média das variações ${pares.join(' e ')}.` : 'Média histórica indisponível: menos de dois anos anteriores.'
  const ultimos = periodos.value.slice(-2)
  const recente = ultimos.length === 2 ? `Recente: ${ultimos[0].periodo}→${ultimos[1].periodo}.` : 'Recente indisponível: sem ano anterior.'
  return `${media} ${recente}${dados.value?.ano_parcial && !dados.value?.periodo_equivalente ? ' O ano foco está parcial; as durações são diferentes.' : ''}`
})

function dataCurta(valor) {
  if (!valor) return '—'
  const [a, m, d] = String(valor).slice(0, 10).split('-')
  return d && m && a ? `${d}/${m}/${a}` : '—'
}
function dataHora(valor) { return valor ? new Date(valor).toLocaleString('pt-BR') : '—' }
function formatarValor(valor) {
  if (valor === null || valor === undefined) return '—'
  const numero = Number(valor)
  return Number.isFinite(numero) ? numero.toLocaleString('pt-BR', { maximumFractionDigits: 0 }) : '—'
}
function valorExato(valor) {
  return valor == null || !Number.isFinite(Number(valor)) ? 'Valor indisponível'
    : `Valor: ${Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
function formatarVariacao(valor) {
  if (valor == null || !Number.isFinite(Number(valor))) return '—'
  const numero = Number(valor)
  return `${numero > 0 ? '+' : ''}${numero.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`
}
function temValor(valor) { return valor != null && Number(valor) !== 0 }
function tituloPeriodo(p) { return visao.value === 'anual' ? p.periodo : MESES[Number(p.periodo.slice(5, 7)) - 1] }
function rotuloPeriodo(p) {
  if (p.posicao_calendario === 'FUTURO' && base.value === 'PAGAMENTO') return 'Futuro'
  if (p.posicao_calendario === 'FUTURO' && base.value === 'VENCIMENTO') {
    if (p.estado_snapshot === 'PRONTO') return 'Programado'
    if (p.estado_snapshot === 'FALHO') return 'Programado · falha'
    if (p.estado_snapshot === 'PENDENTE') return 'Programado · atualizando'
    return 'Programado · sem agregado'
  }
  if (p.estado_snapshot === 'FALHO') return 'Falha'
  if (p.estado_snapshot === 'DIARIO_AUSENTE') return 'Sem diário'
  if (p.estado_snapshot === 'AUSENTE') return 'Sem agregado'
  if (p.estado_snapshot === 'PENDENTE') return 'Atualizando'
  if (p.posicao_calendario === 'CORRENTE') return 'Prévia'
  if (dados.value?.periodo_equivalente && p.data_corte) return `Até ${dataCurta(p.data_corte).slice(0, 5)}`
  return ''
}
function descricaoPeriodo(p) { return `${dataCurta(p.inicio)} a ${dataCurta(p.fim_efetivo || p.data_corte || p.fim)}${p.estado_snapshot === 'PRONTO' ? '' : ` · ${rotuloPeriodo(p)}`}` }
function nomeCompleto(no) {
  const nomes = [no.nome]
  let pai = categoriasPorId.value.get(no.pai_id)
  while (pai) { nomes.unshift(pai.nome); pai = categoriasPorId.value.get(pai.pai_id) }
  return nomes.join(' › ')
}
function estiloCelula(linha, valor, indice) {
  if (colunasIgnoradas.value.includes(indice)) return {}
  const numero = numeroFinanceiro(valor)
  const ponto = numero === null ? undefined : quartis.value.get(linha.chave)?.get(numero)
  return ponto === undefined ? {} : { backgroundColor: `rgba(55, 52, 53, ${ponto >= 0.75 ? 0.12 : ponto <= 0.25 ? 0.055 : 0.025})` }
}
function alternar(id) { const novos = new Set(expandidos.value); novos.has(id) ? novos.delete(id) : novos.add(id); expandidos.value = novos }
function expandirTudo() { expandidos.value = new Set(categorias.value.map((no) => no.id)) }
function recolherTudo() { expandidos.value = new Set(dados.value ? [dados.value.familia.id] : []) }
async function focarCategoria() {
  const alvo = categoriasPorId.value.get(Number(route.query.categoria_id))
  if (!alvo) return
  const abertos = new Set(expandidos.value)
  let pai = categoriasPorId.value.get(alvo.pai_id)
  while (pai) { abertos.add(pai.id); pai = categoriasPorId.value.get(pai.pai_id) }
  expandidos.value = abertos
  await nextTick()
  document.getElementById(`despesa-categoria-${alvo.id}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' })
}
function linkFolha(no, periodoFoco = null) {
  return { path: '/analise/despesas/tipos', query: {
    familia_id: familiaId.value, folha_id: no.id, visao: visao.value, base: base.value,
    ano: String(ano.value), periodo_equivalente: equivalente.value ? '1' : '0',
    periodo: periodoFoco || (visao.value === 'mensal' ? `${ano.value}-${String(ano.value === anoCorrente ? new Date().getMonth() + 1 : 12).padStart(2, '0')}-01` : String(ano.value)),
  } }
}
function mudarFiltros(alteracoes) { router.push({ query: { ...route.query, ...alteracoes } }) }
function mudarVisao(nova) { mudarFiltros({ visao: nova, periodo_equivalente: nova === 'anual' && ano.value === anoCorrente ? '1' : '0' }) }
function mudarAno(novo) { mudarFiltros({ ano: String(novo), periodo_equivalente: visao.value === 'anual' && Number(novo) === anoCorrente ? '1' : '0' }) }

async function carregarFamilias(nomePreferido = null) {
  const atual = ++sequenciaFamilias
  familiasCarregadas.value = false
  try {
    const lista = await despesasApi('categorias/')
    if (atual !== sequenciaFamilias) return
    familias.value = lista.filter((no) => no.pai == null)
    familiasCarregadas.value = true
    const porNome = nomePreferido && familias.value.find((f) => f.nome === nomePreferido)
    const escolhida = porNome ? String(porNome.id)
      : familias.value.some((f) => String(f.id) === familiaId.value) ? familiaId.value
        : String(familias.value.find((f) => f.nome.toUpperCase() === 'DESPESAS')?.id || familias.value[0]?.id || '')
    if (!escolhida) { dados.value = null; return }
    const canonica = { familia_id: escolhida, visao: visao.value, base: base.value, ano: String(ano.value), periodo_equivalente: equivalente.value ? '1' : '0' }
    if (Object.entries(canonica).some(([chave, valor]) => String(route.query[chave] || '') !== valor)) {
      await router.replace({ query: { ...route.query, ...canonica } })
    } else carregar()
  } catch (e) {
    if (atual !== sequenciaFamilias) return
    familias.value = []
    familiasCarregadas.value = true
    erro.value = e?.message || 'Não foi possível carregar as famílias.'
  }
}
async function carregar() {
  if (!familiasCarregadas.value || !familiaId.value) return
  const atual = ++sequencia
  carregando.value = true
  erro.value = ''
  dados.value = null
  try {
    const params = new URLSearchParams({ familia_id: familiaId.value, visao: visao.value, base: base.value, ano: String(ano.value), periodo_equivalente: equivalente.value ? '1' : '0' })
    const resposta = await despesasApi(`bi/?${params}`)
    if (atual !== sequencia) return
    dados.value = resposta
    recolherTudo()
    await focarCategoria()
  } catch (e) {
    if (atual === sequencia) erro.value = e?.message || 'Não foi possível carregar a análise.'
  } finally {
    if (atual === sequencia) carregando.value = false
  }
}
watch(() => route.fullPath, () => {
  if (familiasCarregadas.value && familias.value.some((f) => String(f.id) === familiaId.value)) carregar()
})
watch(() => filialAtiva.value.id, () => {
  const anterior = familias.value.find((f) => String(f.id) === familiaId.value)?.nome
  ++sequencia
  dados.value = null
  carregarFamilias(anterior)
})
onMounted(carregarFamilias)
onUnmounted(() => { ++sequencia; ++sequenciaFamilias })
</script>

<template>
  <div class="flex w-full min-w-0 flex-col gap-5 text-[#373435]">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div><h1 class="text-xl font-bold text-gray-900">Despesas por Categoria</h1><p class="mt-0.5 text-sm text-gray-400">Obrigações ou saídas financeiras pela hierarquia do plano de contas.</p></div>
      <RouterLink to="/despesas/tipos" class="flex h-[34px] items-center rounded-md border border-gray-200 bg-white px-3 text-xs font-semibold text-gray-700 hover:bg-gray-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#373435]">Gerenciar classificações</RouterLink>
    </header>

    <article class="w-full min-w-0 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <section aria-label="Filtros da análise de despesas">
        <div class="flex flex-col gap-3 border-b border-gray-100 bg-gray-50/70 px-4 py-3 sm:flex-row sm:items-end sm:justify-between">
          <label class="flex w-full min-w-0 max-w-md flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500 sm:min-w-[260px]">Família do plano de contas
            <select :value="familiaId" class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium normal-case text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300" :disabled="!familias.length" @change="mudarFiltros({ familia_id: $event.target.value })"><option v-for="f in familias" :key="f.id" :value="String(f.id)">{{ f.nome }}</option></select>
          </label>
          <div v-if="dados && dados.estado_atualizacao !== 'SEM_HISTORICO'" class="flex shrink-0 gap-2 text-xs"><button type="button" class="rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-gray-600 hover:bg-gray-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#373435]" @click="expandirTudo">Expandir tudo</button><button type="button" class="rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-gray-600 hover:bg-gray-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#373435]" @click="recolherTudo">Recolher</button></div>
        </div>
        <div class="grid gap-3 border-b border-gray-100 bg-gray-50/70 px-4 py-3 xl:grid-cols-[minmax(0,1fr)_auto] xl:gap-0">
          <div class="min-w-0 xl:pr-4" role="group" aria-label="Período"><div class="flex flex-wrap items-end gap-3">
            <div class="flex flex-col gap-1"><span class="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Visão</span><div class="flex h-[34px] overflow-hidden rounded-md border border-gray-200 text-xs font-semibold"><button v-for="opcao in [{ valor: 'mensal', nome: 'Mensal' }, { valor: 'anual', nome: 'Anual' }]" :key="opcao.valor" type="button" class="px-3 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-[#373435]" :class="visao === opcao.valor ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" :aria-pressed="visao === opcao.valor" @click="mudarVisao(opcao.valor)">{{ opcao.nome }}</button></div></div>
            <label class="flex w-28 flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">Ano<select :value="ano" class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300" @change="mudarAno($event.target.value)"><option v-for="opcao in anos" :key="opcao" :value="opcao">{{ opcao }}</option></select></label>
            <label v-if="podeEquivaler" class="flex h-[34px] cursor-pointer items-center gap-2 rounded-md border border-gray-200 bg-white px-3 text-xs font-medium text-gray-600"><input type="checkbox" :checked="equivalente" class="accent-[#373435]" @change="mudarFiltros({ periodo_equivalente: $event.target.checked ? '1' : '0' })" />Períodos equivalentes</label>
          </div></div>
          <div class="min-w-0 border-t border-gray-200 pt-3 xl:border-l xl:border-t-0 xl:pl-4 xl:pt-0" role="group" aria-label="Leitura"><div class="flex flex-wrap items-end gap-3">
            <label class="flex min-w-[210px] flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">Analisar<select :value="base" class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium normal-case text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300" @change="mudarFiltros({ base: $event.target.value })"><option value="VENCIMENTO">Obrigações por vencimento</option><option value="PAGAMENTO">Saídas por pagamento</option></select></label>
            <button type="button" class="flex h-[34px] items-center gap-1.5 rounded-md border border-gray-200 bg-white px-3 text-xs font-medium text-gray-600 hover:bg-gray-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#373435] disabled:opacity-50" :disabled="carregando || !familiaId" @click="carregar"><RefreshCw class="h-3.5 w-3.5" aria-hidden="true" />Atualizar</button>
            <details v-if="dados" class="relative text-xs text-gray-600"><summary class="flex h-[34px] w-[34px] cursor-pointer list-none items-center justify-center rounded-md border border-gray-200 bg-white text-gray-500 hover:bg-gray-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#373435] [&::-webkit-details-marker]:hidden" aria-label="Detalhes técnicos da atualização" title="Detalhes técnicos da atualização"><Info class="h-4 w-4" aria-hidden="true" /></summary><div class="absolute right-0 z-30 mt-1 w-72 rounded-lg border border-gray-200 bg-white p-3 shadow-lg"><p class="font-semibold text-gray-800">Atualização dos dados</p><p class="mt-2">Agregado: {{ dataHora(dados.atualizado_em) }}</p><p>Fonte: {{ dados.fonte_atualizada_em ? dataHora(dados.fonte_atualizada_em) : 'data não informada' }}</p><p>Cobertura da fonte: {{ dados.cobertura_fonte_ate ? dataCurta(dados.cobertura_fonte_ate) : 'não informada' }}</p></div></details>
          </div></div>
        </div>
      </section>

      <div v-if="dados?.desatualizado" role="alert" class="flex items-start gap-2 border-b border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800"><AlertTriangle class="h-4 w-4 shrink-0" aria-hidden="true" />Há períodos com atualização falha ou pendente. As células afetadas não entram nas comparações.</div>
      <div v-if="semDiario" role="status" class="flex items-start gap-2 border-b border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800"><AlertTriangle class="h-4 w-4 shrink-0" aria-hidden="true" />O histórico diário ainda não foi carregado para todo o corte equivalente. Essas células aparecem como indisponíveis; desative o controle para consultar os agregados mensais existentes.</div>
      <div v-else-if="faltantes.length && dados?.estado_atualizacao !== 'SEM_HISTORICO'" role="status" class="border-b border-amber-100 bg-amber-50/70 px-4 py-2 text-xs text-amber-800">{{ faltantes.length }} {{ faltantes.length === 1 ? 'período necessário está indisponível' : 'períodos necessários estão indisponíveis' }}. Ausência de snapshot não equivale a zero.</div>
      <div v-if="dados?.periodo_equivalente && visao === 'mensal'" class="border-b border-gray-100 bg-gray-50/60 px-4 py-2 text-xs text-gray-600">Meses anteriores e mês atual comparados do dia 1 ao dia {{ Number(dados.data_corte?.slice(-2)) }}. Meses futuros de vencimento permanecem programados fora do Total comparável.</div>
      <div v-if="dados?.periodo_equivalente && visao === 'anual'" class="border-b border-gray-100 bg-gray-50/60 px-4 py-2 text-xs text-gray-600">Prévia até {{ dataCurta(dados.data_corte) }}; anos anteriores cortados no mesmo mês e dia.</div>
      <div v-if="dados?.ano_parcial && visao === 'anual' && !dados.periodo_equivalente" class="border-b border-amber-100 bg-amber-50/60 px-4 py-2 text-xs text-amber-800">Ano foco parcial. A taxa recente compara durações diferentes e é exibida sem juízo de desempenho.</div>
      <div v-if="visao === 'mensal' && dados?.mes_aberto && !dados.periodo_equivalente" class="border-b border-gray-100 bg-gray-50/60 px-4 py-2 text-xs text-gray-600">{{ base === 'VENCIMENTO' ? 'Mês atual pode incluir obrigações com vencimento nos próximos dias.' : 'Mês atual mostra pagamentos até hoje; registros com data futura ficam separados.' }}</div>
      <div v-if="dados?.estado_atualizacao !== 'SEM_HISTORICO' && base === 'VENCIMENTO' && (temValor(raiz?.programado_apos_corte) || dados?.programado_incompleto)" class="border-b border-blue-100 bg-blue-50/60 px-4 py-2 text-xs text-blue-900"><template v-if="raiz?.programado_apos_corte != null">Programado após o corte: <strong class="font-mono">{{ formatarValor(raiz.programado_apos_corte) }}</strong> · </template><template v-else>Programado após o corte ainda não disponível · </template>{{ dados.programado_incompleto ? 'valor conhecido parcial; faltam snapshots futuros ou o diário do mês atual.' : 'dados conhecidos na última atualização.' }}</div>
      
      <div v-if="carregando" role="status" class="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center"><div class="h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-[#373435]" /><div><p class="text-sm font-medium text-gray-700">Carregando análise</p><p class="mt-1 text-xs text-gray-400">Os valores vêm dos agregados já persistidos.</p></div></div>
      <div v-else-if="erro" role="alert" class="px-5 py-6 text-sm text-red-700">{{ erro }}</div>
      <div v-else-if="!familias.length" class="px-5 py-12 text-center text-sm text-gray-500">Nenhuma família cadastrada nesta filial.</div>
      <div v-else-if="dados?.estado_atualizacao === 'SEM_HISTORICO'" class="flex flex-col items-center justify-center px-6 py-14 text-center"><Layers3 class="mb-3 h-7 w-7 text-gray-300" aria-hidden="true" /><p class="text-sm font-medium text-gray-700">Sem histórico de despesas carregado</p><p class="mt-1 max-w-md text-xs text-gray-500">A estrutura de categorias existe, mas ainda não há snapshots oficiais desta base. Os períodos não são tratados como zero.</p></div>
      <div v-else-if="!linhas.length" class="px-5 py-12 text-center text-sm text-gray-500">Nenhuma categoria nesta família.</div>
      <div v-else class="app-scrollbar overflow-x-auto"><table class="w-full border-collapse text-xs"><thead><tr class="border-b border-gray-100 bg-white">
        <th scope="col" class="sticky left-0 z-20 min-w-[300px] bg-white px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-400 shadow-[1px_0_0_#f3f4f6]">Categoria</th>
        <th v-for="(periodo, indice) in periodos" :key="periodo.periodo" scope="col" class="min-w-[104px] px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider" :class="periodo.posicao_calendario === 'FUTURO' ? 'bg-slate-50 text-slate-500' : (indice === periodos.length - 1 && visao === 'anual') || periodo.posicao_calendario === 'CORRENTE' ? 'bg-gray-50 text-[#373435]' : 'text-gray-500'" :title="descricaoPeriodo(periodo)">{{ tituloPeriodo(periodo) }}<span v-if="rotuloPeriodo(periodo)" class="block font-normal normal-case tracking-normal" :class="periodo.estado_snapshot !== 'PRONTO' ? 'text-amber-700' : 'text-gray-500'">{{ rotuloPeriodo(periodo) }}</span></th>
        <th v-if="visao === 'mensal'" scope="col" class="min-w-[125px] bg-gray-50 px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-700">{{ raiz?.total_rotulo || 'Total' }}</th>
        <th v-else scope="col" class="min-w-[145px] bg-gray-50 px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-700" :title="tituloVariacoes">Variações<span class="block font-normal normal-case">Média / recente</span></th>
      </tr></thead><tbody>
        <tr v-for="linha in linhas" :id="`despesa-categoria-${linha.no.id}`" :key="linha.chave" class="border-b border-gray-50 last:border-0 hover:bg-gray-50/70" :class="[linha.nivel === 0 ? 'bg-gray-50/60 font-semibold' : '', Number(route.query.categoria_id) === linha.no.id ? 'ring-2 ring-inset ring-[#373435]/60' : '']">
          <td class="sticky left-0 z-10 bg-white px-4 py-2.5 shadow-[1px_0_0_#f3f4f6]" :class="linha.nivel === 0 ? '!bg-gray-50' : ''"><div class="flex min-w-0 items-center gap-1" :style="{ paddingLeft: `${linha.nivel * 18}px` }">
            <button v-if="linha.expansivel" type="button" class="flex h-5 w-5 shrink-0 items-center justify-center rounded text-gray-500 hover:bg-gray-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#373435]" :aria-label="`${expandidos.has(linha.no.id) ? 'Recolher' : 'Expandir'} ${linha.no.nome}`" :aria-expanded="expandidos.has(linha.no.id)" @click="alternar(linha.no.id)"><ChevronDown v-if="expandidos.has(linha.no.id)" class="h-3.5 w-3.5" aria-hidden="true" /><ChevronRight v-else class="h-3.5 w-3.5" aria-hidden="true" /></button><span v-else class="h-5 w-5 shrink-0" />
            <span class="min-w-0 truncate" :title="nomeCompleto(linha.no)" :class="linha.nivel === 0 ? 'text-[#373435]' : 'font-medium text-gray-700'">{{ linha.no.nome }}</span>
            <RouterLink v-if="linha.no.folha" :to="linkFolha(linha.no)" target="_blank" rel="noopener noreferrer" class="ml-auto flex h-6 w-6 shrink-0 items-center justify-center rounded text-gray-400 hover:bg-gray-200 hover:text-gray-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#373435]" :aria-label="`Analisar tipos da categoria ${linha.no.nome} em nova aba`" title="Abrir tipos em uma nova aba" @click.stop><ExternalLink class="h-3.5 w-3.5" aria-hidden="true" /></RouterLink>
          </div></td>
          <td v-for="(periodo, indice) in periodos" :key="periodo.periodo" class="px-3 py-2.5 text-right font-mono tabular-nums" :class="linha.no.valores[periodo.periodo] == null ? 'text-gray-300' : periodo.posicao_calendario === 'FUTURO' ? 'bg-slate-50 text-slate-600' : 'text-gray-700'" :style="estiloCelula(linha, linha.no.valores[periodo.periodo], indice)" :title="valorExato(linha.no.valores[periodo.periodo])"><RouterLink v-if="linha.no.folha && linha.no.valores[periodo.periodo] != null" :to="linkFolha(linha.no, periodo.periodo)" target="_blank" rel="noopener" class="rounded px-1 hover:bg-gray-200 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#373435]" :aria-label="`Analisar tipos de ${linha.no.nome} em ${tituloPeriodo(periodo)} em nova aba`">{{ formatarValor(linha.no.valores[periodo.periodo]) }}</RouterLink><template v-else>{{ formatarValor(linha.no.valores[periodo.periodo]) }}</template></td>
          <td v-if="visao === 'mensal'" class="bg-gray-50 px-3 py-2.5 text-right font-mono font-semibold tabular-nums text-gray-800" :title="linha.no.total_incompleto ? `Total indisponível; soma dos períodos conhecidos: ${formatarValor(linha.no.total_conhecido)}` : valorExato(linha.no.total)">{{ formatarValor(linha.no.total) }}</td>
          <td v-else class="bg-gray-50 px-3 py-2 text-right" :title="tituloVariacoes"><div class="whitespace-nowrap font-mono tabular-nums leading-4"><div class="text-[11px] font-bold text-gray-800">Média · {{ formatarVariacao(linha.no.variacao_historica_percentual) }}</div><div class="text-[10px] font-medium text-gray-600">Recente · {{ formatarVariacao(linha.no.variacao_percentual) }}</div></div></td>
        </tr>
      </tbody></table></div>
    </article>

    <details v-if="dados && naoClassificados?.quantidade_tipos && dados.estado_atualizacao !== 'SEM_HISTORICO'" class="overflow-hidden rounded-lg border border-gray-200 bg-white"><summary class="cursor-pointer px-4 py-3 text-xs font-semibold text-gray-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#373435]">Não classificados nesta família · {{ naoClassificados.quantidade_tipos }} {{ naoClassificados.quantidade_tipos === 1 ? 'tipo' : 'tipos' }} <span v-if="naoClassificados.tipos_com_vinculo_invalido?.length" class="font-normal text-amber-700">· {{ naoClassificados.tipos_com_vinculo_invalido.length }} com vínculo inválido</span></summary><div class="border-t border-gray-100 px-4 py-3 text-xs text-gray-600"><p>Estes valores estão fora da árvore selecionada. A soma deles com a raiz reproduz o total oficial da base em cada período disponível.</p><div class="app-scrollbar mt-3 overflow-x-auto"><table class="w-full border-collapse text-xs"><thead><tr class="text-gray-500"><th scope="col" class="min-w-[180px] py-2 text-left">Cobertura</th><th v-for="periodo in periodos" :key="periodo.periodo" scope="col" class="min-w-[95px] px-2 py-2 text-right">{{ tituloPeriodo(periodo) }}</th></tr></thead><tbody><tr class="border-t border-gray-100 font-mono"><th scope="row" class="py-2 text-left font-medium">Fora da família</th><td v-for="periodo in periodos" :key="periodo.periodo" class="px-2 py-2 text-right" :title="valorExato(naoClassificados.valores[periodo.periodo])">{{ formatarValor(naoClassificados.valores[periodo.periodo]) }}</td></tr></tbody></table></div></div></details>
  </div>
</template>
