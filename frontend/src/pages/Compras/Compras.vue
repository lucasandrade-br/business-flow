<template>
  <section>
    <BaseTable
      title="Compras"
      subtitle="Consulta operacional de compras oficiais"
      :columns="columns"
      :rows="rows"
      row-key="id_compra"
      :count="count"
      :next="next"
      :previous="previous"
      :loading="loading"
      :error="error"
      @next="goNext"
      @previous="goPrevious"
    >
      <template #header-extra>
        <div class="flex flex-wrap items-center gap-2">
          <div class="flex items-center gap-2 rounded-md border border-gray-200 bg-white px-2 py-1.5">
            <Search class="h-4 w-4 text-gray-400" />
            <input
              v-model="search"
              type="text"
              placeholder="Buscar compra, nota ou fornecedor"
              class="w-56 border-0 bg-transparent p-0 text-xs outline-none"
              @keyup.enter="applyFilters"
            />
          </div>

          <DateRangeField v-model:start="dataInicial" v-model:end="dataFinal" />

          <RemoteSearchSelect
            v-model="fornecedorId"
            :endpoint="`${API_BASE_URL}/api/cadastros/fornecedores`"
            value-field="id_fornecedor"
            :format-option-label="formatFornecedorOption"
            all-label="Todos os Fornecedores"
            search-placeholder="Pesquisar fornecedor por nome..."
            :min-chars="2"
            :limit="20"
          />

          <RemoteSearchSelect
            v-model="produtoId"
            :endpoint="`${API_BASE_URL}/api/cadastros/produtos`"
            value-field="id_produto"
            :format-option-label="formatProdutoOption"
            all-label="Todos os Produtos"
            search-placeholder="Pesquisar produto por nome..."
            :min-chars="2"
            :limit="20"
          />

          <input
            v-model="nfeStatus"
            type="text"
            placeholder="Status NFe"
            class="rounded-md border border-gray-200 px-2 py-1.5 text-xs"
            @keyup.enter="applyFilters"
          />

          <button
            type="button"
            class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50"
            @click="applyFilters"
          >
            Filtrar
          </button>
          <button
            type="button"
            class="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 hover:bg-gray-50"
            @click="clearFilters"
          >
            Limpar
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-black px-3 py-2 text-xs font-medium text-white hover:opacity-95"
            @click="showExportModal = true"
          >
            <Download class="h-3.5 w-3.5" />
            Exportar
          </button>
        </div>
      </template>

      <template #cell-compra_ref="{ row }">
        <span class="font-semibold text-[#373435]">{{ formatCompraRef(row) }}</span>
      </template>

      <template #cell-valor_total_documento="{ row }">
        {{ asMoney(row.valor_total_documento) }}
      </template>

      <template #cell-status_nfe="{ row }">
        <span class="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-semibold text-gray-700">
          {{ row.nfe_status || 'N/A' }}
        </span>
      </template>

      <template #actions="{ row }">
        <button
          type="button"
          class="inline-flex items-center gap-1 rounded-md border border-gray-200 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
          @click="openDetails(row)"
        >
          <Eye class="h-3.5 w-3.5" />
          Detalhes
        </button>
      </template>
    </BaseTable>

    <CompraDetailsModal v-model="showDetailsModal" :compra-id="activeCompraId" />

    <ExportModal
      v-model="showExportModal"
      tabela="compras"
      :available-columns="exportColumns"
      :loading="exporting"
      :error="exportError"
      @confirm="exportData"
    />
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { Download, Eye, Search } from "lucide-vue-next";
import BaseTable from "@/components/ui/BaseTable.vue";
import DateRangeField from "@/components/ui/DateRangeField.vue";
import ExportModal from "@/components/ui/ExportModal.vue";
import RemoteSearchSelect from "@/components/ui/RemoteSearchSelect.vue";
import CompraDetailsModal from "@/components/compras/CompraDetailsModal.vue";

const API_BASE_URL = "http://127.0.0.1:8000";
const endpoint = `${API_BASE_URL}/api/compras/compras`;

const columns = [
  { key: "compra_ref", label: "Compra" },
  { key: "data_emissao", label: "Emissao" },
  { key: "fornecedor_nome", label: "Fornecedor" },
  { key: "valor_total_documento", label: "Valor" },
  { key: "status_nfe", label: "Status NFe" },
];

