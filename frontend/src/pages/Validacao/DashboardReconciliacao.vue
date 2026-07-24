<template>
  <section class="space-y-4">
    <!-- Coordenador: delega toda a lógica de negócio aos painéis filhos.
         PainelImportacaoVendas: importação de planilhas e sincronização Firebird.
         PainelGerenciamentoStg: KPIs, filtros, tabela, tratamento e consolidação. -->

    <article v-if="initializing" class="rounded-md border border-gray-200 bg-white p-4">
      <div class="flex items-center gap-3">
        <Loader2 class="h-5 w-5 animate-spin text-gray-400" />
        <p class="text-sm text-gray-500">Verificando dados pendentes de validação...</p>
      </div>
    </article>

    <PainelImportacaoVendas v-if="!initializing && !hasValidationResult" />

    <PainelGerenciamentoStg
      v-if="!initializing && hasValidationResult"
      @nova-importacao-confirmada="onNovaImportacaoConfirmada"
    />

    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="translate-y-2 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="translate-y-2 opacity-0"
    >
      <div v-if="toast" class="fixed bottom-5 right-5 z-50 rounded-md border border-gray-200 bg-white px-4 py-3 text-xs text-[#373435]">
        {{ toast }}
      </div>
    </transition>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { Loader2 } from "lucide-vue-next";
import { getApiBaseUrl } from "@/services/firebirdSync";
import PainelImportacaoVendas from "./PainelImportacaoVendas.vue";
import PainelGerenciamentoStg from "./PainelGerenciamentoStg.vue";
import { useSharedKpis, resetKpis, applyKpis } from "./composables/useSharedKpis";
import { useToast } from "./composables/useToast";

const API_BASE_URL = getApiBaseUrl();
const { kpis } = useSharedKpis();
const { toast } = useToast();
const initializing = ref(true);

const hasValidationResult = computed(() => Number(kpis.total_vendas_stg || 0) > 0);

function onNovaImportacaoConfirmada() {
  resetKpis();
}

onMounted(async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/divergencias`);
    const payload = await response.json().catch(() => ({}));
    if (response.ok) {
      applyKpis((payload.results || {}).kpis || {});
    }
  } finally {
    initializing.value = false;
  }
});
</script>
