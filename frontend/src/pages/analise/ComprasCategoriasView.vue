<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AlertTriangle, ChevronDown, ChevronRight, ExternalLink, Layers3 } from 'lucide-vue-next'
import RemoteSearchSelect from '@/components/ui/RemoteSearchSelect.vue'
import { getApiBaseUrl } from '@/services/firebirdSync'
import {
  MESES,
  estiloCelulaFinanceira,
  formatarQuantidade,
  formatarValor,
  indicesIgnoradosMesAberto,
  mapaQuartis,
  mesEstaAberto,
  numeroFinanceiro,
  tooltipMesAberto,
} from './analiseMensalUtils'

const API_BASE_URL = getApiBaseUrl()
const ENDPOINT = `${API_BASE_URL}/api/analise/categorias/compras/`
const FORNECEDORES_ENDPOINT = `${API_BASE_URL}/api/cadastros/fornecedores`
const route = useRoute()
const router = useRouter()

const familias = ref([])
const anos = ref([])
const familiaSelecionada = ref(String(route.query.raiz_id || ''))
const anoSelecionado = ref(Number(route.query.ano) || null)
const metrica = ref(['valor', 'quantidade'].includes(route.query.metrica) ? route.query.metrica : 'valor')
const fornecedorSelecionado = ref(String(route.query.fornecedor_id || ''))
const dados = ref(null)
const loadingInicial = ref(true)
const loading = ref(false)
const erro = ref('')
const conflitos = ref([])
const expandidas = ref(new Set())
const pronto = ref(false)
let requisicaoAtual = null

const fornecedorLabel = computed(() => {
  const fornecedor = dados.value?.fornecedor
  if (!fornecedor || String(fornecedor.id_fornecedor) !== fornecedorSelecionado.value) return ''
  return `${fornecedor.id_fornecedor} - ${fornecedor.nome_fornecedor}`
})

const linhasVisiveis = computed(() => {
  const linhas = dados.value?.linhas ?? []
  const porId = new Map(linhas.map((linha) => [linha.id_conta, linha]))
  return linhas.filter((linha) => {
    let paiId = linha.conta_pai_id
    while (paiId) {
      if (!expandidas.value.has(paiId)) return false
      paiId = porId.get(paiId)?.conta_pai_id ?? null
    }
    return true
  })
})

const quartisPorLinha = computed(() => new Map(
  (dados.value?.linhas ?? []).map((linha) => [
    linha.id_conta,
    mapaQuartis(linha.valores ?? [], indicesIgnoradosMesAberto(dados.value)),
  ]),
))

function formatFornecedorOption(item) {
  const nome = String(item.nome_gerencial || '').trim() || item.nome_fornecedor
  return `${item.id_fornecedor} - ${nome}`
}

function sincronizarUrl() {
  const query = {}
  if (familiaSelecionada.value) query.raiz_id = familiaSelecionada.value
  if (anoSelecionado.value) query.ano = String(anoSelecionado.value)
  query.metrica = metrica.value
  if (fornecedorSelecionado.value) query.fornecedor_id = fornecedorSelecionado.value
  router.replace({ query })
}

async function carregarOpcoes() {
  loadingInicial.value = true
  erro.value = ''
  try {
    const [resFamilias, resMetadata] = await Promise.all([
      fetch(`${API_BASE_URL}/api/cadastros/plano-contas/raizes`),
      fetch(ENDPOINT),
    ])
    if (!resFamilias.ok || !resMetadata.ok) throw new Error('Não foi possível carregar as opções da análise.')
    familias.value = await resFamilias.json()
    const metadata = await resMetadata.json()
    anos.value = metadata.anos_disponiveis ?? []
    if (!anos.value.includes(anoSelecionado.value)) anoSelecionado.value = anos.value[0] ?? null
    if (familiaSelecionada.value && !familias.value.some(
      (familia) => String(familia.id_conta) === familiaSelecionada.value,
    )) familiaSelecionada.value = ''
  } catch (e) {
    erro.value = e?.message || 'Falha ao carregar a análise.'
  } finally {
    loadingInicial.value = false
    pronto.value = true
  }
  await carregarRelatorio()
}

async function carregarRelatorio() {
  if (!pronto.value || !familiaSelecionada.value || !anoSelecionado.value) {
    dados.value = null
    conflitos.value = []
    sincronizarUrl()
    return
  }
  if (requisicaoAtual) requisicaoAtual.abort()
  const requisicao = new AbortController()
  requisicaoAtual = requisicao
  loading.value = true
  erro.value = ''
  conflitos.value = []
  sincronizarUrl()
  try {
    const params = new URLSearchParams({
      ano: String(anoSelecionado.value),
      raiz_id: familiaSelecionada.value,
      metrica: metrica.value,
    })
    if (fornecedorSelecionado.value) params.set('fornecedor_id', fornecedorSelecionado.value)
    const response = await fetch(`${ENDPOINT}?${params}`, { signal: requisicao.signal })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) {
      conflitos.value = payload.produtos_conflitantes ?? []
      throw new Error(payload.detail || `Erro ${response.status}`)
    }
    dados.value = payload
    expandidas.value = new Set([payload.familia.id_conta])
  } catch (e) {
    if (e?.name === 'AbortError') return
    dados.value = null
    erro.value = e?.message || 'Falha ao processar o relatório.'
  } finally {
    if (requisicaoAtual === requisicao) {
      requisicaoAtual = null
      loading.value = false
    }
  }
}

