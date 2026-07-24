<template>
  <BaseModal
    v-model="open"
    title="Resolver duplicata DAV / NFCE"
    description="O DAV foi convertido em NFCE mas ambos estão no staging. Escolha qual documento manter."
  >
    <div v-if="loading" class="flex items-center justify-center py-8">
      <Loader2 class="h-5 w-5 animate-spin text-gray-400" />
    </div>

    <div v-else-if="fetchError" class="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-700">
      {{ fetchError }}
    </div>

    <div v-else-if="par" class="space-y-4">
      <!-- Alerta informativo -->
      <div class="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
        <p class="font-semibold">DAV convertido em NFCE</p>
        <p class="mt-0.5">O DAV possui correspondência na auditoria. A NFCE é o documento fiscal (SEFAZ), mas está sem auditoria. Clique no card para selecionar qual manter.</p>
      </div>

      <!-- Cards lado a lado -->
      <div class="grid grid-cols-2 gap-3">
        <!-- DAV Card -->
        <div
          class="cursor-pointer rounded-xl border-2 p-3 transition-all"
          :class="decisao === 'manter_dav' ? 'border-blue-500 bg-blue-50 shadow-sm' : 'border-gray-200 hover:border-blue-300'"
          @click="decisao = 'manter_dav'"
        >
          <div class="mb-2 flex items-center justify-between">
            <span class="text-xs font-bold text-gray-800">{{ par.dav?.venda ?? 'DAV não encontrado' }}</span>
            <span class="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700">DAV</span>
          </div>
          <div class="space-y-0.5 text-[11px] text-gray-600">
            <p>Data: {{ formatDate(par.dav?.data_venda) }}</p>
            <p>Valor: {{ asMoney(par.dav?.valor_final) }}</p>
            <p>
              Validação:
              <span :class="statusValidacaoCls(par.dav?.status_validacao)">{{ par.dav?.status_validacao || '-' }}</span>
            </p>
            <p>Tratamento: {{ par.dav?.status_tratamento || '-' }}</p>
            <p v-if="par.dav?.nome_cliente_legado" class="truncate" :title="par.dav.nome_cliente_legado">
              Cliente: {{ par.dav.nome_cliente_legado }}
            </p>
          </div>
          <div class="mt-2 flex items-center gap-1 text-[10px]">
            <CheckCircle v-if="par.dav?.tem_auditoria" class="h-3 w-3 shrink-0 text-green-600" />
            <XCircle v-else class="h-3 w-3 shrink-0 text-red-500" />
            <span :class="par.dav?.tem_auditoria ? 'text-green-700' : 'text-red-600'">
              {{ par.dav?.tem_auditoria ? 'Tem auditoria' : 'Sem auditoria' }}
            </span>
          </div>
          <div
            v-if="decisao === 'manter_dav'"
            class="mt-2 rounded-md bg-blue-500 py-1 text-center text-[11px] font-bold text-white"
          >
            ✓ Selecionado — manter
          </div>
        </div>

        <!-- NFCE Card -->
        <div
          class="cursor-pointer rounded-xl border-2 p-3 transition-all"
          :class="decisao === 'manter_nfce' ? 'border-purple-500 bg-purple-50 shadow-sm' : 'border-gray-200 hover:border-purple-300'"
          @click="decisao = 'manter_nfce'"
        >
          <div class="mb-2 flex items-center justify-between">
            <span class="text-xs font-bold text-gray-800">{{ par.nfce?.venda }}</span>
            <span class="rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-semibold text-purple-700">NFCE</span>
          </div>
          <div class="space-y-0.5 text-[11px] text-gray-600">
            <p>Data: {{ formatDate(par.nfce?.data_venda) }}</p>
            <p>Valor: {{ asMoney(par.nfce?.valor_final) }}</p>
            <p>
              Validação:
              <span :class="statusValidacaoCls(par.nfce?.status_validacao)">{{ par.nfce?.status_validacao || '-' }}</span>
            </p>
            <p v-if="par.nfce?.nfce_numero && par.nfce.nfce_numero !== '0'">Nº NF: {{ par.nfce.nfce_numero }}</p>
            <p v-if="par.nfce?.nfce_status">Status NF: {{ par.nfce.nfce_status }}</p>
          </div>
          <div class="mt-2 flex items-center gap-1 text-[10px]">
            <XCircle class="h-3 w-3 shrink-0 text-red-500" />
            <span class="text-red-600">Sem auditoria</span>
          </div>
          <div class="mt-1 flex items-center gap-1 text-[10px] text-purple-700 font-medium">
            <span>📄 Documento fiscal (SEFAZ)</span>
          </div>
          <div
            v-if="decisao === 'manter_nfce'"
            class="mt-2 rounded-md bg-purple-500 py-1 text-center text-[11px] font-bold text-white"
          >
            ✓ Selecionado — manter
          </div>
        </div>
      </div>

      <!-- Resumo da ação -->
      <div v-if="decisao" class="rounded-md border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700">
        <p v-if="decisao === 'manter_dav'">
          <strong>Ação:</strong> A NFCE
          <span class="font-mono font-semibold">{{ par.nfce?.venda }}</span>
          será marcada como <strong class="text-red-700">Negligenciada</strong>. O DAV permanece inalterado.
        </p>
        <p v-else>
          <strong>Ação:</strong> O DAV
          <span class="font-mono font-semibold">{{ par.dav?.venda ?? '—' }}</span>
          será marcado como <strong class="text-red-700">Negligenciado</strong>. A NFCE será
          <strong class="text-green-700">aprovada com validação override</strong> (sem necessidade de auditoria).
        </p>
      </div>

      <!-- Erro de resolução -->
      <div v-if="resolveError" class="rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-700">
        {{ resolveError }}
      </div>
    </div>

    <template #footer>
      <button
        type="button"
        class="rounded-md border border-gray-200 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
        :disabled="resolvendo"
        @click="$emit('update:modelValue', false)"
      >
        Cancelar
      </button>
      <button
        type="button"
        class="inline-flex items-center gap-1.5 rounded-md bg-[#373435] px-3 py-1.5 text-xs font-semibold text-white hover:bg-black disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="!decisao || resolvendo || loading"
        @click="confirmar"
      >
        <Loader2 v-if="resolvendo" class="h-3.5 w-3.5 animate-spin" />
        {{ resolvendo ? 'Processando...' : 'Confirmar resolução' }}
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { CheckCircle, Loader2, XCircle } from 'lucide-vue-next'
import BaseModal from '@/components/ui/BaseModal.vue'
import { getApiBaseUrl } from '@/services/firebirdSync'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  nfceIdLegado: { type: Number, default: null },
})
const emit = defineEmits(['update:modelValue', 'resolved'])