const exportColumns = [
  { key: "id_compra", label: "ID Compra" },
  { key: "id_legado", label: "ID Legado" },
  { key: "nota", label: "Nota" },
  { key: "fornecedor", label: "Fornecedor" },
  { key: "data_emissao", label: "Data Emissao" },
  { key: "data_lanc", label: "Data Lancamento" },
  { key: "valor_produtos", label: "Valor Produtos" },
  { key: "valor_total_documento", label: "Valor Total" },
  { key: "nfe_status", label: "Status NFe" },
  { key: "momento_consolidacao", label: "Momento Consolidacao" },
];

const rows = ref([]);
const loading = ref(false);
const error = ref("");
const count = ref(0);
const next = ref("");
const previous = ref("");

const search = ref("");
const dataInicial = ref("");
const dataFinal = ref("");
const fornecedorId = ref("");
const produtoId = ref("");
const nfeStatus = ref("");

const showDetailsModal = ref(false);
const activeCompraId = ref(null);

const showExportModal = ref(false);
const exporting = ref(false);
const exportError = ref("");

function asMoney(value) {
  return Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatCompraRef(row) {
  return `COMPRA #${row?.id_legado ?? ""}`;
}

function formatFornecedorOption(item) {
  return `${item.id_fornecedor} - ${item.nome_fornecedor}`;
}

function formatProdutoOption(item) {
  return `${item.id_produto} - ${item.produto}`;
}

function getFilenameFromDisposition(disposition, fallback) {
  const match = disposition?.match(/filename="?([^";]+)"?/i);
  return match?.[1] || fallback;
}

function activeFilters() {
  return {
    data_inicial: dataInicial.value || undefined,
    data_final: dataFinal.value || undefined,
    fornecedor_id: fornecedorId.value || undefined,
    produto_id: produtoId.value || undefined,
    nfe_status: nfeStatus.value || undefined,
  };
}

function withFilters(raw = endpoint) {
  const url = new URL(raw);
  if (search.value.trim()) {
    url.searchParams.set("search", search.value.trim());
  }

  const filtros = activeFilters();
  for (const [key, value] of Object.entries(filtros)) {
    if (value !== undefined && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }

  return url.toString();
}

async function load(url = endpoint) {
  loading.value = true;
  error.value = "";
  try {
    const response = await fetch(withFilters(url));
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    rows.value = data.results || [];
    count.value = data.count || 0;
    next.value = data.next || "";
    previous.value = data.previous || "";
  } catch (err) {
    console.error(err);
    error.value = "Falha ao carregar compras.";
  } finally {
    loading.value = false;
  }
}

function goNext() {
  if (next.value) load(next.value);
}

function goPrevious() {
  if (previous.value) load(previous.value);
}

function applyFilters() {
  load(endpoint);
}

function clearFilters() {
  search.value = "";
  dataInicial.value = "";
  dataFinal.value = "";
  fornecedorId.value = "";
  produtoId.value = "";
  nfeStatus.value = "";
  load(endpoint);
}

function openDetails(row) {
  activeCompraId.value = row.id_compra;
  showDetailsModal.value = true;
}

async function exportData({ tipo, colunas, query_sql, formato, salvar_nome }) {
  exporting.value = true;
  exportError.value = "";

  try {
    if (salvar_nome) {
      const saveResponse = await fetch(`${API_BASE_URL}/api/cadastros/templates-exportacao/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nome: salvar_nome,
          tabela: "compras",
          tipo,
          colunas_selecionadas: tipo === "BASICO" ? colunas : null,
          query_sql: tipo === "SQL" ? query_sql : null,
        }),
      });
      if (!saveResponse.ok) {
        throw new Error(await saveResponse.text());
      }
    }

    const response = await fetch(`${API_BASE_URL}/api/cadastros/exportar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tabela: "compras",
        tipo,
        colunas,
        query_sql,
        formato,
        search: search.value.trim(),
        filtros: activeFilters(),
      }),
    });

    if (!response.ok) {
      throw new Error(await response.text());
    }

    const blob = await response.blob();
    const filename = getFilenameFromDisposition(response.headers.get("Content-Disposition"), `exportacao_compras.${formato}`);
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.style.display = "none";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);

    showExportModal.value = false;
  } catch (err) {
    console.error(err);
    exportError.value = "Falha ao exportar dados.";
  } finally {
    exporting.value = false;
  }
}

onMounted(() => {
  load();
});
</script>
