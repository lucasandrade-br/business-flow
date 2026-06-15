<template>
  <section class="space-y-4">
    <article class="rounded-md border border-gray-200 bg-white p-4">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 class="text-sm font-semibold text-[#373435]">Hub de Validação</h2>
          <p class="mt-1 text-xs text-gray-500">Consolida pendências de produtos, clientes e fornecedores.</p>
        </div>
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div class="flex items-center gap-2 rounded-md border border-gray-200 bg-white px-2 py-1.5">
            <Search class="h-4 w-4 text-gray-400" />
            <input
              v-model="search"
              type="text"
              placeholder="Buscar na aba ativa"
              class="w-52 border-0 bg-transparent p-0 text-xs outline-none"
            />
          </div>
          <button
            type="button"
            class="inline-flex items-center gap-2 rounded-md border border-gray-200 px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="syncing"
            @click="sincronizar"
          >
            <RefreshCw class="h-3.5 w-3.5" :class="syncing ? 'animate-spin' : ''" />
            {{ syncing ? "Sincronizando..." : "Sincronizar ERP" }}
          </button>
        </div>
      </div>
    </article>

    <div class="grid gap-3 md:grid-cols-3">
      <button
        v-for="card in cards"
        :key="card.key"
        type="button"
        class="rounded-md border p-4 text-left transition"
        :class="activeEntity === card.key ? 'border-[#a82631] bg-[#fff5f6]' : 'border-gray-200 bg-white hover:border-gray-300'"
        @click="selectEntity(card.key)"
      >
        <div class="flex items-start justify-between">
          <div>
            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">{{ card.title }}</p>
            <p class="mt-1 text-xs text-gray-500">{{ card.subtitle }}</p>
          </div>
          <span class="rounded-full bg-[#a82631] px-2 py-0.5 text-xs font-semibold text-white">{{ summary[card.key] || 0 }}</span>
        </div>
      </button>
    </div>

    <BaseTable
      :title="tableTitle"
      :subtitle="tableSubtitle"
      :columns="tableColumns"
      :rows="rows"
      :row-key="rowKey"
      :count="count"
      :next="next"
      :previous="previous"
      :loading="loading"
      :error="error"
      empty-text="Nenhum produto pendente."
      @next="goNext"
      @previous="goPrevious"
    >
      <template #header-extra>
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:w-full">
          <div class="flex items-center gap-2">
            <span class="rounded-md border border-gray-200 px-2 py-1 text-xs text-gray-600">{{ rows.length }} nesta pagina</span>
            <label class="inline-flex items-center gap-1 text-xs text-gray-700">
              <input :checked="allPaginaSelecionada" type="checkbox" @change="toggleSelecionarTodos($event.target.checked)" />
              Selecionar todos da pagina
            </label>
          </div>

          <div class="flex items-center gap-2">
            <button
              type="button"
              class="rounded-md border border-[#03ad12] px-3 py-1.5 text-xs text-[#03ad12] hover:bg-[#d7fce1] disabled:opacity-60"
              :disabled="!selectedRows.length || applyingBatch"
              @click="validarSelecionados"
            >
              {{ applyingBatch ? "Processando..." : "Validar Selecionados" }}
            </button>
            <button
              type="button"
              class="rounded-md border border-[#a82631] px-3 py-1.5 text-xs text-[#a82631] hover:bg-[#fff5f6] disabled:opacity-60"
              :disabled="!selectedRows.length || applyingBatch"
              @click="negligenciarSelecionados"
            >
              {{ applyingBatch ? "Processando..." : "Negligenciar Selecionados" }}
            </button>
          </div>
        </div>
      </template>

      <template #cell-select="{ row }">
        <div class="flex cursor-pointer items-center" @click="toggleLinha(row)">
          <input
            :checked="selectedMap[getRowKeyValue(row)] || false"
            type="checkbox"
            @click.stop
            @change="toggleRow(row, $event.target.checked)"
          />
        </div>
      </template>

      <template #cell-custo="{ row }">
        {{ asMoney(row.custo) }}
      </template>

      <template #cell-valor_venda="{ row }">
        {{ asMoney(row.valor_venda) }}
      </template>

      <template #cell-tipo_pendencia="{ row }">
        <span
          v-if="row.tipo_pendencia"
          class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium"
          :class="row.tipo_pendencia === 'ATUALIZACAO' ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'"
        >
          {{ row.tipo_pendencia === "ATUALIZACAO" ? "Divergencia" : "Novo" }}
        </span>
        <span v-else class="text-xs text-gray-500">-</span>
      </template>

      <template #cell-divergencias_resumo="{ row }">
        <div v-if="row.tipo_pendencia === 'ATUALIZACAO'" class="space-y-1">
          <div class="flex flex-wrap items-center gap-1">
            <span
              v-if="getResumoDivergencias(row).alta > 0"
              class="inline-flex rounded-full bg-red-100 px-2 py-0.5 text-[11px] font-medium text-red-700"
            >
              Alta: {{ getResumoDivergencias(row).alta }}
            </span>
            <span
              v-if="getResumoDivergencias(row).media > 0"
              class="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-700"
            >
              Media: {{ getResumoDivergencias(row).media }}
            </span>
            <span
              v-if="getResumoDivergencias(row).leve > 0"
              class="inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-[11px] font-medium text-blue-700"
            >
              Leve: {{ getResumoDivergencias(row).leve }}
            </span>
            <span
              v-for="campo in obterCamposDivergentes(row)"
              :key="`${getRowKeyValue(row)}-${campo}`"
              class="inline-flex rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-[11px] font-medium text-gray-700"
            >
              {{ campo }}
            </span>
          </div>
          <div class="flex max-w-[320px] flex-wrap gap-1">
            
            <span
              v-if="!obterCamposDivergentes(row).length"
              class="inline-flex rounded-full border border-gray-200 bg-white px-2 py-0.5 text-[11px] font-medium text-gray-500"
            >
              Sem detalhe
            </span>
          </div>
          <p class="max-w-[280px] truncate text-[11px] text-gray-500">{{ detalheRapidoDivergencia(row) }}</p>
        </div>
        <span v-else class="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-[11px] font-medium text-green-700">
          Registro novo
        </span>
      </template>

      <template #cell-dt_cadastro="{ row }">
        {{ row.dt_cadastro || '-' }}
      </template>

      <template #actions="{ row }">
        <button
          type="button"
          class="rounded-md border border-gray-200 px-3 py-1.5 text-xs text-[#373435] hover:bg-gray-50"
          @click="openModal(row)"
        >
          Analisar
        </button>
      </template>
    </BaseTable>

    <ModalAprovacaoProduto
      v-model="showProdutoModal"
      :produto="selected"
      @approved="onApproved"
    />

    <ModalAprovacaoCliente
      v-model="showClienteModal"
      :cliente="selected"
      @approved="onApproved"
    />

    <ModalAprovacaoFornecedor
      v-model="showFornecedorModal"
      :fornecedor="selected"
      @approved="onApproved"
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RefreshCw, Search } from "lucide-vue-next";
import BaseTable from "@/components/ui/BaseTable.vue";
import ModalAprovacaoCliente from "@/pages/Validacao/ModalAprovacaoCliente.vue";
import ModalAprovacaoFornecedor from "@/pages/Validacao/ModalAprovacaoFornecedor.vue";
import ModalAprovacaoProduto from "@/pages/Validacao/ModalAprovacaoProduto.vue";
import { executarSincronizacaoFirebird, formatarErroSincronizacao, getApiBaseUrl } from "@/services/firebirdSync";

