<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { AlertTriangle, ExternalLink, Layers3, RefreshCw } from 'lucide-vue-next'
import { getApiBaseUrl } from '@/services/firebirdSync'
import SnapshotDetails from './SnapshotDetails.vue'
import VariacoesCompactas from './VariacoesCompactas.vue'
import QuarentenaBotao from './QuarentenaBotao.vue'
import {
  MESES, estiloCelulaFinanceira, formatarQuantidade, formatarValor,
  indicesIgnoradosMesAberto, mapaQuartis, mesEstaAberto, tooltipMesAberto,
} from './analiseMensalUtils'

const api = getApiBaseUrl()
const endpoint = `${api}/api/analise/categorias/vendas/quarentena/`
const metadados = `${api}/api/analise/categorias/vendas/`
const route = useRoute()
const router = useRouter()

const visao = ref(['semanal', 'mensal', 'anual'].includes(route.query.visao) ? route.query.visao : 'semanal')
const metrica = ref(['valor', 'quantidade'].includes(route.query.metrica) ? route.query.metrica : 'valor')
const raizId = ref(String(route.query.raiz_id || ''))
const ano = ref(Number(route.query.ano) || null)
const semana = ref(String(route.query.semana_inicio || ''))
const equivalenteSemanal = ref(!['0', 'false'].includes(String(route.query.periodo_equivalente || '1').toLowerCase()))
const equivalenteMensal = ref(['1', 'true'].includes(String(route.query.periodo_equivalente || '').toLowerCase()) && visao.value === 'mensal')
const equivalenteAnual = ref(!['0', 'false'].includes(String(route.query.periodo_equivalente || '1').toLowerCase()))
const familias = ref([])
const anosMensais = ref([])
const anosAnuais = ref([])
const semanas = ref([])
const atualizadoSemanalEm = ref(null)
const ultimaVendaMensal = ref(null)
const grupos = ref([])
const totalCategorias = ref(0)
const carregando = ref(false)
const pronto = ref(false)
const erro = ref('')
const erroAcao = ref('')
const removendo = ref(new Set())
let sequencia = 0
let intervalo = null

const anosDisponiveis = computed(() => visao.value === 'anual' ? anosAnuais.value : anosMensais.value)
const equivalente = computed(() => visao.value === 'semanal' ? equivalenteSemanal.value : visao.value === 'anual' ? equivalenteAnual.value : equivalenteMensal.value)
const mesAberto = computed(() => {
  if (!ultimaVendaMensal.value || ano.value !== new Date().getFullYear()) return false
  const data = new Date(`${ultimaVendaMensal.value}T12:00:00`)
  return data.getDate() < new Date(data.getFullYear(), data.getMonth() + 1, 0).getDate()
})

function dataCurta(valor) {
  if (!valor) return ''
  const [anoValor, mes, dia] = valor.split('-')
  return `${dia}/${mes}/${anoValor}`
}

function rotuloSemana(inicio) {
  const fim = new Date(`${inicio}T12:00:00`)
  fim.setDate(fim.getDate() + 6)
  return `${dataCurta(inicio)} a ${fim.toLocaleDateString('pt-BR')}`
}

function parametros() {
  const params = new URLSearchParams({
    visao: visao.value, metrica: metrica.value,
    periodo_equivalente: equivalente.value ? '1' : '0',
  })
  if (raizId.value) params.set('raiz_id', raizId.value)
  if (visao.value === 'semanal') params.set('semana_inicio', semana.value)
  else params.set('ano', String(ano.value))
  return params
}

function sincronizarUrl() {
  const query = {
    visao: visao.value,
    metrica: metrica.value,
    periodo_equivalente: equivalente.value ? '1' : '0',
  }
  if (raizId.value) query.raiz_id = raizId.value
  if (visao.value === 'semanal' && semana.value) query.semana_inicio = semana.value
  if (visao.value !== 'semanal' && ano.value) query.ano = String(ano.value)
  router.replace({ query })
}

