<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { AlertTriangle, ChevronDown, ChevronRight, ExternalLink, Layers3 } from 'lucide-vue-next'
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
const ENDPOINT = `${API_BASE_URL}/api/analise/categorias/vendas/`
const router = useRouter()

const familias = ref([])
const anos = ref([])
const familiaSelecionada = ref('')
const anoSelecionado = ref(null)
const metrica = ref('valor')
const dados = ref(null)
const loadingInicial = ref(true)
const loading = ref(false)
const erro = ref('')
const conflitos = ref([])
const expandidas = ref(new Set())

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
    anoSelecionado.value = anos.value[0] ?? null
  } catch (e) {
    erro.value = e?.message || 'Falha ao carregar a análise.'
  } finally {
    loadingInicial.value = false
  }
}

async function carregarRelatorio() {
  if (!familiaSelecionada.value || !anoSelecionado.value) {
    dados.value = null
    conflitos.value = []
    return
  }
  loading.value = true
  erro.value = ''
  conflitos.value = []
  try {
    const params = new URLSearchParams({
      ano: String(anoSelecionado.value),
      raiz_id: String(familiaSelecionada.value),
      metrica: metrica.value,
    })
    const res = await fetch(`${ENDPOINT}?${params}`)
    const payload = await res.json().catch(() => ({}))
    if (!res.ok) {
      conflitos.value = payload.produtos_conflitantes ?? []
      throw new Error(payload.detail || `Erro ${res.status}`)
    }
    dados.value = payload
    expandidas.value = new Set([payload.familia.id_conta])
  } catch (e) {
    dados.value = null
    erro.value = e?.message || 'Falha ao processar o relatório.'
  } finally {
    loading.value = false
  }
}

watch([familiaSelecionada, anoSelecionado, metrica], carregarRelatorio)
onMounted(carregarOpcoes)

function toggleCategoria(id) {
  const novo = new Set(expandidas.value)
  if (novo.has(id)) novo.delete(id)
  else novo.add(id)
  expandidas.value = novo
}

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

function estiloLinha(linha, valor, indice) {
  return estiloCelulaFinanceira(
    quartisPorLinha.value.get(linha.id_conta),
    valor,
    false,
    mesEstaAberto(dados.value, indice),
  )
}

