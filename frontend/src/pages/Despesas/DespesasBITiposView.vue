<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { AlertTriangle, ArrowLeft, Info, RefreshCw, Search } from 'lucide-vue-next'
import RemoteSearchSelect from '@/components/ui/RemoteSearchSelect.vue'
import { MESES } from '@/pages/analise/analiseMensalUtils.js'
import { despesasApi } from '@/services/despesasApi.js'
import { filialAtiva } from '@/stores/filial.js'

const route = useRoute()
const router = useRouter()
const categorias = ref([])
const categoriasCarregadas = ref(false)
const dados = ref(null)
const total = ref(0)
const busca = ref(String(route.query.busca || ''))
const carregando = ref(false)
const erro = ref('')
let sequencia = 0
let sequenciaCategorias = 0
const hoje = new Date()
const anoAtual = hoje.getFullYear()
const visao = computed(() => route.query.visao === 'anual' ? 'anual' : 'mensal')
const base = computed(() => route.query.base === 'VENCIMENTO' ? 'VENCIMENTO' : 'PAGAMENTO')
const familiaId = computed(() => String(route.query.familia_id || ''))
const categoriaId = computed(() => String(route.query.categoria_id || route.query.folha_id || familiaId.value || ''))
const familias = computed(() => categorias.value.filter((item) => item.pai == null))
const categoriaAtual = computed(() => categorias.value.find((item) => String(item.id) === categoriaId.value))
const categoriaControle = computed({
  get: () => categoriaId.value === familiaId.value ? '' : categoriaId.value,
  set: (valor) => mudarCategoria(valor),
})
const categoriasEndpoint = computed(() => `${filialAtiva.value.apiUrl}/api/despesas/categorias/`)
const ano = computed(() => Number(route.query.ano) || anoAtual)
const equivalente = computed(() => String(route.query.periodo_equivalente || '0') === '1')
const periodos = computed(() => dados.value?.periodos || [])
const tipos = computed(() => dados.value?.tipos || [])
const categoriaExibida = computed(() => dados.value?.categoria || dados.value?.folha || null)
const foco = computed(() => String(route.query.periodo || (visao.value === 'anual' ? ano.value : `${ano.value}-${String(hoje.getMonth() + 1).padStart(2, '0')}-01`)))
const anos = computed(() => [...new Set([anoAtual, ano.value, ...(dados.value?.anos_disponiveis || [])])].sort((a, b) => b - a))
const podeEquivaler = computed(() => ano.value === anoAtual && (visao.value === 'anual' ? dados.value?.ano_parcial : dados.value?.mes_aberto))
const retorno = computed(() => ({ path: '/analise/despesas', query: { familia_id: familiaId.value, ...(categoriaId.value !== familiaId.value ? { categoria_id: categoriaId.value } : {}), visao: visao.value, base: base.value, ano: String(ano.value), periodo_equivalente: equivalente.value ? '1' : '0' } }))