const API_BASE_URL = getApiBaseUrl();

const cards = [
  { key: "produtos", title: "Produtos", subtitle: "Catálogo de itens" },
  { key: "clientes", title: "Clientes", subtitle: "Carteira comercial" },
  { key: "fornecedores", title: "Fornecedores", subtitle: "Base de compras" },
];

const columnsByEntity = {
  produtos: [
    { key: "select", label: "Sel" },
    { key: "id_produto", label: "ID" },
    { key: "nome", label: "Produto" },
    { key: "tipo_pendencia", label: "Status" },
    { key: "divergencias_resumo", label: "Divergencias" },
    { key: "custo", label: "Custo" },
    { key: "valor_venda", label: "Venda" },
  ],
  clientes: [
    { key: "select", label: "Sel" },
    { key: "id_cliente", label: "ID" },
    { key: "nome_cliente", label: "Cliente" },
    { key: "tipo_pendencia", label: "Status" },
    { key: "divergencias_resumo", label: "Divergencias" },
    { key: "raz_social", label: "Razao Social" },
  ],
  fornecedores: [
    { key: "select", label: "Sel" },
    { key: "id_fornecedor", label: "ID" },
    { key: "nome_fornecedor", label: "Fornecedor" },
    { key: "tipo_pendencia", label: "Status" },
    { key: "divergencias_resumo", label: "Divergencias" },
    { key: "raz_social", label: "Razao Social" },
    { key: "dt_cadastro", label: "Cadastro" },
  ],
};

