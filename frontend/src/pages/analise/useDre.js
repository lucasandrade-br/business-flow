import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getApiBaseUrl } from '@/services/firebirdSync'

export function useDre(visao) {
  const route = useRoute()
  const router = useRouter()
  const endpoint = `${getApiBaseUrl()}/api/analise/dashboard/dre/${visao}/`
  const anosDisponiveis = ref([])
  const periodoEquivalente = ref(visao === 'anual')
  const dados = ref(null)
  const loading = ref(true)
  const semDados = ref(false)
  const erro = ref('')
  const periodosPendentes = ref([])
  let sequencia = 0

  const anoSelecionado = computed({
    get() {
      const anoUrl = Number(route.query.ano)
      return anosDisponiveis.value.includes(anoUrl) ? anoUrl : (anosDisponiveis.value[0] ?? null)
    },
    set(ano) {
      if (visao === 'mensal') periodoEquivalente.value = false
      router.replace({ path: route.path, query: { ...route.query, ano: String(ano) } })
    },
  })

  onMounted(async () => {
    try {
      const response = await fetch(endpoint)
      if (response.status === 404) {
        semDados.value = true
        return
      }
      if (!response.ok) throw new Error('Não foi possível carregar os anos do DRE.')
      const payload = await response.json()
      anosDisponiveis.value = payload.anos_disponiveis ?? []
      if (!anosDisponiveis.value.length) semDados.value = true
      else if (String(route.query.ano || '') !== String(anoSelecionado.value)) {
        router.replace({ path: route.path, query: { ...route.query, ano: String(anoSelecionado.value) } })
      }
    } catch (e) {
      erro.value = e?.message || 'Falha ao carregar o DRE.'
    } finally {
      if (semDados.value || erro.value) loading.value = false
    }
  })

  watch([anoSelecionado, periodoEquivalente], async ([ano]) => {
    if (!ano) return
    const atual = ++sequencia
    loading.value = true
    semDados.value = false
    erro.value = ''
    periodosPendentes.value = []
    try {
      const params = new URLSearchParams({ ano: String(ano), periodo_equivalente: periodoEquivalente.value ? '1' : '0' })
      const response = await fetch(`${endpoint}?${params}`)
      const payload = await response.json().catch(() => ({}))
      if (atual !== sequencia) return
      if (response.status === 404) {
        dados.value = null
        semDados.value = true
        return
      }
      if (!response.ok) {
        periodosPendentes.value = payload.periodos_pendentes ?? []
        throw new Error(payload.detail || `Erro ${response.status} ao carregar o DRE.`)
      }
      dados.value = payload
    } catch (e) {
      if (atual === sequencia) erro.value = e?.message || 'Falha ao carregar o DRE.'
    } finally {
      if (atual === sequencia) loading.value = false
    }
  })

  return { anosDisponiveis, anoSelecionado, periodoEquivalente, dados, loading, semDados, erro, periodosPendentes }
}
