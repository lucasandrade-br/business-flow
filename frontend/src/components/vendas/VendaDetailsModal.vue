<template>
  <BaseModal
    :model-value="modelValue"
    title="Detalhes da Venda"
    description="Visao consolidada de itens e pagamentos da venda selecionada."
    @update:model-value="emit('update:modelValue', $event)"
  >
    <p v-if="loading" class="text-xs text-gray-500">Carregando detalhes...</p>
    <p v-else-if="error" class="text-xs text-red-600">{{ error }}</p>

    <div v-else-if="details" class="space-y-4">
      <div class="grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">ID Venda</p>
          <p class="font-medium text-gray-800">{{ details.id_venda }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">Venda</p>
          <p class="font-medium text-gray-800">{{ formatVendaRef(details) }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">Status</p>
          <span
            class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold"
            :class="statusVendaBadgeClass(details.status)"
          >
            {{ details.status || 'N/A' }}
          </span>
        </div>
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">Cliente</p>
          <p class="font-medium text-gray-800">{{ details.cliente_nome || '-' }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">Usuario</p>
          <p class="font-medium text-gray-800">{{ details.usuario_nome || '-' }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">Data</p>
          <p class="font-medium text-gray-800">{{ details.data_venda }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">Hora</p>
          <p class="font-medium text-gray-800">{{ details.hora_venda || '-' }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">Valor Total</p>
          <p class="font-medium text-gray-800">{{ asMoney(details.valor_total_documento) }}</p>
        </div>
      </div>

      <div>
        <h4 class="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Itens da Venda</h4>
        <div class="overflow-x-auto rounded-md border border-gray-200">
          <table class="min-w-full text-xs">
            <thead>
              <tr class="bg-gray-50 text-left text-[11px] uppercase tracking-wide text-gray-500">
                <th class="px-3 py-2">Produto</th>
                <th class="px-3 py-2">Unidade</th>
                <th class="px-3 py-2">Qtd</th>
                <th class="px-3 py-2">Vlr Unit.</th>
                <th class="px-3 py-2">Vlr Total</th>
                <th class="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in details.itens || []" :key="item.id_item_venda" class="border-t border-gray-100">
                <td class="px-3 py-2">{{ item.produto_nome || item.produto }}</td>
                <td class="px-3 py-2">{{ item.unidade_sigla || '-' }}</td>
                <td class="px-3 py-2">{{ item.quantidade }}</td>
                <td class="px-3 py-2">{{ asMoney(item.valor_unitario) }}</td>
                <td class="px-3 py-2">{{ asMoney(item.valor_total_item) }}</td>
                <td class="px-3 py-2">
                  <span
                    class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold"
                    :class="statusItemBadgeClass(item.cancelado)"
                  >
                    {{ toBoolean(item.cancelado) ? 'CANCELADO' : 'ATIVO' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h4 class="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Pagamentos da Venda</h4>
        <div class="overflow-x-auto rounded-md border border-gray-200">
          <table class="min-w-full text-xs">
            <thead>
              <tr class="bg-gray-50 text-left text-[11px] uppercase tracking-wide text-gray-500">
                <th class="px-3 py-2">Forma</th>
                <th class="px-3 py-2">Valor</th>
                <th class="px-3 py-2">Estorno</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="pg in details.pagamentos || []" :key="pg.id_pagamento_venda" class="border-t border-gray-100">
                <td class="px-3 py-2">{{ pg.forma_pagamento_descricao || pg.forma_pagamento }}</td>
                <td class="px-3 py-2">{{ asMoney(pg.valor_pago) }}</td>
                <td class="px-3 py-2">{{ toBoolean(pg.estorno) ? 'Sim' : 'Nao' }}</td>
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
  vendaId: { type: [Number, String], default: null },
});

const emit = defineEmits(["update:modelValue"]);

const loading = ref(false);
const error = ref("");
const details = ref(null);

function toBoolean(value) {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value === 1;
  const normalized = String(value || "").trim().toLowerCase();
  return normalized === "1" || normalized === "true" || normalized === "sim";
}

function asMoney(value) {
  return Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatVendaRef(row) {
  const tipo = String(row?.tipo_documento || "").toUpperCase();
  const idLegado = row?.id_legado ?? "";
  return `${tipo} #${idLegado}`;
}

function statusVendaBadgeClass(status) {
  const norm = String(status || "").toUpperCase();
  if (norm === "F") return "bg-green-100 text-green-800";
  if (norm === "C") return "bg-amber-100 text-amber-800";
  return "bg-gray-100 text-gray-700";
}

function statusItemBadgeClass(cancelado) {
  return toBoolean(cancelado) ? "bg-amber-100 text-amber-800" : "bg-green-100 text-green-800";
}

async function fetchDetails() {
  if (!props.vendaId) {
    details.value = null;
    return;
  }

  loading.value = true;
  error.value = "";
  details.value = null;

  try {
    const response = await fetch(`${API_BASE_URL}/api/vendas/vendas/${props.vendaId}`);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    details.value = await response.json();
  } catch (err) {
    console.error(err);
    error.value = "Falha ao carregar detalhes da venda.";
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.modelValue, props.vendaId],
  ([isOpen]) => {
    if (!isOpen) {
      return;
    }
    fetchDetails();
  },
  { immediate: true },
);
</script>
