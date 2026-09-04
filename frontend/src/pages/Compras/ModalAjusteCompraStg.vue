<template>
  <BaseModal
    :model-value="modelValue"
    title="Ajustar Compra STG"
    description="Ajuste dados da compra e dos itens. A validacao sera recalculada automaticamente ao salvar."
    @update:model-value="(value) => emit('update:modelValue', value)"
  >
    <div class="space-y-4">
      <p class="text-xs text-gray-700">
        Compra: <strong>{{ row?.compra || '-' }}</strong>
        | Nota: <strong>{{ row?.nota || '-' }}</strong>
        | Emissao: <strong>{{ formatDateBR(row?.data_emissao) }}</strong>
      </p>

      <div class="grid gap-3 sm:grid-cols-2">
        <CurrencyInput v-model="form.valor_total" label="Total Documento" :precision="PRECISAO_MOEDA" />
        <BaseInput :model-value="totalProdutosDisplay" label="Total Produtos (automatico)" readonly />

        <div class="space-y-1 text-xs">
          <span class="inline-flex items-center gap-1 font-medium text-gray-600">Status NFe (somente leitura)</span>
          <p class="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700">
            {{ form.nfe_status || '-' }}
          </p>
        </div>

        <div class="space-y-1 text-xs">
          <span class="inline-flex items-center gap-1 font-medium text-gray-600">Fornecedor Resolvido</span>
          <RemoteSearchSelect
            v-model="form.fornecedor_resolvido_id"
            :endpoint="`${API_BASE_URL}/api/cadastros/fornecedores`"
            value-field="id_fornecedor"
            :format-option-label="formatFornecedorOption"
            :initial-label="form.fornecedor_resolvido_label"
            all-label="Limpar selecao"
            search-placeholder="Pesquisar fornecedor por nome..."
            :min-chars="2"
            :limit="20"
          />
        </div>
      </div>

      <div class="space-y-2">
        <p class="text-xs font-semibold text-gray-700">Itens da Compra</p>
        <div class="max-h-80 overflow-auto rounded-md border border-gray-200">
          <table class="min-w-full text-xs">
            <thead>
              <tr class="border-b border-gray-100 bg-gray-50 text-left text-gray-500">
                <th class="px-2 py-1">ID Item</th>
                <th class="px-2 py-1">Produto Legado</th>
                <th class="px-2 py-1">Und Legado</th>
                <th class="px-2 py-1">Qtd</th>
                <th class="px-2 py-1">Vlr Custo</th>
                <th class="px-2 py-1">Vlr Total</th>
                <th class="px-2 py-1">Produto Resolvido</th>
                <th class="px-2 py-1">Unidade Resolvida</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in form.itens" :key="item.id_stg_item_compra" class="border-b border-gray-100">
                <td class="px-2 py-1">{{ item.id_stg_item_compra }}</td>
                <td class="px-2 py-1">{{ item.nome_produto_legado || item.id_produto_legado || '-' }}</td>
                <td class="px-2 py-1">{{ item.unidade_legado || '-' }}</td>
                <td class="px-2 py-1">
                  <input
                    v-model="item.quantidade"
                    type="text"
                    inputmode="decimal"
                    class="w-20 rounded-md border border-gray-200 px-2 py-1"
                    @input="item.quantidade = limitarDecimais(item.quantidade, PRECISAO_MOEDA.max)"
                    @blur="item.quantidade = formatarQuantidade(item.quantidade)"
                  />
                </td>
                <td class="px-2 py-1">
                  <div class="w-28">
                    <CurrencyInput v-model="item.valor_custo" :precision="PRECISAO_MOEDA" />
                  </div>
                </td>
                <td class="px-2 py-1">
                  <span class="inline-flex rounded-md border border-gray-200 bg-gray-50 px-2 py-1 text-gray-700">
                    {{ asMoney(calcularTotalItem(item)) }}
                  </span>
                </td>
                <td class="px-2 py-1">
                  <RemoteSearchSelect
                    v-model="item.produto_resolvido_id"
                    :endpoint="`${API_BASE_URL}/api/cadastros/produtos`"
                    value-field="id_produto"
                    :format-option-label="formatProdutoOption"
                    :initial-label="item.produto_resolvido_label"
                    all-label="Limpar selecao"
                    search-placeholder="Pesquisar produto..."
                    :min-chars="2"
                    :limit="20"
                  />
                </td>
                <td class="px-2 py-1">
                  <RemoteSearchSelect
                    v-model="item.unidade_resolvida_id"
                    :endpoint="`${API_BASE_URL}/api/cadastros/unidades-medida`"
                    value-field="id_und_medida"
                    :format-option-label="formatUnidadeOption"
                    :initial-label="item.unidade_resolvida_label"
                    all-label="Limpar selecao"
                    search-placeholder="Pesquisar unidade..."
                    :min-chars="0"
                    :limit="80"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <p v-if="error" class="text-xs text-red-600">{{ error }}</p>
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
import { computed, reactive, ref, watch } from "vue";
import BaseInput from "@/components/ui/BaseInput.vue";
import BaseModal from "@/components/ui/BaseModal.vue";
import CurrencyInput from "@/components/ui/CurrencyInput.vue";
import RemoteSearchSelect from "@/components/ui/RemoteSearchSelect.vue";

