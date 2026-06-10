<template>
  <section>
    <BaseTable
      title="Itens de Venda"
      subtitle="Consulta detalhada dos itens vendidos"
      :columns="columns"
      :rows="rows"
      row-key="id_item_venda"
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
              placeholder="Buscar item, produto ou cliente"
              class="w-52 border-0 bg-transparent p-0 text-xs outline-none"
              @keyup.enter="applyFilters"
            />
          </div>

          <input v-model="dataInicial" type="date" class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs" />
          <input v-model="dataFinal" type="date" class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs" />

          <select v-model="tipoDocumento" class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs">
            <option value="">Todos os Tipos</option>
            <option value="NFCE">NFCE</option>
            <option value="DAV">DAV</option>
          </select>

          <select v-model="clienteId" class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs">
            <option value="">Todos os Clientes</option>
            <option v-for="item in clientesOptions" :key="item.value" :value="String(item.value)">
              {{ item.label }}
            </option>
          </select>

          <select v-model="produtoId" class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs">
            <option value="">Todos os Produtos</option>
            <option v-for="item in produtosOptions" :key="item.value" :value="String(item.value)">
              {{ item.label }}
            </option>
          </select>

          <select v-model="formaPagamentoId" class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs">
            <option value="">Todos os Pagamentos</option>
            <option v-for="item in formasOptions" :key="item.value" :value="String(item.value)">
              {{ item.label }}
            </option>
          </select>

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
            class="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50"
            @click="showExportModal = true"
          >
            <Download class="h-3.5 w-3.5" />
            Exportar
          </button>
        </div>
      </template>

      <template #cell-valor_unitario="{ row }">
        {{ asMoney(row.valor_unitario) }}
      </template>
      <template #cell-valor_total_item="{ row }">
        {{ asMoney(row.valor_total_item) }}
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

    <BaseModal
      v-model="showDetailsModal"
      title="Detalhes do Item"
      description="Informacoes detalhadas do item selecionado."
    >
      <div v-if="selectedRow" class="grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-3">
        <div v-for="field in detailFields" :key="field.label" class="rounded-md border border-gray-200 p-2">
          <p class="text-gray-500">{{ field.label }}</p>
          <p class="font-medium text-gray-800">{{ field.value }}</p>
        </div>
      </div>

      <template #footer>
        <button
          type="button"
          class="rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50"
          @click="showDetailsModal = false"
        >
          Fechar
        </button>
      </template>
    </BaseModal>

    <ExportModal
      v-model="showExportModal"
      tabela="itens_venda"
      :available-columns="exportColumns"
      :loading="exporting"
      :error="exportError"
      @confirm="exportData"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { Download, Eye, Search } from "lucide-vue-next";
import BaseModal from "@/components/ui/BaseModal.vue";
import BaseTable from "@/components/ui/BaseTable.vue";
import ExportModal from "@/components/ui/ExportModal.vue";

const API_BASE_URL = "http://127.0.0.1:8000";
const endpoint = `${API_BASE_URL}/api/vendas/itens`;

const columns = [
  { key: "id_item_venda", label: "ID Item" },
  { key: "id_legado_venda", label: "Venda" },
  { key: "tipo_documento", label: "Tipo" },
  { key: "data_venda", label: "Data" },
  { key: "produto_nome", label: "Produto" },
  { key: "cliente_nome", label: "Cliente" },
  { key: "quantidade", label: "Qtd" },
  { key: "valor_unitario", label: "Vlr Unit" },
  { key: "valor_total_item", label: "Vlr Total" },
];

const exportColumns = [
  { key: "id_item_venda", label: "ID Item" },
  { key: "venda", label: "Venda" },
  { key: "produto", label: "Produto" },
  { key: "unidade_medida", label: "Unidade" },
  { key: "quantidade", label: "Quantidade" },
  { key: "valor_unitario", label: "Valor Unitario" },
  { key: "valor_total_item", label: "Valor Total Item" },
  { key: "cancelado", label: "Cancelado" },
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
const tipoDocumento = ref("");
const clienteId = ref("");
const produtoId = ref("");
const formaPagamentoId = ref("");

const clientesOptions = ref([]);
const produtosOptions = ref([]);
const formasOptions = ref([]);

const showDetailsModal = ref(false);
const selectedRow = ref(null);

const showExportModal = ref(false);
const exporting = ref(false);
const exportError = ref("");

const detailFields = computed(() => {
  const row = selectedRow.value;
  if (!row) return [];
  return [
    { label: "ID Item", value: row.id_item_venda },
    { label: "Venda", value: `${row.id_legado_venda} (${row.tipo_documento})` },
    { label: "Data Venda", value: row.data_venda || "-" },
    { label: "Cliente", value: row.cliente_nome || "-" },
    { label: "Produto", value: row.produto_nome || "-" },
    { label: "Unidade", value: row.unidade_sigla || "-" },
    { label: "Quantidade", value: row.quantidade || "0" },
    { label: "Valor Unitario", value: asMoney(row.valor_unitario) },
    { label: "Valor Total", value: asMoney(row.valor_total_item) },
    { label: "Cancelado", value: row.cancelado ? "Sim" : "Nao" },
  ];
});

function asMoney(value) {
  return Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function getFilenameFromDisposition(disposition, fallback) {
  const match = disposition?.match(/filename="?([^";]+)"?/i);
  return match?.[1] || fallback;
}

function activeFilters() {
  return {
    data_inicial: dataInicial.value || undefined,
    data_final: dataFinal.value || undefined,
    tipo_documento: tipoDocumento.value || undefined,
    cliente_id: clienteId.value || undefined,
    produto_id: produtoId.value || undefined,
    forma_pagamento_id: formaPagamentoId.value || undefined,
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
    error.value = "Falha ao carregar itens de venda.";
  } finally {
    loading.value = false;
  }
}

async function loadClientes() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/cadastros/clientes?limit=200`);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    clientesOptions.value = (data.results || []).map((item) => ({
      value: item.id_cliente,
      label: `${item.id_cliente} - ${item.nome_cliente}`,
    }));
  } catch (err) {
    console.error(err);
    clientesOptions.value = [];
  }
}

async function loadProdutos() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/cadastros/produtos?limit=200`);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    produtosOptions.value = (data.results || []).map((item) => ({
      value: item.id_produto,
      label: `${item.id_produto} - ${item.produto}`,
    }));
  } catch (err) {
    console.error(err);
    produtosOptions.value = [];
  }
}

async function loadFormasPagamento() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/cadastros/formas-pagamento?limit=200`);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    formasOptions.value = (data.results || []).map((item) => ({
      value: item.id_forma,
      label: `${item.id_forma} - ${item.descricao}`,
    }));
  } catch (err) {
    console.error(err);
    formasOptions.value = [];
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
  tipoDocumento.value = "";
  clienteId.value = "";
  produtoId.value = "";
  formaPagamentoId.value = "";
  load(endpoint);
}

function openDetails(row) {
  selectedRow.value = row;
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
          tabela: "itens_venda",
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
        tabela: "itens_venda",
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
    const filename = getFilenameFromDisposition(response.headers.get("Content-Disposition"), `exportacao_itens_venda.${formato}`);
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
  loadClientes();
  loadProdutos();
  loadFormasPagamento();
});
</script>