async function carregarOpcoes() {
  try {
    const [resFamilias, resMensal, resSemanal, resAnual] = await Promise.all([
      fetch(`${api}/api/cadastros/plano-contas/raizes`),
      fetch(metadados), fetch(`${metadados}semanal/`), fetch(`${metadados}anual/`),
    ])
    if (![resFamilias, resMensal, resSemanal, resAnual].every((res) => res.ok)) throw new Error('Não foi possível carregar os períodos da análise.')
    familias.value = await resFamilias.json()
    const metadataMensal = await resMensal.json()
    anosMensais.value = metadataMensal.anos_disponiveis ?? []
    const metadataSemanal = await resSemanal.json()
    semanas.value = metadataSemanal.semanas_disponiveis ?? []
    atualizadoSemanalEm.value = metadataSemanal.atualizado_em
    ultimaVendaMensal.value = metadataSemanal.ultima_data_disponivel
    anosAnuais.value = (await resAnual.json()).anos_disponiveis ?? []
    if (raizId.value && !familias.value.some((familia) => String(familia.id_conta) === raizId.value)) raizId.value = ''
    if (!semanas.value.includes(semana.value)) semana.value = metadataSemanal.semana_inicial ?? semanas.value[0] ?? ''
    if (!anosDisponiveis.value.includes(ano.value)) ano.value = anosDisponiveis.value[0] ?? null
    pronto.value = true
    await carregarMatriz()
  } catch (e) {
    erro.value = e?.message || 'Falha ao carregar a quarentena.'
  }
}

async function carregarMatriz() {
  const atual = ++sequencia
  if (!pronto.value || (visao.value === 'semanal' ? !semana.value : !ano.value)) {
    grupos.value = []
    return
  }
  carregando.value = true
  erro.value = ''
  try {
    const resposta = await fetch(`${endpoint}matriz/?${parametros()}`)
    const payload = await resposta.json().catch(() => ({}))
    if (atual !== sequencia) return
    if (!resposta.ok) throw new Error(payload.detail || 'Falha ao consultar as categorias em quarentena.')
    grupos.value = payload.grupos ?? []
    totalCategorias.value = payload.total_categorias ?? 0
  } catch (e) {
    if (atual === sequencia) erro.value = e?.message || 'Falha ao consultar a quarentena.'
  } finally {
    if (atual === sequencia) carregando.value = false
  }
}

async function verificarAtualizacao() {
  if (visao.value !== 'semanal' || !pronto.value) return
  try {
    const resposta = await fetch(`${metadados}semanal/`)
    if (!resposta.ok) return
    const metadata = await resposta.json()
    const semanaMaisRecente = semanas.value[0]
    const mudou = atualizadoSemanalEm.value !== metadata.atualizado_em
    semanas.value = metadata.semanas_disponiveis ?? []
    atualizadoSemanalEm.value = metadata.atualizado_em
    if (semana.value === semanaMaisRecente && metadata.semana_inicial !== semana.value) {
      semana.value = metadata.semana_inicial ?? semanas.value[0] ?? ''
    } else if (mudou) carregarMatriz()
  } catch { /* O botão Atualizar continua disponível. */ }
}

watch([visao, metrica, raizId, ano, semana, equivalenteSemanal, equivalenteMensal, equivalenteAnual], () => {
  if (!pronto.value) return
  if (visao.value !== 'semanal' && !anosDisponiveis.value.includes(ano.value)) ano.value = anosDisponiveis.value[0] ?? null
  sincronizarUrl()
  carregarMatriz()
})

function quandoFocar() { carregarMatriz() }
onMounted(() => {
  carregarOpcoes()
  window.addEventListener('focus', quandoFocar)
  intervalo = window.setInterval(verificarAtualizacao, 60000)
})
onUnmounted(() => {
  window.removeEventListener('focus', quandoFocar)
  window.clearInterval(intervalo)
  sequencia += 1
})