const endpointByEntity = {
  produtos: `${API_BASE_URL}/api/validacao/produtos/pendentes`,
  clientes: `${API_BASE_URL}/api/validacao/clientes/pendentes`,
  fornecedores: `${API_BASE_URL}/api/validacao/fornecedores/pendentes`,
};

const rows = ref([]);
const loading = ref(false);
const error = ref("");
const count = ref(0);
const next = ref("");
const previous = ref("");

const syncing = ref(false);
const activeEntity = ref("produtos");
const summary = ref({ produtos: 0, clientes: 0, fornecedores: 0 });
const search = ref("");
let searchDebounce = null;
const applyingBatch = ref(false);
const selectedMap = ref({});

const showProdutoModal = ref(false);
const showClienteModal = ref(false);
const showFornecedorModal = ref(false);
const selected = ref(null);
const toast = ref("");

const rowKey = computed(() => {
  if (activeEntity.value === "clientes") return "id_cliente";
  if (activeEntity.value === "fornecedores") return "id_fornecedor";
  return "id_produto";
});

const tableColumns = computed(() => columnsByEntity[activeEntity.value]);

const tableTitle = computed(() => {
  if (activeEntity.value === "clientes") return "Clientes Pendentes";
  if (activeEntity.value === "fornecedores") return "Fornecedores Pendentes";
  return "Produtos Pendentes";
});

const tableSubtitle = computed(() => "Itens de staging aguardando aprovação");
const selectedRows = computed(() => rows.value.filter((row) => selectedMap.value[getRowKeyValue(row)]));
const allPaginaSelecionada = computed(() => rows.value.length > 0 && selectedRows.value.length === rows.value.length);