function abrirProdutos(linha) {
  const destino = router.resolve({
    name: 'analise-categorias-produtos-vendas',
    query: {
      raiz_id: familiaSelecionada.value,
      categoria_id: linha.id_conta,
      ano: anoSelecionado.value,
      metrica: metrica.value,
    },
  })
  const novaAba = window.open(destino.href, '_blank', 'noopener,noreferrer')
  if (novaAba) novaAba.opener = null
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <div>
      <h1 class="text-xl font-bold text-gray-900">Vendas por Categoria</h1>
      <p class="mt-0.5 text-sm text-gray-400">Receita bruta ou quantidade vendida pela hierarquia do plano de contas.</p>
    </div>

    <div class="rounded-xl border border-gray-200 bg-white shadow-sm">
      <div class="flex flex-wrap items-end gap-3 border-b border-gray-100 bg-gray-50/70 px-4 py-3">
        <label class="flex min-w-[260px] flex-1 flex-col gap-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
          Família do plano de contas
          <select v-model="familiaSelecionada" class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium normal-case text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300" :disabled="loadingInicial || !anos.length">
            <option value="">Selecione uma família</option>
            <option v-for="familia in familias" :key="familia.id_conta" :value="familia.id_conta">
              {{ familia.codigo_hierarquico }} {{ familia.nome_conta }}
            </option>
          </select>
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
            <button type="button" class="px-3 transition-colors" :class="metrica === 'valor' ? 'bg-[#373435] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'" @click="metrica = 'valor'">Valores financeiros</button>
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
          <li v-for="produto in conflitos.slice(0, 10)" :key="produto.id_produto">
            {{ produto.id_produto }} — {{ produto.produto }}
          </li>
          <li v-if="conflitos.length > 10">E mais {{ conflitos.length - 10 }} produto(s).</li>
        </ul>
      </div>

      <div v-if="loadingInicial || loading" class="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
        <div class="h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-[#373435]" />
        <div>
          <p class="text-sm font-medium text-gray-700">Processando análise</p>
          <p class="mt-1 text-xs text-gray-400">Consultas de grande volume podem levar alguns segundos.</p>
        </div>
      </div>

      <div v-else-if="!anos.length && !erro" class="flex flex-col items-center justify-center px-6 py-16 text-center">
        <div class="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-amber-50">
          <AlertTriangle class="h-5 w-5 text-amber-500" />
        </div>
        <p class="text-sm font-medium text-gray-600">Agregado analítico ainda não construído</p>
        <p class="mt-1 text-xs text-gray-400">Execute a reconstrução inicial para disponibilizar os anos do relatório.</p>
      </div>

      <div v-else-if="!familiaSelecionada && !erro" class="flex flex-col items-center justify-center px-6 py-16 text-center">
        <div class="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-gray-100">
          <Layers3 class="h-5 w-5 text-gray-400" />
        </div>
        <p class="text-sm font-medium text-gray-600">Selecione uma família</p>
        <p class="mt-1 text-xs text-gray-400">A estrutura completa do plano será exibida nesta matriz.</p>
      </div>

      <div v-else-if="dados" class="app-scrollbar overflow-x-auto">
        <table class="w-full border-collapse text-xs">
          <thead>
            <tr class="border-b border-gray-100 bg-white">
              <th class="sticky left-0 z-20 min-w-[280px] bg-white px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-400 shadow-[1px_0_0_#f3f4f6]">Categoria</th>
              <th v-for="(mes, indice) in MESES" :key="mes" class="min-w-[100px] px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400" :title="tooltipMesAberto(dados, indice)" :aria-label="tooltipMesAberto(dados, indice) || mes">{{ mes }}</th>
              <th class="min-w-[120px] bg-gray-50 px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-600">Total</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="linha in linhasVisiveis" :key="linha.id_conta" class="border-b border-gray-50 last:border-0 hover:bg-gray-50/70" :class="linha.nivel === 0 ? 'bg-gray-50/50 font-bold' : ''">
              <td class="sticky left-0 z-10 bg-white px-4 py-2.5 shadow-[1px_0_0_#f3f4f6]" :class="linha.nivel === 0 ? '!bg-gray-50' : ''">
                <div class="flex items-center" :style="{ paddingLeft: `${linha.nivel * 18}px` }">
                  <button v-if="linha.tem_filhos" type="button" class="mr-1 flex h-5 w-5 items-center justify-center rounded text-gray-400 hover:bg-gray-200 hover:text-gray-700" @click="toggleCategoria(linha.id_conta)">
                    <ChevronDown v-if="expandidas.has(linha.id_conta)" class="h-3.5 w-3.5" />
                    <ChevronRight v-else class="h-3.5 w-3.5" />
                  </button>
                  <span v-else class="mr-1 inline-block h-5 w-5" />
                  <span class="mr-2 font-mono text-[10px] text-gray-400">{{ linha.codigo_hierarquico }}</span>
                  <span class="text-gray-700" :class="linha.tem_filhos ? 'font-semibold' : 'font-medium'">{{ linha.nome_conta }}</span>
                  <button
                    v-if="!linha.tem_filhos"
                    type="button"
                    class="ml-auto flex h-6 w-6 shrink-0 items-center justify-center rounded text-gray-400 hover:bg-gray-200 hover:text-gray-700"
                    title="Abrir vendas por produto em uma nova aba"
                    :aria-label="`Detalhar produtos de ${linha.nome_conta}`"
                    @click.stop="abrirProdutos(linha)"
                  >
                    <ExternalLink class="h-3.5 w-3.5" />
                  </button>
                </div>
              </td>

              <template v-if="metrica === 'valor'">
                <td
                  v-for="(valor, indice) in linha.valores"
                  :key="indice"
                  class="px-3 py-2.5 text-right font-mono tabular-nums"
                  :class="numeroFinanceiro(valor) === null ? 'text-gray-300' : 'text-gray-700'"
                  :style="estiloLinha(linha, valor, indice)"
                >{{ formatarValor(valor) }}</td>
                <td class="bg-gray-50 px-4 py-2.5 text-right font-mono font-semibold tabular-nums text-gray-800">{{ formatarValor(linha.total) }}</td>
              </template>
              <template v-else>
                <td v-for="indice in 12" :key="indice" class="px-3 py-2 text-right align-top font-mono tabular-nums text-gray-600">
                  <div v-if="linha.unidades.length" class="space-y-0.5">
                    <div v-for="unidade in linha.unidades" :key="unidade.id_unidade" class="whitespace-nowrap">
                      {{ formatarQuantidade(unidade.valores[indice - 1]) }} <span class="text-[9px] font-semibold text-gray-400">{{ unidade.sigla }}</span>
                    </div>
                  </div>
                  <span v-else class="text-gray-300">0</span>
                </td>
                <td class="bg-gray-50 px-4 py-2 text-right align-top font-mono font-semibold tabular-nums text-gray-800">
                  <div v-if="linha.unidades.length" class="space-y-0.5">
                    <div v-for="unidade in linha.unidades" :key="unidade.id_unidade" class="whitespace-nowrap">
                      {{ formatarQuantidade(unidade.total) }} <span class="text-[9px] text-gray-500">{{ unidade.sigla }}</span>
                    </div>
                  </div>
                  <span v-else class="text-gray-300">0</span>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