async function removerCategoria(item) {
  const id = item.id_conta
  if (removendo.value.has(id)) return
  removendo.value = new Set([...removendo.value, id])
  erroAcao.value = ''
  try {
    const resposta = await fetch(`${endpoint}${id}/`, { method: 'DELETE' })
    if (!resposta.ok) throw new Error('Não foi possível remover a categoria da quarentena.')
    await carregarMatriz()
  } catch (e) {
    erroAcao.value = e?.message || 'Falha ao remover categoria.'
  } finally {
    const novas = new Set(removendo.value)
    novas.delete(id)
    removendo.value = novas
  }
}

function queryRecorte(grupo, categoriaId = null) {
  const query = {
    raiz_id: String(grupo.familia.id_conta),
    metrica: metrica.value,
    periodo_equivalente: equivalente.value ? '1' : '0',
    ...(visao.value === 'semanal' ? { visao: 'semanal', semana_inicio: semana.value } : { ano: String(ano.value) }),
    ...(visao.value === 'anual' ? { visao: 'anual' } : {}),
  }
  if (categoriaId) query.categoria_id = String(categoriaId)
  return query
}

function abrirProdutos(grupo, linha) {
  const destino = router.resolve({ name: 'analise-categorias-produtos-vendas', query: queryRecorte(grupo, linha.id_conta) })
  const aba = window.open(destino.href, '_blank', 'noopener,noreferrer')
  if (aba) aba.opener = null
}

function tituloAnual(dados) {
  const anos = dados.anos?.map((item) => item.ano) ?? []
  const historicas = anos.slice(0, -2).map((valor, indice) => `${valor}→${anos[indice + 1]}`)
  return `Média: ${historicas.length ? historicas.join(' e ') : 'indisponível'}. Recente: ${anos.length > 1 ? `${anos.at(-2)}→${anos.at(-1)}` : 'indisponível'}.`
}