function toggleCategoria(id) {
  const novo = new Set(expandidas.value)
  if (novo.has(id)) novo.delete(id)
  else novo.add(id)
  expandidas.value = novo
}

function estiloLinha(linha, valor, indice) {
  return estiloCelulaFinanceira(
    quartisPorLinha.value.get(linha.id_conta),
    valor,
    true,
    mesEstaAberto(dados.value, indice),
  )
}

function abrirProdutos(linha) {
  const query = {
    raiz_id: familiaSelecionada.value,
    categoria_id: linha.id_conta,
    ano: anoSelecionado.value,
    metrica: metrica.value,
  }
  if (fornecedorSelecionado.value) query.fornecedor_id = fornecedorSelecionado.value
  const destino = router.resolve({ name: 'analise-categorias-produtos-compras', query })
  const novaAba = window.open(destino.href, '_blank', 'noopener,noreferrer')
  if (novaAba) novaAba.opener = null
}

watch([familiaSelecionada, anoSelecionado, metrica, fornecedorSelecionado], () => {
  if (pronto.value) carregarRelatorio()
})
onMounted(carregarOpcoes)
onBeforeUnmount(() => {
  if (requisicaoAtual) requisicaoAtual.abort()
})
</script>

<template>
  <div class="flex flex-col gap-5">
    <div>
      <h1 class="text-xl font-bold text-gray-900">Compras por Categoria</h1>
      <p class="mt-0.5 text-sm text-gray-400">Valor comprado ou quantidade pela hierarquia do plano de contas.</p>
    </div>

    <div class="rounded-xl border border-gray-200 bg-white shadow-sm">
      <div class="flex flex-wrap items-end gap-3 border-b border-gray-100 bg-gray-50/70 px-4 py-3">
        <label class="flex min-w-[220px] flex-1 flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
          Família do plano de contas
          <select v-model="familiaSelecionada" class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium normal-case text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300" :disabled="loadingInicial || !anos.length">
            <option value="">Selecione uma família</option>
            <option v-for="familia in familias" :key="familia.id_conta" :value="String(familia.id_conta)">{{ familia.codigo_hierarquico }} {{ familia.nome_conta }}</option>
          </select>
        </label>

        <label class="flex min-w-[250px] flex-1 flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
          Fornecedor
          <RemoteSearchSelect
            v-model="fornecedorSelecionado"
            :endpoint="FORNECEDORES_ENDPOINT"
            value-field="id_fornecedor"
            :format-option-label="formatFornecedorOption"
            all-label="Todos os fornecedores"
            search-placeholder="Pesquisar fornecedor..."
            :min-chars="2"
            :limit="20"
            :initial-label="fornecedorLabel"
            :disabled="loadingInicial"
            button-class="flex h-[34px] w-full items-center justify-between gap-2 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium normal-case text-gray-700 hover:bg-gray-50 disabled:opacity-60"
          />
        </label>

        <label class="flex w-28 flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
          Ano
          <select v-model="anoSelecionado" class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300" :disabled="loadingInicial || !anos.length">
            <option v-for="ano in anos" :key="ano" :value="ano">{{ ano }}</option>
          </select>
        </label>

        <div class="flex flex-col gap-1">
          <span class="text-[10px] font-semibold uppercase tracking-wide text-gray-500">Métrica</span>
          <div class="flex h-[34px] overflow-hidden rounded-md border border-gray-200 text-xs font-semibold">
            <button type="button" class="px-3 transition-colors" :class="metrica === 'valor' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" @click="metrica = 'valor'">Valor comprado</button>
            <button type="button" class="border-l border-gray-200 px-3 transition-colors" :class="metrica === 'quantidade' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" @click="metrica = 'quantidade'">Quantidades</button>
          </div>
        </div>
      </div>

      <div v-if="dados?.desatualizado" class="flex items-start gap-2 border-b border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
        <AlertTriangle class="mt-0.5 h-4 w-4 shrink-0" />
        <span>Existem períodos aguardando atualização. Os últimos valores válidos continuam visíveis.</span>
      </div>
      <div v-if="erro" class="border-b border-red-100 bg-red-50 px-4 py-3 text-xs text-red-700">
        <p class="font-semibold">{{ erro }}</p>
        <ul v-if="conflitos.length" class="mt-2 list-disc pl-5">
          <li v-for="produto in conflitos.slice(0, 10)" :key="produto.id_produto">{{ produto.id_produto }} — {{ produto.produto }}</li>
          <li v-if="conflitos.length > 10">E mais {{ conflitos.length - 10 }} produto(s).</li>
        </ul>
      </div>

      <div v-if="loadingInicial || loading" class="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
        <div class="h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-[#373435]" />
        <div><p class="text-sm font-medium text-gray-700">Processando análise</p><p class="mt-1 text-xs text-gray-400">A consulta pode levar alguns segundos.</p></div>
      </div>
      <div v-else-if="!anos.length && !erro" class="flex flex-col items-center justify-center px-6 py-16 text-center">
        <AlertTriangle class="mb-3 h-7 w-7 text-amber-500" />
        <p class="text-sm font-medium text-gray-600">Agregado analítico ainda não construído</p>
      </div>
      <div v-else-if="!familiaSelecionada && !erro" class="flex flex-col items-center justify-center px-6 py-16 text-center">
        <Layers3 class="mb-3 h-8 w-8 text-gray-300" />
        <p class="text-sm font-medium text-gray-600">Selecione uma família</p>
      </div>

      <div v-else-if="dados" class="app-scrollbar overflow-x-auto">
        <table class="w-full border-collapse text-xs">
          <thead><tr class="border-b border-gray-100 bg-white">
            <th class="sticky left-0 z-20 min-w-[300px] bg-white px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-400 shadow-[1px_0_0_#f3f4f6]">Categoria</th>
            <th v-for="(mes, indice) in MESES" :key="mes" class="min-w-[100px] px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400" :title="tooltipMesAberto(dados, indice)" :aria-label="tooltipMesAberto(dados, indice) || mes">{{ mes }}</th>
            <th class="min-w-[120px] bg-gray-50 px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-600">Total</th>
          </tr></thead>
          <tbody>
            <tr v-for="linha in linhasVisiveis" :key="linha.id_conta" class="border-b border-gray-50 last:border-0 hover:bg-gray-50/70" :class="linha.nivel === 0 ? 'bg-gray-50/50 font-bold' : ''">
              <td class="sticky left-0 z-10 bg-white px-4 py-2.5 shadow-[1px_0_0_#f3f4f6]" :class="linha.nivel === 0 ? '!bg-gray-50' : ''">
                <div class="flex items-center" :style="{ paddingLeft: `${linha.nivel * 18}px` }">
                  <button v-if="linha.tem_filhos" type="button" class="mr-1 flex h-5 w-5 items-center justify-center rounded text-gray-400 hover:bg-gray-200" @click="toggleCategoria(linha.id_conta)">
                    <ChevronDown v-if="expandidas.has(linha.id_conta)" class="h-3.5 w-3.5" /><ChevronRight v-else class="h-3.5 w-3.5" />
                  </button>
                  <span v-else class="mr-1 inline-block h-5 w-5" />
                  <span class="mr-2 font-mono text-[10px] text-gray-400">{{ linha.codigo_hierarquico }}</span>
                  <span class="text-gray-700" :class="linha.tem_filhos ? 'font-semibold' : 'font-medium'">{{ linha.nome_conta }}</span>
                  <button v-if="!linha.tem_filhos" type="button" class="ml-auto flex h-6 w-6 shrink-0 items-center justify-center rounded text-gray-400 hover:bg-gray-200" title="Abrir compras por produto em uma nova aba" :aria-label="`Detalhar produtos de ${linha.nome_conta}`" @click.stop="abrirProdutos(linha)">
                    <ExternalLink class="h-3.5 w-3.5" />
                  </button>
                </div>
              </td>
              <template v-if="metrica === 'valor'">
                <td v-for="(valor, indice) in linha.valores" :key="indice" class="px-3 py-2.5 text-right font-mono tabular-nums" :class="numeroFinanceiro(valor) === null ? 'text-gray-300' : 'text-gray-700'" :style="estiloLinha(linha, valor, indice)">{{ formatarValor(valor) }}</td>
                <td class="bg-gray-50 px-4 py-2.5 text-right font-mono font-semibold tabular-nums text-gray-800">{{ formatarValor(linha.total) }}</td>
              </template>
              <template v-else>
                <td v-for="indice in 12" :key="indice" class="px-3 py-2 text-right align-top font-mono tabular-nums text-gray-600">
                  <div v-if="linha.unidades.length" class="space-y-0.5"><div v-for="unidade in linha.unidades" :key="unidade.id_unidade" class="whitespace-nowrap">{{ formatarQuantidade(unidade.valores[indice - 1]) }} <span class="text-[9px] font-semibold text-gray-400">{{ unidade.sigla }}</span></div></div>
                  <span v-else class="text-gray-300">-</span>
                </td>
                <td class="bg-gray-50 px-4 py-2 text-right align-top font-mono font-semibold tabular-nums text-gray-800">
                  <div v-if="linha.unidades.length" class="space-y-0.5"><div v-for="unidade in linha.unidades" :key="unidade.id_unidade" class="whitespace-nowrap">{{ formatarQuantidade(unidade.total) }} <span class="text-[9px] text-gray-500">{{ unidade.sigla }}</span></div></div>
                  <span v-else class="text-gray-300">-</span>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
