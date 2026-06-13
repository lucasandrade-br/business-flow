<template>
  <BaseModal
    :model-value="modelValue"
    title="Detalhes da Compra"
    description="Visao consolidada dos itens da compra selecionada."
    @update:model-value="emit('update:modelValue', $event)"
  >
    <p v-if="loading" class="text-xs text-gray-500">Carregando detalhes...</p>
    <p v-else-if="error" class="text-xs text-red-600">{{ error }}</p>

    <div v-else-if="details" class="space-y-4">
      <div class="grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">ID Compra</p>
          <p class="font-medium text-gray-800">{{ details.id_compra }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">Compra</p>
          <p class="font-medium text-gray-800">{{ formatCompraRef(details) }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">Nota</p>
          <p class="font-medium text-gray-800">{{ details.nota || '-' }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">Fornecedor</p>
          <p class="font-medium text-gray-800">{{ details.fornecedor_nome || '-' }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">Status NFe</p>
          <p class="font-medium text-gray-800">{{ details.nfe_status || '-' }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">Emissao</p>
          <p class="font-medium text-gray-800">{{ details.data_emissao || '-' }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">Lancamento</p>
          <p class="font-medium text-gray-800">{{ details.data_lanc || '-' }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">Valor Total</p>
          <p class="font-medium text-gray-800">{{ asMoney(details.valor_total_documento) }}</p>
        </div>
      </div>

      <div>
        <h4 class="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Itens da Compra</h4>
        <div class="overflow-x-auto rounded-md border border-gray-200">
          <table class="min-w-full text-xs">
            <thead>
              <tr class="bg-gray-50 text-left text-[11px] uppercase tracking-wide text-gray-500">
                <th class="px-3 py-2">Produto</th>
                <th class="px-3 py-2">Unidade</th>
                <th class="px-3 py-2">Qtd</th>
                <th class="px-3 py-2">Custo Unit.</th>
                <th class="px-3 py-2">Total Item</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in details.itens || []" :key="item.id_item_compra" class="border-t border-gray-100">
                <td class="px-3 py-2">{{ item.produto_nome || '-' }}</td>
                <td class="px-3 py-2">{{ item.unidade_sigla || '-' }}</td>
                <td class="px-3 py-2">{{ item.quantidade }}</td>
                <td class="px-3 py-2">{{ asMoney(item.valor_custo) }}</td>
                <td class="px-3 py-2">{{ asMoney(item.valor_total_item) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <template #footer>
      <button
        type="button"
        class="rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50"
        @click="emit('update:modelValue', false)"
      >
        Fechar
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch } from "vue";
import BaseModal from "@/components/ui/BaseModal.vue";

const API_BASE_URL = "http://127.0.0.1:8000";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  compraId: { type: [Number, String], default: null },
});

const emit = defineEmits(["update:modelValue"]);

const loading = ref(false);
const error = ref("");
const details = ref(null);

function asMoney(value) {
  return Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatCompraRef(row) {
  return `COMPRA #${row?.id_legado ?? ""}`;
}

async function fetchDetails() {
  if (!props.compraId) {
    details.value = null;
    return;
  }

  loading.value = true;
  error.value = "";
  details.value = null;

  try {
    const response = await fetch(`${API_BASE_URL}/api/compras/compras/${props.compraId}`);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    details.value = await response.json();
  } catch (err) {
    console.error(err);
    error.value = "Falha ao carregar detalhes da compra.";
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.modelValue, props.compraId],
  ([isOpen]) => {
    if (!isOpen) {
      return;
    }
    fetchDetails();
  },
  { immediate: true },
);
</script>