function mudar(alteracoes) { router.push({ query: { ...route.query, page: '1', ...alteracoes } }) }
function mudarFamilia(nova) { mudar({ familia_id: String(nova), categoria_id: undefined, folha_id: undefined }) }
function mudarCategoria(nova) { mudar({ categoria_id: nova ? String(nova) : undefined, folha_id: undefined }) }
function rotuloCategoria(item) { return String(item?.caminho || item?.nome || '').split('\x1f').join(' › ') }
function mudarVisao(nova) { mudar({ visao: nova, periodo: nova === 'anual' ? String(ano.value) : `${ano.value}-${String(hoje.getMonth() + 1).padStart(2, '0')}-01`, periodo_equivalente: nova === 'anual' && ano.value === anoAtual ? '1' : '0' }) }
function mudarAno(novo) { mudar({ ano: String(novo), periodo: visao.value === 'anual' ? String(novo) : `${novo}-${String(Number(novo) === anoAtual ? hoje.getMonth() + 1 : 12).padStart(2, '0')}-01`, periodo_equivalente: visao.value === 'anual' && Number(novo) === anoAtual ? '1' : '0' }) }
function periodoNome(p) { return visao.value === 'anual' ? p.periodo : MESES[Number(p.periodo.slice(5, 7)) - 1] }
function numero(valor) { return valor == null || !Number.isFinite(Number(valor)) ? '—' : Number(valor).toLocaleString('pt-BR', { maximumFractionDigits: 0 }) }
function exato(valor) { return valor == null ? 'Indisponível' : Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function percentual(valor) { return valor == null ? '—' : `${Number(valor) > 0 ? '+' : ''}${Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%` }
function dataBR(valor) { return valor ? String(valor).slice(0, 10).split('-').reverse().join('/') : '—' }
function linkMovimentos(tipo, periodo) { return { path: '/despesas/movimentos', query: {
  bi: '1', familia_id: familiaId.value, folha_id: tipo.folha_id,
  tipos_categoria_id: categoriaId.value,
  tipos_busca: route.query.busca || undefined, tipos_page: route.query.page || undefined,
  tipo_id: tipo.id, visao: visao.value, base: base.value, ano: String(ano.value),
  periodo_equivalente: equivalente.value ? '1' : '0', periodo: periodo.periodo,
} } }

async function carregar() {
  if (!categoriasCarregadas.value || !familias.value.some((item) => String(item.id) === familiaId.value)) return
  const atual = ++sequencia
  carregando.value = true
  erro.value = ''
  busca.value = String(route.query.busca || '')
  try {
    const params = new URLSearchParams({ familia_id: familiaId.value, visao: visao.value, base: base.value, ano: String(ano.value), periodo_equivalente: equivalente.value ? '1' : '0', busca: String(route.query.busca || ''), page: String(route.query.page || '1') })
    if (route.query.categoria_id) params.set('categoria_id', String(route.query.categoria_id))
    else if (route.query.folha_id) params.set('folha_id', String(route.query.folha_id))
    const resposta = await despesasApi(`bi/tipos/?${params}`)
    if (atual === sequencia) { dados.value = resposta.results; total.value = resposta.count || 0 }
  } catch (e) { if (atual === sequencia) { dados.value = null; total.value = 0; erro.value = e.message } }
  finally { if (atual === sequencia) carregando.value = false }
}
async function carregarCategorias(nomePreferido = '', trocaFilial = false) {
  const atual = ++sequenciaCategorias
  categoriasCarregadas.value = false
  carregando.value = true
  erro.value = ''
  ++sequencia
  dados.value = null
  try {
    const lista = await despesasApi('categorias/')
    if (atual !== sequenciaCategorias) return
    categorias.value = lista
    const raizes = lista.filter((item) => item.pai == null)
    const familia = (nomePreferido && raizes.find((item) => item.nome === nomePreferido))
      || (!trocaFilial && raizes.find((item) => String(item.id) === familiaId.value))
      || raizes.find((item) => item.nome.toUpperCase() === 'DESPESAS') || raizes[0]
    if (!familia) { carregando.value = false; erro.value = 'Nenhuma família de despesas cadastrada nesta filial.'; return }
    const selecionada = !trocaFilial && lista.find((item) => String(item.id) === categoriaId.value
      && (item.caminho === familia.caminho || item.caminho.startsWith(`${familia.caminho}\x1f`)))
    categoriasCarregadas.value = true
    const query = {
      ...route.query, familia_id: String(familia.id),
      categoria_id: selecionada && route.query.categoria_id ? String(selecionada.id) : undefined,
      folha_id: selecionada && route.query.folha_id && !route.query.categoria_id ? String(selecionada.id) : undefined,
      page: trocaFilial ? '1' : route.query.page,
    }
    if (JSON.stringify(query) !== JSON.stringify(route.query)) await router.replace({ query })
    else carregar()
  } catch (e) { if (atual === sequenciaCategorias) { carregando.value = false; erro.value = e.message } }
}
watch(() => route.fullPath, carregar)
watch(() => filialAtiva.value.id, () => {
  const nome = familias.value.find((item) => String(item.id) === familiaId.value)?.nome || ''
  carregarCategorias(nome, true)
})
onMounted(() => carregarCategorias())
onUnmounted(() => { ++sequencia; ++sequenciaCategorias })
</script>

<template>
  <div class="flex w-full min-w-0 flex-col gap-5 text-[#373435]">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div><h1 class="text-xl font-bold text-gray-900">Despesas por Tipo</h1><p class="mt-0.5 text-sm text-gray-400">{{ categoriaExibida?.nome || 'Tipos da família' }} · obrigações ou saídas no mesmo recorte da matriz.</p></div>
      <RouterLink :to="retorno" class="flex h-[34px] items-center gap-1.5 rounded-md border border-gray-200 bg-white px-3 text-xs font-semibold text-gray-700 hover:bg-gray-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#373435]"><ArrowLeft class="h-3.5 w-3.5" aria-hidden="true" />Por Categoria</RouterLink>
    </header>

    <article class="w-full min-w-0 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <div class="flex flex-wrap items-end gap-3 border-b border-gray-100 bg-gray-50/70 px-4 py-3">
        <label class="flex min-w-[170px] flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">Família<select :value="familiaId" class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium normal-case" @change="mudarFamilia($event.target.value)"><option v-for="item in familias" :key="item.id" :value="item.id">{{ item.nome }}</option></select></label>
        <div class="flex min-w-[220px] flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500"><span>Categoria</span><RemoteSearchSelect v-model="categoriaControle" :endpoint="categoriasEndpoint" value-field="id" :format-option-label="rotuloCategoria" all-label="Toda a família" search-placeholder="Pesquisar categoria" :extra-params="{ familia_id: familiaId }" :initial-label="categoriaAtual && categoriaId !== familiaId ? rotuloCategoria(categoriaAtual) : ''" :disabled="!categoriasCarregadas || !familiaId" button-class="flex h-[34px] w-full items-center justify-between gap-2 rounded-md border border-gray-200 bg-white px-3 text-xs font-medium normal-case text-gray-700 hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#373435]" /></div>
        <div class="flex flex-col gap-1"><span class="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Visão</span><div class="flex h-[34px] overflow-hidden rounded-md border border-gray-200 text-xs font-semibold"><button v-for="opcao in [{ valor: 'mensal', nome: 'Mensal' }, { valor: 'anual', nome: 'Anual' }]" :key="opcao.valor" type="button" class="px-3 focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-[#373435]" :class="visao === opcao.valor ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" :aria-pressed="visao === opcao.valor" @click="mudarVisao(opcao.valor)">{{ opcao.nome }}</button></div></div>
        <label class="flex w-28 flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">Ano<select :value="ano" class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium" @change="mudarAno($event.target.value)"><option v-for="opcao in anos" :key="opcao" :value="opcao">{{ opcao }}</option></select></label>
        <label class="flex min-w-[205px] flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">Analisar<select :value="base" class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium normal-case" @change="mudar({ base: $event.target.value })"><option value="VENCIMENTO">Obrigações por vencimento</option><option value="PAGAMENTO">Saídas por pagamento</option></select></label>
        <label v-if="podeEquivaler" class="flex h-[34px] cursor-pointer items-center gap-2 rounded-md border border-gray-200 bg-white px-3 text-xs font-medium text-gray-600"><input type="checkbox" :checked="equivalente" class="accent-[#373435]" @change="mudar({ periodo_equivalente: $event.target.checked ? '1' : '0' })" />Períodos equivalentes</label>
        <button type="button" class="flex h-[34px] items-center gap-1.5 rounded-md border border-gray-200 bg-white px-3 text-xs text-gray-600 hover:bg-gray-100 focus-visible:outline focus-visible:outline-2 disabled:opacity-50" :disabled="carregando" @click="carregar"><RefreshCw class="h-3.5 w-3.5" aria-hidden="true" />Atualizar</button>
        <details v-if="dados" class="relative text-xs text-gray-600"><summary class="flex h-[34px] w-[34px] cursor-pointer list-none items-center justify-center rounded-md border border-gray-200 bg-white [&::-webkit-details-marker]:hidden" aria-label="Detalhes dos períodos" title="Detalhes dos períodos"><Info class="h-4 w-4" aria-hidden="true" /></summary><div class="absolute right-0 z-30 mt-1 w-72 rounded-lg border border-gray-200 bg-white p-3 shadow-lg">Cada célula abre os lançamentos ou pagamentos nas datas que formaram seu agregado. Valores indisponíveis não são tratados como zero.</div></details>
      </div>
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-4 py-3">
        <form class="flex items-center gap-2 rounded-md border border-gray-200 px-2 py-1.5" @submit.prevent="mudar({ busca })"><Search class="h-4 w-4 text-gray-400" aria-hidden="true" /><input v-model="busca" class="w-52 bg-transparent text-xs outline-none" placeholder="Buscar tipo de despesa" aria-label="Buscar tipo de despesa" /><button class="text-xs font-semibold text-gray-600 hover:underline">Buscar</button></form>
        <span v-if="dados" class="text-xs text-gray-500">{{ Number(route.query.page || 1) }}ª página · {{ categoriaExibida?.nome || 'Família' }} · {{ dados.estado_atualizacao === 'PRONTO' ? 'atualizado' : dados.estado_atualizacao }}</span>
      </div>
      <div v-if="dados?.desatualizado" role="alert" class="flex gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800"><AlertTriangle class="h-4 w-4 shrink-0" aria-hidden="true" />Há períodos com atualização falha ou pendente.</div>
      <div v-else-if="dados?.estado_atualizacao === 'INCOMPLETO' || dados?.estado_atualizacao === 'SEM_HISTORICO'" role="status" class="flex gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800"><AlertTriangle class="h-4 w-4 shrink-0" aria-hidden="true" />Há períodos sem snapshot de {{ base === 'PAGAMENTO' ? 'pagamentos' : 'obrigações' }}. Valores indisponíveis não entram como zero.</div>
      <div v-if="dados?.periodo_equivalente" class="border-b border-gray-100 bg-gray-50 px-4 py-2 text-xs text-gray-600">{{ visao === 'mensal' ? `Meses comparados até o dia ${Number(dados.data_corte?.slice(-2))}.` : `Anos comparados até ${dataBR(dados.data_corte)}.` }}</div>
      <div v-if="carregando" role="status" class="px-5 py-12 text-center text-sm text-gray-500">Carregando tipos…</div>
      <div v-else-if="erro" role="alert" class="px-5 py-6 text-sm text-red-700">{{ erro }}</div>
      <div v-else-if="!tipos.length" class="px-5 py-12 text-center text-sm text-gray-500">Nenhum tipo encontrado neste recorte.</div>
      <div v-else class="app-scrollbar overflow-x-auto"><table class="w-full border-collapse text-xs"><thead><tr class="border-b border-gray-100">
        <th scope="col" class="sticky left-0 z-20 min-w-[260px] bg-white px-4 py-3 text-left text-[10px] uppercase tracking-wider text-gray-400">Tipo de Despesa</th>
        <th v-for="p in periodos" :key="p.periodo" scope="col" class="min-w-[105px] px-3 py-3 text-right text-[10px] uppercase tracking-wider" :class="p.periodo === foco ? 'bg-gray-100 text-gray-800' : 'text-gray-500'" :title="`${dataBR(p.inicio)} a ${dataBR(p.fim_efetivo || p.fim)} · ${p.estado}`"><button type="button" class="rounded px-1 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#373435]" :aria-pressed="p.periodo === foco" :aria-label="`Selecionar ${periodoNome(p)} como período foco`" @click="mudar({ periodo: p.periodo })">{{ periodoNome(p) }}</button><span v-if="p.estado !== 'PRONTO'" class="block font-normal normal-case">{{ p.estado === 'PARCIAL' ? 'Prévia' : p.estado === 'FUTURO' ? 'Futuro' : 'Indisponível' }}</span></th>
        <th scope="col" class="min-w-[125px] bg-gray-50 px-3 py-3 text-right text-[10px] uppercase tracking-wider text-gray-700">{{ visao === 'mensal' ? categoriaExibida?.total_rotulo || 'Total' : 'Variações' }}</th>
      </tr></thead><tbody><tr v-for="tipo in tipos" :key="tipo.id" class="border-b border-gray-50 hover:bg-gray-50/70"><th scope="row" class="sticky left-0 z-10 bg-white px-4 py-2.5 text-left font-medium shadow-[1px_0_0_#f3f4f6]">{{ tipo.nome }}</th>
        <td v-for="p in periodos" :key="p.periodo" class="px-3 py-2.5 text-right font-mono tabular-nums" :class="p.periodo === foco ? 'bg-gray-50 font-semibold' : ''" :title="exato(tipo.valores[p.periodo])"><RouterLink v-if="tipo.valores[p.periodo] != null" :to="linkMovimentos(tipo, p)" target="_blank" rel="noopener" class="rounded px-1 hover:bg-gray-200 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#373435]" :aria-label="`Ver movimentações de ${tipo.nome} em ${periodoNome(p)} em nova aba`">{{ numero(tipo.valores[p.periodo]) }}</RouterLink><span v-else class="text-gray-300">—</span></td>
        <td v-if="visao === 'mensal'" class="bg-gray-50 px-3 py-2.5 text-right font-mono font-semibold">{{ numero(tipo.total) }}</td><td v-else class="bg-gray-50 px-3 py-2 text-right font-mono leading-4"><div class="text-[11px] font-bold">Média · {{ percentual(tipo.variacao_historica_percentual) }}</div><div class="text-[10px] text-gray-600">Recente · {{ percentual(tipo.variacao_percentual) }}</div></td>
      </tr></tbody></table></div>
      <div v-if="dados" class="flex items-center justify-between border-t border-gray-100 px-4 py-3 text-xs text-gray-500"><span>{{ total }} tipos · {{ categoriaExibida?.nome || 'Família' }}: {{ numero(categoriaExibida?.valores?.[foco]) }} no período em foco</span><div class="flex gap-2"><button type="button" class="rounded border px-3 py-1.5 disabled:opacity-40" :disabled="Number(route.query.page || 1) <= 1" @click="mudar({ page: String(Number(route.query.page || 1) - 1) })">Anterior</button><button type="button" class="rounded border px-3 py-1.5 disabled:opacity-40" :disabled="Number(route.query.page || 1) * 100 >= total" @click="mudar({ page: String(Number(route.query.page || 1) + 1) })">Próxima</button></div></div>
    </article>
  </div>
</template>