function asMoney(value) {
  return Number(value || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function getResumoDivergencias(row) {
  const fallback = {
    total: 0,
    alta: 0,
    media: 0,
    leve: 0,
    campos: [],
  };

  const resumo = row?.divergencias_resumo;
  if (resumo && typeof resumo === "object") {
    return {
      total: Number(resumo.total || 0),
      alta: Number(resumo.alta || 0),
      media: Number(resumo.media || 0),
      leve: Number(resumo.leve || 0),
      campos: Array.isArray(resumo.campos) ? resumo.campos : [],
    };
  }

  const divergencias = Array.isArray(row?.divergencias) ? row.divergencias : [];
  return {
    ...fallback,
    total: divergencias.length,
    alta: divergencias.filter((item) => item?.gravidade === "alta").length,
    media: divergencias.filter((item) => item?.gravidade === "media").length,
    leve: divergencias.filter((item) => item?.gravidade === "leve").length,
    campos: divergencias.map((item) => item?.label).filter(Boolean),
  };
}

function obterCamposDivergentes(row) {
  const campos = getResumoDivergencias(row).campos;
  return [...new Set(campos)];
}

function detalheRapidoDivergencia(row) {
  const divergencias = Array.isArray(row?.divergencias) ? row.divergencias : [];
  if (!divergencias.length) {
    return "Sem detalhes adicionais";
  }

  const principal = divergencias[0];
  const label = principal?.label || "Campo";
  const sor = principal?.valor_sor ?? "-";
  const sot = principal?.valor_sot ?? "-";
  return `${label}: ${sor} -> ${sot}`;
}

function notify(message) {
  toast.value = message;
  setTimeout(() => {
    toast.value = "";
  }, 2500);
}

function getRowKeyValue(row) {
  if (activeEntity.value === "clientes") return String(row.id_cliente);
  if (activeEntity.value === "fornecedores") return String(row.id_fornecedor);
  return String(row.id_produto);
}

function clearSelection() {
  selectedMap.value = {};
}

function toggleRow(row, checked) {
  selectedMap.value[getRowKeyValue(row)] = Boolean(checked);
}

function toggleLinha(row) {
  const key = getRowKeyValue(row);
  selectedMap.value[key] = !Boolean(selectedMap.value[key]);
}

function toggleSelecionarTodos(checked) {
  const next = { ...selectedMap.value };
  for (const row of rows.value) {
    next[getRowKeyValue(row)] = Boolean(checked);
  }
  selectedMap.value = next;
}

async function loadResumo() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/resumo`);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    summary.value = {
      produtos: Number(data.produtos || 0),
      clientes: Number(data.clientes || 0),
      fornecedores: Number(data.fornecedores || 0),
    };
  } catch (err) {
    console.error(err);
  }
}

function baseEndpoint() {
  return endpointByEntity[activeEntity.value];
}

function endpointWithSearch(raw = baseEndpoint()) {
  const url = new URL(raw);
  url.searchParams.set("page_size", "100");
  if (search.value.trim()) {
    url.searchParams.set("search", search.value.trim());
  } else {
    url.searchParams.delete("search");
  }
  return url.toString();
}

async function load(url = baseEndpoint()) {
  loading.value = true;
  error.value = "";

  try {
    const response = await fetch(endpointWithSearch(url));
    if (!response.ok) {
      throw new Error(`Erro ${response.status}`);
    }

    const data = await response.json();
    rows.value = data.results || [];
    count.value = data.count || 0;
    next.value = data.next || "";
    previous.value = data.previous || "";
    clearSelection();
  } catch (err) {
    console.error(err);
    error.value = "Nao foi possivel carregar os produtos pendentes.";
  } finally {
    loading.value = false;
  }
}

function goNext() {
  if (next.value) {
    load(next.value);
  }
}

function goPrevious() {
  if (previous.value) {
    load(previous.value);
  }
}

function openModal(row) {
  selected.value = row;
  if (activeEntity.value === "clientes") {
    showClienteModal.value = true;
    return;
  }
  if (activeEntity.value === "fornecedores") {
    showFornecedorModal.value = true;
    return;
  }
  showProdutoModal.value = true;
}

async function selectEntity(entity) {
  activeEntity.value = entity;
  clearSelection();
  await load(baseEndpoint());
}

async function aplicarLotePendencias(acao) {
  if (!selectedRows.value.length) {
    return;
  }

  applyingBatch.value = true;
  try {
    const ids = selectedRows.value.map((row) => Number(getRowKeyValue(row))).filter((id) => Number.isFinite(id));
    const response = await fetch(`${API_BASE_URL}/api/validacao/pendencias/tratar-lote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        entidade: activeEntity.value,
        acao,
        ids,
      }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `Erro ${response.status}`);
    }

    const totalFalhas = Array.isArray(payload.falhas) ? payload.falhas.length : 0;
    const msg = totalFalhas > 0
      ? `${payload.detail || "Tratamento em lote concluido."} Falhas: ${totalFalhas}.`
      : (payload.detail || "Tratamento em lote concluido.");

    notify(msg);
    await loadResumo();
    await load(baseEndpoint());
  } catch (err) {
    console.error(err);
    notify(err?.message || "Falha ao processar lote.");
  } finally {
    applyingBatch.value = false;
  }
}

function validarSelecionados() {
  return aplicarLotePendencias("validar");
}

function negligenciarSelecionados() {
  return aplicarLotePendencias("negligenciar");
}

watch(search, () => {
  if (searchDebounce) {
    clearTimeout(searchDebounce);
  }
  searchDebounce = setTimeout(() => {
    load(baseEndpoint());
  }, 300);
});

async function sincronizar() {
  syncing.value = true;
  try {
    await executarSincronizacaoFirebird(`${API_BASE_URL}/api/integracao/sincronizar`, {}, {
      allowBrowserUploadFallback: false,
    });

    notify("Sincronizacao concluida com sucesso.");
    await loadResumo();
    await load(baseEndpoint());
  } catch (err) {
    console.error(err);
    notify(formatarErroSincronizacao(err, "Falha ao sincronizar o ERP."));
  } finally {
    syncing.value = false;
  }
}

async function onApproved() {
  notify("Registro aprovado com sucesso.");
  await loadResumo();
  await load(baseEndpoint());
}

onMounted(() => {
  loadResumo();
  load();
});

onBeforeUnmount(() => {
  if (searchDebounce) {
    clearTimeout(searchDebounce);
  }
});
</script>
