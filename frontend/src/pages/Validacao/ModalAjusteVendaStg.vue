<template>
  <BaseModal
    :model-value="modelValue"
    title="Ajustar Venda STG"
    description="Ajuste venda, itens e pagamentos. A validacao sera recalculada automaticamente ao salvar."
    @update:model-value="(value) => emit('update:modelValue', value)"
  >
    <div class="space-y-4">
      <p class="text-xs text-gray-700">
        Data: <strong>{{ formatDateBR(row?.data_venda) }}</strong>
        | Venda: <strong>{{ row?.venda || `${row?.tipo_documento || '-'} #${row?.id_legado || '-'}` }}</strong>
        | Cliente: <strong>{{ row?.nome_cliente_legado || '-' }}</strong>
      </p>
      <div class="grid gap-3 sm:grid-cols-2">
        <BaseInput v-model="form.valor_final" label="Total Documento" />
        <div class="space-y-1">
          <label class="text-xs font-semibold text-gray-700">Status da Venda</label>
          <select v-model="form.status_venda" class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm">
            <option value="F">F</option>
            <option value="C">C</option>
          </select>
        </div>
      </div>

      <div class="space-y-2">
        <p class="text-xs font-semibold text-gray-700">Itens</p>
        <div class="max-h-48 overflow-auto rounded-md border border-gray-200">
          <table class="min-w-full text-xs">
            <thead>
              <tr class="border-b border-gray-100 bg-gray-50 text-left text-gray-500">
                <th class="px-2 py-1">Produto</th>
                <th class="px-2 py-1">Status</th>
                <th class="px-2 py-1">Qtd</th>
                <th class="px-2 py-1">Unitario</th>
                <th class="px-2 py-1">Total</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in form.itens" :key="item.id_stg_item_venda" class="border-b border-gray-100">
                <td class="px-2 py-1">{{ item.nome_produto_legado || item.id_produto_legado }}</td>
                <td class="px-2 py-1">{{ formatStatus(item.status_venda) }}</td>
                <td class="px-2 py-1"><input v-model="item.quantidade" type="text" class="w-20 rounded-md border border-gray-200 px-2 py-1" /></td>
                <td class="px-2 py-1"><input v-model="item.valor_unitario" type="text" class="w-24 rounded-md border border-gray-200 px-2 py-1" /></td>
                <td class="px-2 py-1"><input v-model="item.valor_total_calculado" type="text" class="w-24 rounded-md border border-gray-200 px-2 py-1" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="space-y-2">
        <p class="text-xs font-semibold text-gray-700">Pagamentos</p>
        <div class="max-h-40 overflow-auto rounded-md border border-gray-200">
          <table class="min-w-full text-xs">
            <thead>
              <tr class="border-b border-gray-100 bg-gray-50 text-left text-gray-500">
                <th class="px-2 py-1">Forma</th>
                <th class="px-2 py-1">Valor</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="pg in form.pagamentos" :key="pg.id_stg_pagamento_venda" class="border-b border-gray-100">
                <td class="px-2 py-1">
                  <select
                    class="w-full rounded-md border border-gray-200 px-2 py-1 text-xs"
                    :value="toStringOrEmpty(pg.id_tipo_pagamento_legado)"
                    @change="handlePagamentoFormaChange(pg, $event.target.value)"
                  >
                    <option value="">Selecione uma forma</option>
                    <option v-for="fp in formasPagamento" :key="fp.id_forma" :value="String(fp.id_forma)">
                      {{ fp.descricao }}
                    </option>
                  </select>
                </td>
                <td class="px-2 py-1"><input v-model="pg.valor_pago" type="text" class="w-24 rounded-md border border-gray-200 px-2 py-1" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="space-y-2">
        <p class="text-xs font-semibold text-gray-700">Pagamentos Auditoria</p>
        <div class="max-h-40 overflow-auto rounded-md border border-gray-200">
          <table class="min-w-full text-xs">
            <thead>
              <tr class="border-b border-gray-100 bg-gray-50 text-left text-gray-500">
                <th class="px-2 py-1">Forma</th>
                <th class="px-2 py-1">Valor Linha</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(pg, idx) in form.auditoria_pagamentos"
                :key="`${pg.tipo_pagamento_descricao || 'N/A'}-${idx}`"
                class="border-b border-gray-100"
              >
                <td class="px-2 py-1">{{ pg.tipo_pagamento_descricao || 'N/A' }}</td>
                <td class="px-2 py-1">{{ pg.valor_linha || '0' }}</td>
              </tr>
              <tr v-if="form.auditoria_pagamentos.length === 0">
                <td colspan="2" class="px-2 py-2 text-gray-500">Nenhum pagamento de auditoria encontrado para a venda.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <template #footer>
      <button
        type="button"
        class="rounded-md border border-gray-200 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
        :disabled="saving"
        @click="emit('update:modelValue', false)"
      >
        Cancelar
      </button>
      <button
        type="button"
        class="rounded-md bg-[#1f4f8a] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#193f6e] disabled:opacity-60"
        :disabled="saving"
        @click="emitSave"
      >
        {{ saving ? 'Salvando...' : 'Salvar ajuste' }}
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { reactive, watch } from "vue";
import BaseInput from "@/components/ui/BaseInput.vue";
import BaseModal from "@/components/ui/BaseModal.vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  row: { type: Object, default: null },
  saving: { type: Boolean, default: false },
  formasPagamento: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:modelValue", "save"]);

const form = reactive({
  valor_final: "",
  status_venda: "F",
  itens: [],
  pagamentos: [],
  auditoria_pagamentos: [],
});

watch(
  () => props.row,
  (row) => {
    form.valor_final = row?.totais?.total_documento || "";
    form.status_venda = ["F", "C"].includes(String(row?.status_venda || "").toUpperCase())
      ? String(row?.status_venda || "").toUpperCase()
      : "F";
    form.itens = (row?.stg?.itens || []).map((item) => ({ ...item }));
    form.pagamentos = (row?.stg?.pagamentos_detalhe || []).map((pg) => ({ ...pg }));
    form.auditoria_pagamentos = (row?.auditoria?.pagamentos_detalhe || []).map((pg) => ({ ...pg }));
  },
  { immediate: true }
);

function toStringOrEmpty(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  return String(value);
}

function handlePagamentoFormaChange(pg, rawValue) {
  const formId = Number(rawValue);
  if (!Number.isInteger(formId) || formId <= 0) {
    pg.id_tipo_pagamento_legado = null;
    pg.tipo_pagamento_descricao_legado = "";
    return;
  }

  const forma = (props.formasPagamento || []).find((item) => Number(item.id_forma) === formId);
  pg.id_tipo_pagamento_legado = formId;
  pg.tipo_pagamento_descricao_legado = forma?.descricao || "";
}

function formatStatus(value) {
  const status = String(value || "").trim().toUpperCase();
  if (status === "F" || status === "C") {
    return status;
  }
  return "-";
}

function formatDateBR(value) {
  if (!value) {
    return "-";
  }

  const text = String(value).trim();
  const directMatch = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (directMatch) {
    return `${directMatch[3]}/${directMatch[2]}/${directMatch[1]}`;
  }

  const date = new Date(text);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "UTC",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
}

function emitSave() {
  emit("save", {
    valor_final: form.valor_final,
    status_venda: form.status_venda,
    itens: form.itens,
    pagamentos: form.pagamentos,
  });
}
</script>