function estiloLinha(dados, linha, valor, indice) {
  const ignorados = visao.value === 'mensal'
    ? (dados.periodo_equivalente ? [] : indicesIgnoradosMesAberto(dados))
    : visao.value === 'anual'
      ? (dados.ano_parcial && !dados.periodo_equivalente ? [linha.valores.length - 1] : [])
      : (dados.semana_parcial && !dados.periodo_equivalente ? [5] : [])
  const neutra = visao.value === 'mensal'
    ? !dados.periodo_equivalente && mesEstaAberto(dados, indice)
    : visao.value === 'anual'
      ? dados.ano_parcial && !dados.periodo_equivalente && indice === dados.anos.length - 1
      : dados.semana_parcial && !dados.periodo_equivalente && indice === 5
  return estiloCelulaFinanceira(mapaQuartis(linha.valores ?? [], ignorados), valor, false, neutra)
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <div>
      <h1 class="text-xl font-bold text-gray-900">Categorias em quarentena</h1>
      <p class="mt-0.5 text-sm text-gray-400">Folhas marcadas para acompanhamento nesta filial. A marcação não altera as vendas.</p>
    </div>

    <div class="rounded-xl border border-gray-200 bg-white shadow-sm">
      <div class="flex flex-wrap items-end gap-3 border-b border-gray-100 bg-gray-50/70 px-4 py-3">
        <label class="flex min-w-[220px] flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
          Família
          <select v-model="raizId" class="h-[34px] rounded-md border border-gray-200 bg-white px-2 text-xs font-medium normal-case text-gray-700">
            <option value="">Todas as famílias</option>
            <option v-for="familia in familias" :key="familia.id_conta" :value="String(familia.id_conta)">{{ familia.codigo_hierarquico }} {{ familia.nome_conta }}</option>
          </select>
        </label>
        <div class="flex flex-col gap-1">
          <span class="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Visão</span>
          <div class="flex h-[34px] overflow-hidden rounded-md border border-gray-200 text-xs font-semibold">
            <button v-for="modo in ['semanal', 'mensal', 'anual']" :key="modo" type="button" class="px-3 capitalize transition-colors" :class="visao === modo ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" :aria-pressed="visao === modo" @click="visao = modo">{{ modo }}</button>
          </div>
        </div>
        <label v-if="visao === 'semanal'" class="flex min-w-[200px] flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
          Semana de referência
          <select v-model="semana" class="h-[34px] rounded-md border border-gray-200 bg-white px-2 text-xs font-medium normal-case text-gray-700">
            <option v-for="inicio in semanas" :key="inicio" :value="inicio">{{ rotuloSemana(inicio) }}</option>
          </select>
        </label>
        <label v-else class="flex flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
          Ano
          <select v-model.number="ano" class="h-[34px] rounded-md border border-gray-200 bg-white px-2 text-xs font-medium normal-case text-gray-700">
            <option v-for="item in anosDisponiveis" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label v-if="visao !== 'mensal' || mesAberto" class="flex h-[34px] items-center gap-1.5 rounded-md border border-gray-200 bg-white px-2 text-xs text-gray-700">
          <input v-if="visao === 'semanal'" v-model="equivalenteSemanal" type="checkbox" />
          <input v-else-if="visao === 'anual'" v-model="equivalenteAnual" type="checkbox" />
          <input v-else v-model="equivalenteMensal" type="checkbox" />
          Períodos equivalentes
        </label>
        <div class="flex flex-col gap-1">
          <span class="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Métrica</span>
          <div class="flex h-[34px] overflow-hidden rounded-md border border-gray-200 text-xs font-semibold">
            <button type="button" class="px-3" :class="metrica === 'valor' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500'" :aria-pressed="metrica === 'valor'" @click="metrica = 'valor'">Valores financeiros</button>
            <button type="button" class="border-l border-gray-200 px-3" :class="metrica === 'quantidade' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500'" :aria-pressed="metrica === 'quantidade'" @click="metrica = 'quantidade'">Quantidades</button>
          </div>
        </div>
        <button type="button" class="flex h-[34px] items-center gap-1.5 rounded-md border border-gray-200 bg-white px-3 text-xs text-gray-600 hover:bg-gray-100" @click="carregarMatriz"><RefreshCw class="h-3.5 w-3.5" /> Atualizar</button>
      </div>

      <div v-if="erro || erroAcao" class="border-b border-red-100 bg-red-50 px-4 py-3 text-xs text-red-700" role="alert">{{ erro || erroAcao }}</div>
      <div v-if="!pronto || carregando" class="px-4 py-14 text-center text-sm text-gray-500" role="status">Carregando categorias em quarentena...</div>
      <div v-else-if="!totalCategorias" class="px-4 py-14 text-center text-sm text-gray-500">Nenhuma categoria em quarentena neste filtro. Marque uma folha em Vendas por Categoria para acompanhá-la aqui.</div>

      <div v-for="grupo in grupos" :key="grupo.familia.id_conta" class="border-t border-gray-200 first:border-t-0">
        <div class="flex flex-wrap items-center justify-between gap-2 bg-slate-50 px-4 py-3">
          <div class="flex items-center gap-2 text-sm font-semibold text-gray-800"><Layers3 class="h-4 w-4" /> {{ grupo.familia.codigo_hierarquico }} {{ grupo.familia.nome_conta }} <span class="text-xs font-normal text-gray-500">({{ grupo.categorias.length }})</span></div>
          <SnapshotDetails v-if="grupo.dados" :ultima-venda="grupo.dados.ultima_data_disponivel" :atualizado-em="grupo.dados.atualizado_em" />
        </div>
        <div v-if="grupo.erro" class="border-t border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800" role="status">
          <p class="font-semibold">Dados indisponíveis nesta família: {{ grupo.erro.detail }}</p>
          <div v-for="item in grupo.categorias.filter((categoria) => categoria.folha_valida)" :key="item.id_conta" class="mt-2 flex items-center gap-2">
            <span>{{ item.codigo_hierarquico }} {{ item.nome_conta }}</span>
            <QuarentenaBotao :nome="item.nome_conta" :marcada="true" :ocupada="removendo.has(item.id_conta)" @toggle="removerCategoria(item)" />
            <RouterLink :to="{ name: 'analise-categorias-vendas', query: queryRecorte(grupo, item.id_conta) }" class="rounded p-1 text-amber-800 hover:bg-amber-100" :aria-label="`Localizar ${item.nome_conta} na análise completa`" title="Localizar na análise completa"><Layers3 class="h-3.5 w-3.5" /></RouterLink>
          </div>
        </div>
        <div v-if="grupo.dados?.desatualizado" class="flex items-center gap-2 border-t border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800"><AlertTriangle class="h-4 w-4" /> Existem períodos aguardando atualização; os últimos snapshots válidos continuam visíveis.</div>
        <div v-if="grupo.dados && visao === 'semanal' && (grupo.dados.semana_parcial || grupo.dados.periodos_considerados_20 < 20 || grupo.dados.periodos_considerados_5 < 5)" class="border-t border-gray-100 px-4 py-2 text-xs text-gray-600">
          <span v-if="grupo.dados.semana_parcial">Prévia até {{ dataCurta(grupo.dados.semanas?.[5]?.data_corte) }}{{ grupo.dados.periodo_equivalente ? '; referências cortadas no mesmo dia da semana.' : '; comparação com semanas anteriores completas.' }}</span>
          <span v-if="grupo.dados.periodos_considerados_20 < 20 || grupo.dados.periodos_considerados_5 < 5" class="ml-1">Histórico: {{ grupo.dados.periodos_considerados_20 }}/20 semanas (últimas cinco: {{ grupo.dados.periodos_considerados_5 }}/5).</span>
        </div>
        <div v-if="grupo.dados && visao === 'mensal' && grupo.dados.periodo_equivalente" class="border-t border-gray-100 px-4 py-2 text-xs text-gray-600">Meses comparados do dia 1 ao dia {{ grupo.dados.dia_corte }}; o total soma apenas os valores exibidos.</div>
        <div v-if="grupo.dados && visao === 'anual' && grupo.dados.ano_parcial" class="border-t border-gray-100 px-4 py-2 text-xs text-gray-600">Prévia até {{ dataCurta(grupo.dados.anos?.at(-1)?.fim) }}{{ grupo.dados.periodo_equivalente ? '; anos anteriores cortados no mesmo mês e dia.' : '; comparação recente com ano anterior completo.' }}</div>

        <div v-if="grupo.dados?.linhas?.length" class="app-scrollbar overflow-x-auto">
          <table class="w-full border-collapse text-xs">
            <thead><tr class="border-b border-gray-100 bg-white">
              <th class="sticky left-0 z-20 min-w-[285px] bg-white px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-500">Categoria folha</th>
              <template v-if="visao === 'semanal'">
                <th class="min-w-[125px] bg-gray-50 px-3 py-3 text-right text-[10px] uppercase text-gray-600">Média 20 semanas</th>
                <th v-for="(periodo, indice) in grupo.dados.semanas" :key="periodo.inicio" class="min-w-[120px] px-3 py-3 text-right text-[10px] uppercase" :class="indice === 5 ? 'bg-gray-50 text-gray-800' : 'text-gray-400'" :title="`${dataCurta(periodo.inicio)} a ${dataCurta(periodo.fim)}${periodo.data_corte ? ` · até ${dataCurta(periodo.data_corte)}` : ''}`"><span v-if="indice === 5" class="block">Semana foco</span>{{ dataCurta(periodo.inicio).slice(0, 5) }}–{{ dataCurta(periodo.fim).slice(0, 5) }}</th>
                <th class="min-w-[135px] bg-gray-50 px-3 py-3 text-right text-[10px] uppercase text-gray-600" title="Média: últimas 5 semanas contra a média de 20. Recente: semana foco contra a média de 5.">Variações<span class="block font-normal normal-case">Média / recente</span></th>
              </template>
              <template v-else-if="visao === 'mensal'">
                <th v-for="(mes, indice) in MESES" :key="mes" class="min-w-[100px] px-3 py-3 text-right text-[10px] uppercase text-gray-400" :title="tooltipMesAberto(grupo.dados, indice)">{{ mes }}</th>
                <th class="min-w-[120px] bg-gray-50 px-3 py-3 text-right text-[10px] uppercase text-gray-600">{{ grupo.dados.periodo_equivalente ? 'Total comparável' : 'Total' }}</th>
              </template>
              <template v-else>
                <th v-for="periodo in grupo.dados.anos" :key="periodo.ano" class="min-w-[145px] px-3 py-3 text-right text-[10px] uppercase text-gray-600" :title="`${dataCurta(periodo.inicio)} a ${dataCurta(periodo.fim)}`">{{ periodo.ano }}<span v-if="periodo.parcial" class="block font-normal normal-case text-amber-700">Parcial</span><span v-else-if="periodo.equivalente" class="block font-normal normal-case text-gray-400">Até {{ dataCurta(periodo.fim).slice(0, 5) }}</span></th>
                <th class="min-w-[135px] bg-gray-50 px-3 py-3 text-right text-[10px] uppercase text-gray-600" :title="tituloAnual(grupo.dados)">Variações<span class="block font-normal normal-case">Média / recente</span></th>
              </template>
            </tr></thead>
            <tbody>
              <tr v-for="linha in grupo.dados.linhas" :key="linha.id_conta" class="border-b border-gray-50 last:border-0 hover:bg-gray-50/70">
                <td class="sticky left-0 z-10 bg-white px-4 py-2.5">
                  <div class="flex items-center gap-2">
                    <span class="font-mono text-[10px] text-gray-400">{{ linha.codigo_hierarquico }}</span>
                    <span class="min-w-0 flex-1 truncate font-medium text-gray-700">{{ linha.nome_conta }}</span>
                    <QuarentenaBotao :nome="linha.nome_conta" :marcada="true" :ocupada="removendo.has(linha.id_conta)" @toggle="removerCategoria(linha)" />
                    <RouterLink :to="{ name: 'analise-categorias-vendas', query: queryRecorte(grupo, linha.id_conta) }" class="rounded p-1 text-gray-500 hover:bg-gray-100" :aria-label="`Localizar ${linha.nome_conta} na análise completa`" title="Localizar na análise completa"><Layers3 class="h-3.5 w-3.5" /></RouterLink>
                    <button type="button" class="rounded p-1 text-gray-500 hover:bg-gray-100" :aria-label="`Detalhar produtos de ${linha.nome_conta}`" title="Abrir produtos em nova aba" @click="abrirProdutos(grupo, linha)"><ExternalLink class="h-3.5 w-3.5" /></button>
                  </div>
                </td>
                <template v-if="visao === 'semanal'">
                  <template v-if="metrica === 'valor'">
                    <td class="bg-gray-50 px-3 py-2.5 text-right font-mono">{{ formatarValor(linha.media_20) }}</td>
                    <td v-for="(valor, indice) in linha.valores" :key="indice" class="px-3 py-2.5 text-right font-mono tabular-nums" :style="estiloLinha(grupo.dados, linha, valor, indice)">{{ formatarValor(valor) }}</td>
                    <td class="bg-gray-50 px-3 py-2 text-right"><VariacoesCompactas :media="linha.variacao_5_vs_20_percentual" :recente="linha.variacao_5_percentual" /></td>
                  </template>
                  <template v-else>
                    <td class="bg-gray-50 px-3 py-2 text-right"><div v-for="unidade in linha.unidades" :key="unidade.id_unidade">{{ formatarQuantidade(unidade.media_20) }} <small>{{ unidade.sigla }}</small></div><span v-if="!linha.unidades.length">—</span></td>
                    <td v-for="indice in 6" :key="indice" class="px-3 py-2 text-right"><div v-for="unidade in linha.unidades" :key="unidade.id_unidade">{{ formatarQuantidade(unidade.valores[indice - 1]) }} <small>{{ unidade.sigla }}</small></div><span v-if="!linha.unidades.length">—</span></td>
                    <td class="bg-gray-50 px-3 py-2 text-right"><VariacoesCompactas v-for="unidade in linha.unidades" :key="unidade.id_unidade" :media="unidade.variacao_5_vs_20_percentual" :recente="unidade.variacao_5_percentual" :sigla="unidade.sigla" /><span v-if="!linha.unidades.length">—</span></td>
                  </template>
                </template>
                <template v-else-if="visao === 'mensal'">
                  <template v-if="metrica === 'valor'">
                    <td v-for="(valor, indice) in linha.valores" :key="indice" class="px-3 py-2.5 text-right font-mono tabular-nums" :style="estiloLinha(grupo.dados, linha, valor, indice)">{{ formatarValor(valor) }}</td>
                    <td class="bg-gray-50 px-3 py-2.5 text-right font-mono font-semibold">{{ formatarValor(linha.total) }}</td>
                  </template>
                  <template v-else>
                    <td v-for="indice in 12" :key="indice" class="px-3 py-2 text-right"><div v-for="unidade in linha.unidades" :key="unidade.id_unidade">{{ formatarQuantidade(unidade.valores[indice - 1]) }} <small>{{ unidade.sigla }}</small></div><span v-if="!linha.unidades.length">—</span></td>
                    <td class="bg-gray-50 px-3 py-2 text-right"><div v-for="unidade in linha.unidades" :key="unidade.id_unidade">{{ formatarQuantidade(unidade.total) }} <small>{{ unidade.sigla }}</small></div><span v-if="!linha.unidades.length">—</span></td>
                  </template>
                </template>
                <template v-else>
                  <template v-if="metrica === 'valor'">
                    <td v-for="(valor, indice) in linha.valores" :key="indice" class="px-3 py-2.5 text-right font-mono tabular-nums" :style="estiloLinha(grupo.dados, linha, valor, indice)">{{ formatarValor(valor) }}</td>
                    <td class="bg-gray-50 px-3 py-2 text-right"><VariacoesCompactas :media="linha.variacao_historica_percentual" :recente="linha.variacao_percentual" :recente-neutra="grupo.dados.ano_parcial && !grupo.dados.periodo_equivalente" /></td>
                  </template>
                  <template v-else>
                    <td v-for="indice in grupo.dados.anos.length" :key="indice" class="px-3 py-2 text-right"><div v-for="unidade in linha.unidades" :key="unidade.id_unidade">{{ formatarQuantidade(unidade.valores[indice - 1]) }} <small>{{ unidade.sigla }}</small></div><span v-if="!linha.unidades.length">—</span></td>
                    <td class="bg-gray-50 px-3 py-2 text-right"><VariacoesCompactas v-for="unidade in linha.unidades" :key="unidade.id_unidade" :media="unidade.variacao_historica_percentual" :recente="unidade.variacao_percentual" :sigla="unidade.sigla" :recente-neutra="grupo.dados.ano_parcial && !grupo.dados.periodo_equivalente" /><span v-if="!linha.unidades.length">—</span></td>
                  </template>
                </template>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-for="item in grupo.categorias.filter((categoria) => !categoria.folha_valida)" :key="item.id_conta" class="flex flex-wrap items-center gap-2 border-t border-amber-100 bg-amber-50 px-4 py-2 text-xs text-amber-800">
          <AlertTriangle class="h-4 w-4" /> {{ item.codigo_hierarquico }} {{ item.nome_conta }} — {{ item.motivo_invalido }}
          <QuarentenaBotao :nome="item.nome_conta" :marcada="true" :ocupada="removendo.has(item.id_conta)" @toggle="removerCategoria(item)" />
        </div>
      </div>
    </div>
  </div>
</template>