import { getApiBaseUrl } from "@/services/firebirdSync"
const API_BASE_URL = getApiBaseUrl();

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  row: { type: Object, default: null },
  saving: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "save"]);

// Custo e quantidade legados chegam com ate 6 casas (ex.: 0.103000); arredondar para 2 distorceria os totais.
const PRECISAO_MOEDA = { min: 2, max: 6 };

const error = ref("");

const form = reactive({
  valor_total: 0,
  nfe_status: "",
  fornecedor_resolvido_id: "",
  fornecedor_resolvido_label: "",
  itens: [],
});

const totalProdutosCalculado = computed(() => {
  return form.itens.reduce((acc, item) => acc + calcularTotalItem(item), 0);
});

const totalProdutosDisplay = computed(() => asMoney(totalProdutosCalculado.value));

watch(
  () => props.row,
  (row) => {
    hydrate(row);
  },
  { immediate: true },
);

function hydrate(row) {
  error.value = "";
  form.valor_total = Number(row?.totais?.total_compra ?? 0) || 0;
  form.nfe_status = String(row?.nfe_status ?? "");
  form.fornecedor_resolvido_id = row?.fornecedor_resolvido?.id_fornecedor
    ? String(row.fornecedor_resolvido.id_fornecedor)
    : "";
  form.fornecedor_resolvido_label = row?.fornecedor_resolvido
    ? formatFornecedorOption(row.fornecedor_resolvido)
    : "";

  form.itens = (row?.itens || []).map((item) => ({
    id_stg_item_compra: item.id_stg_item_compra,
    id_produto_legado: item.id_produto_legado,
    nome_produto_legado: item.nome_produto_legado,
    unidade_legado: item.unidade_legado,
    quantidade: formatarQuantidade(item.quantidade),
    valor_custo: Number(item.valor_custo ?? 0) || 0,
    valor_total_calculado: String(item.valor_total_calculado ?? ""),
    produto_resolvido_id: item.produto_resolvido_id ? String(item.produto_resolvido_id) : "",
    produto_resolvido_label: item.produto_resolvido ? formatProdutoOption(item.produto_resolvido) : "",
    unidade_resolvida_id: item.unidade_resolvida_id ? String(item.unidade_resolvida_id) : "",
    unidade_resolvida_label: item.unidade_resolvida ? formatUnidadeOption(item.unidade_resolvida) : "",
  }));
}

