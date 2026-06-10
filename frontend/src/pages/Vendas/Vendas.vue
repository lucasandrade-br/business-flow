<template>
  <section>
    <BaseTable
      title="Vendas"
      subtitle="Consulta operacional com filtros e detalhamento"
      :columns="columns"
      :rows="rows"
      row-key="id_venda"
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
              placeholder="Buscar venda, cliente ou usuario"
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

      <template #cell-valor_total_documento="{ row }">
        {{ asMoney(row.valor_total_documento) }}
      </template>

      <template #cell-momento_consolidacao="{ row }">
        {{ formatDateTime(row.momento_consolidacao) }}
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
      title="Detalhes da Venda"
      description="Visao consolidada de itens e pagamentos da venda selecionada."
    >
      <p v-if="detailsLoading" class="text-xs text-gray-500">Carregando detalhes...</p>
      <p v-else-if="detailsError" class="text-xs text-red-600">{{ detailsError }}</p>

      <div v-else-if="details" class="space-y-4">
        <div class="grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
          <div class="rounded-md border border-gray-200 p-2">
            <p class="text-gray-500">ID Venda</p>
            <p class="font-medium text-gray-800">{{ details.id_venda }}</p>
          </div>
          <div class="rounded-md border border-gray-200 p-2">
            <p class="text-gray-500">ID Legado</p>
            <p class="font-medium text-gray-800">{{ details.id_legado }}</p>
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
            <p class="text-gray-500">Tipo</p>
            <p class="font-medium text-gray-800">{{ details.tipo_documento }}</p>
          </div>
          <div class="rounded-md border border-gray-200 p-2">
            <p class="text-gray-500">Valor Total</p>
            <p class="font-medium text-gray-800">{{ asMoney(details.valor_total_documento) }}</p>
          </div>
          <div class="rounded-md border border-gray-200 p-2">
            <p class="text-gray-500">Consolidacao</p>
            <p class="font-medium text-gray-800">{{ formatDateTime(details.momento_consolidacao) }}</p>
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
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in details.itens || []" :key="item.id_item_venda" class="border-t border-gray-100">
                  <td class="px-3 py-2">{{ item.produto_nome || item.produto }}</td>
                  <td class="px-3 py-2">{{ item.unidade_sigla || '-' }}</td>
                  <td class="px-3 py-2">{{ item.quantidade }}</td>
                  <td class="px-3 py-2">{{ asMoney(item.valor_unitario) }}</td>
                  <td class="px-3 py-2">{{ asMoney(item.valor_total_item) }}</td>
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
                  <td class="px-3 py-2">{{ pg.estorno ? 'Sim' : 'Nao' }}</td>
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
          @click="showDetailsModal = false"
        >
          Fechar
        </button>
      </template>
    </BaseModal>

    <ExportModal
      v-model="showExportModal"
      tabela="vendas"
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
import BaseModal from "@/components/ui/BaseModal.vue";
import BaseTable from "@/components/ui/BaseTable.vue";
import ExportModal from "@/components/ui/ExportModal.vue";

const API_BASE_URL = "http://127.0.0.1:8000";
const endpoint = `${API_BASE_URL}/api/vendas/vendas`;

const columns = [
  { key: "id_venda", label: "ID" },
  { key: "id_legado", label: "ID Legado" },
  { key: "tipo_documento", label: "Tipo" },
  { key: "data_venda", label: "Data" },
  { key: "cliente_nome", label: "Cliente" },
  { key: "usuario_nome", label: "Usuario" },
  { key: "valor_total_documento", label: "Valor" },
  { key: "momento_consolidacao", label: "Consolidacao" },
];

const exportColumns = [
  { key: "id_venda", label: "ID Venda" },
  { key: "id_legado", label: "ID Legado" },
  { key: "tipo_documento", label: "Tipo Documento" },
  { key: "data_venda", label: "Data Venda" },
  { key: "hora_venda", label: "Hora Venda" },
  { key: "status", label: "Status" },
  { key: "cliente", label: "Cliente" },
  { key: "usuario", label: "Usuario" },
  { key: "valor_total_documento", label: "Valor Total" },
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
const tipoDocumento = ref("");
const clienteId = ref("");
const produtoId = ref("");
const formaPagamentoId = ref("");

const clientesOptions = ref([]);
const produtosOptions = ref([]);
const formasOptions = ref([]);

const showDetailsModal = ref(false);
const detailsLoading = ref(false);
const detailsError = ref("");
const details = ref(null);

const showExportModal = ref(false);
const exporting = ref(false);
const exportError = ref("");

function asMoney(value) {
  return Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("pt-BR");
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
    error.value = "Falha ao carregar vendas.";
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

async function openDetails(row) {
  showDetailsModal.value = true;
  detailsLoading.value = true;
  detailsError.value = "";
  details.value = null;

  try {
    const response = await fetch(`${API_BASE_URL}/api/vendas/vendas/${row.id_venda}`);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    details.value = await response.json();
  } catch (err) {
    console.error(err);
    detailsError.value = "Falha ao carregar detalhes da venda.";
  } finally {
    detailsLoading.value = false;
  }
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
          tabela: "vendas",
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
        tabela: "vendas",
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
    const filename = getFilenameFromDisposition(response.headers.get("Content-Disposition"), `exportacao_vendas.${formato}`);
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