const API_BASE_URL = getApiBaseUrl()

const loading = ref(false)
const fetchError = ref('')
const resolveError = ref('')
const par = ref(null)
const decisao = ref('')
const resolvendo = ref(false)

const open = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

watch(
  () => props.modelValue,
  async (isOpen) => {
    if (!isOpen) {
      decisao.value = ''
      par.value = null
      fetchError.value = ''
      resolveError.value = ''
      return
    }
    if (!props.nfceIdLegado) return
    loading.value = true
    fetchError.value = ''
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/validacao/reconciliacao/par-nfce-dav?nfce_id_legado=${props.nfceIdLegado}`,
      )
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.detail || `Erro ${response.status}`)
      par.value = payload
    } catch (err) {
      fetchError.value = err?.message || 'Falha ao carregar dados do par NFCE/DAV.'
    } finally {
      loading.value = false
    }
  },
)

async function confirmar() {
  if (!decisao.value || !props.nfceIdLegado) return
  resolvendo.value = true
  resolveError.value = ''
  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/par-nfce-dav`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nfce_id_legado: props.nfceIdLegado, decisao: decisao.value }),
    })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(payload.detail || `Erro ${response.status}`)
    emit('resolved', payload)
    emit('update:modelValue', false)
  } catch (err) {
    resolveError.value = err?.message || 'Falha ao resolver par NFCE/DAV.'
  } finally {
    resolvendo.value = false
  }
}

function formatDate(value) {
  const raw = String(value || '').trim()
  if (!raw) return '-'
  const parts = raw.slice(0, 10).split('-')
  if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`
  return raw
}

function asMoney(value) {
  return Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function statusValidacaoCls(s) {
  const norm = String(s || '').toUpperCase()
  if (norm === 'APROVADO') return 'font-semibold text-green-700'
  if (norm === 'DIVERGENTE') return 'font-semibold text-red-600'
  return 'text-gray-500'
}
</script>