function limitarDecimais(value, maxDecimals) {
  const clean = String(value ?? "").replace(/[^\d,]/g, "");
  const parts = clean.split(",");
  if (parts.length === 1) return parts[0];
  return `${parts[0]},${parts.slice(1).join("").slice(0, maxDecimals)}`;
}

function formatarQuantidade(value) {
  const parsed = parseLocaleDecimal(value);
  if (parsed === null) return "";
  return parsed.toLocaleString("pt-BR", {
    minimumFractionDigits: PRECISAO_MOEDA.min,
    maximumFractionDigits: PRECISAO_MOEDA.max,
  });
}

function parseLocaleDecimal(value) {
  const text = String(value ?? "").trim();
  if (!text) return null;

  const normalized = text.includes(",") ? text.replace(/\./g, "").replace(",", ".") : text;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatDateBR(value) {
  if (!value) {
    return "-";
  }

  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) {
    return String(value);
  }

  return `${match[3]}/${match[2]}/${match[1]}`;
}

function asMoney(value) {
  return Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function normalizeDecimal(value) {
  const text = String(value ?? "").trim();
  if (!text) {
    return undefined;
  }
  return text.replace(/\s+/g, "").replace(",", ".");
}

function parseDecimal(value) {
  const normalized = normalizeDecimal(value);
  if (normalized === undefined) {
    return null;
  }
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return parsed;
}

function normalizeInt(value) {
  const text = String(value ?? "").trim();
  if (!text) {
    return undefined;
  }

  const parsed = Number(text);
  if (!Number.isInteger(parsed)) {
    return undefined;
  }

  return parsed;
}

function calcularTotalItem(item) {
  const quantidade = parseLocaleDecimal(item.quantidade);
  const valorCusto = Number(item.valor_custo ?? 0);
  if (quantidade !== null && Number.isFinite(valorCusto)) {
    return quantidade * valorCusto;
  }

  const totalInformado = parseDecimal(item.valor_total_calculado);
  return totalInformado !== null ? totalInformado : 0;
}

function formatDecimalPayload(value) {
  return Number(value || 0).toFixed(6);
}

function formatFornecedorOption(item) {
  return `${item.id_fornecedor} - ${item.nome_fornecedor || "Sem nome"}`;
}

function formatProdutoOption(item) {
  return `${item.id_produto} - ${item.produto || "Sem nome"}`;
}

function formatUnidadeOption(item) {
  const sigla = String(item?.sigla || "").trim();
  const descricao = String(item?.descricao || "").trim();
  const detalhe = descricao ? ` - ${descricao}` : "";
  return `${item.id_und_medida} - ${sigla || "UN"}${detalhe}`;
}

function emitSave() {
  error.value = "";

  const payload = {};

  payload.valor_total = formatDecimalPayload(form.valor_total);
  payload.valor_produtos = formatDecimalPayload(totalProdutosCalculado.value);

  const fornecedorResolvidoId = normalizeInt(form.fornecedor_resolvido_id);
  if (fornecedorResolvidoId !== undefined) {
    payload.fornecedor_resolvido_id = fornecedorResolvidoId;
  }

  payload.itens = form.itens.map((item) => {
    const normalized = {
      id_stg_item_compra: item.id_stg_item_compra,
    };

    normalized.quantidade = formatDecimalPayload(parseLocaleDecimal(item.quantidade));
    normalized.valor_custo = formatDecimalPayload(item.valor_custo);
    normalized.valor_total_calculado = formatDecimalPayload(calcularTotalItem(item));

    const produtoResolvidoId = normalizeInt(item.produto_resolvido_id);
    if (produtoResolvidoId !== undefined) {
      normalized.produto_resolvido_id = produtoResolvidoId;
    }

    const unidadeResolvidaId = normalizeInt(item.unidade_resolvida_id);
    if (unidadeResolvidaId !== undefined) {
      normalized.unidade_resolvida_id = unidadeResolvidaId;
    }

    return normalized;
  });

  emit("save", payload);
}
</script>
