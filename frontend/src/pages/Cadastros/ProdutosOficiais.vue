<template>
  <section>
    <BaseTable
      title="Produtos Oficiais"
      subtitle="CRUD com busca rapida"
      :columns="columns"
      :rows="rows"
      row-key="id_produto"
      :count="count"
      :next="next"
      :previous="previous"
      :loading="loading"
      :error="error"
      @next="goNext"
      @previous="goPrevious"
    >
      <template #header-extra>
        <div class="flex items-center gap-2">
          <select
            v-model="categoriaFiltro"
            class="appearance-none rounded-md border border-gray-200 bg-white px-3 py-2 text-xs"
            @change="onCategoriaFiltroChange"
          >
            <option value="">Todas as Categorias</option>
            <option v-for="item in categoriaFiltroOptions" :key="item.value" :value="String(item.value)">
              {{ item.label }}
            </option>
          </select>
          <div class="flex items-center gap-2 rounded-md border border-gray-200 bg-white px-2 py-1.5">
            <Search class="h-4 w-4 text-gray-400" />
            <input
              v-model="search"
              type="text"
              placeholder="Buscar produto"
              class="w-44 border-0 bg-transparent p-0 text-xs outline-none"
              @keyup.enter="reload"
            />
          </div>
          <button
            type="button"
            class="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50"
            @click="showExportModal = true"
          >
            <Download class="h-3.5 w-3.5" />
            Exportar
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-1 rounded-md bg-black px-3 py-2 text-xs font-medium text-white hover:bg-gray-800"
            @click="openCreate"
          >
            <Plus class="h-3.5 w-3.5" />
            Novo Cadastro
          </button>
        </div>
      </template>

      <template #cell-custo="{ row }">
        {{ asMoney(row.custo) }}
      </template>

      <template #cell-venda="{ row }">
        {{ asMoney(row.venda) }}
      </template>

      <template #actions="{ row }">
        <div class="inline-flex items-center gap-2">
          <button type="button" class="rounded-md border border-gray-200 p-1.5 text-gray-600 hover:bg-gray-50" @click="openEdit(row)">
            <Pencil class="h-3.5 w-3.5" />
          </button>
          <button type="button" class="rounded-md border border-red-200 p-1.5 text-red-600 hover:bg-red-50" @click="remove(row)">
            <Trash2 class="h-3.5 w-3.5" />
          </button>
        </div>
      </template>
    </BaseTable>

    <BaseModal
      v-model="showModal"
      :title="editing ? 'Editar Produto' : 'Novo Produto'"
      description="Preencha os dados do produto e vincule categorias por raiz."
    >
      <section class="grid gap-3 sm:grid-cols-2">
        <BaseInput v-model="form.id_produto" label="ID Produto" type="number" required />
        <BaseInput v-model="form.produto" label="Nome" required />
        <label class="space-y-1 text-xs">
          <span class="inline-flex items-center gap-1 font-medium text-gray-600">
            Status
            <span class="text-red-500">*</span>
          </span>
          <button
            type="button"
            :aria-pressed="form.status"
            class="inline-flex w-full items-center justify-between rounded-md border border-gray-200 px-3 py-2"
            @click="form.status = !form.status"
          >
            <span class="text-sm font-medium" :class="form.status ? 'text-green-700' : 'text-gray-500'">
              {{ form.status ? 'ATIVO' : 'INATIVO' }}
            </span>
            <span class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors" :class="form.status ? 'bg-green-500' : 'bg-gray-300'">
              <span class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform" :class="form.status ? 'translate-x-6' : 'translate-x-1'" />
            </span>
          </button>
        </label>
        <label class="space-y-1 text-xs">
          <span class="inline-flex items-center gap-1 font-medium text-gray-600">
            Und. Medida
            <span class="text-red-500">*</span>
          </span>
          <select v-model="form.id_und_medida" required class="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm">
            <option value="">Selecione</option>
            <option v-for="option in unidadesOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <CurrencyInput v-model="form.custo" label="Custo" required />
        <CurrencyInput v-model="form.venda" label="Venda" required />
        <PercentInput v-model="form.markup" label="Markup" help-text="Percentual de lucro sobre o custo" />
        <PercentInput v-model="form.markup_inv" label="Markup Inv" help-text="Percentual de margem invertida" />
        <PercentInput v-model="form.perda" label="Perda" />
        <BaseInput
          v-model="form.fisico"
          label="Fisico"
          help-text="Estoque fisico real atual"
          inputmode="decimal"
          @update:model-value="(value) => (form.fisico = normalizeDecimalInput(value, 4))"
        />
        <label class="space-y-1 text-xs">
          <span class="inline-flex items-center gap-1 font-medium text-gray-600">
            AliqEFC
            <span class="group relative inline-flex items-center">
              <HelpCircle class="h-4 w-4 text-gray-400" />
              <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-56 -translate-x-1/2 rounded-md bg-[#1f1f1f] px-2 py-1 text-[11px] font-normal text-white group-hover:block">
                Aliquota de emissor de cupom fiscal
              </span>
            </span>
          </span>
          <select v-model="form.aliqefc" class="w-full appearance-none rounded-md border border-gray-200 bg-white px-3 py-2 text-sm">
            <option value="">Selecione</option>
            <option v-for="option in aliquotasOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <BaseInput v-model="form.cod_g3n" label="Cod G3N" type="number" help-text="Codigo de agrupamento gerencial" />
        <BaseInput v-model="form.cod_rel" label="Cod Rel" type="number" help-text="Codigo de relacionamento para relatorios" />
        <label class="space-y-1 text-xs">
          <span class="font-medium text-gray-600">Usuario</span>
          <input v-model="form.usuario" type="text" class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm" />
        </label>
        <label class="space-y-1 text-xs">
          <span class="font-medium text-gray-600">GTIN</span>
          <input v-model="form.gtin" type="text" class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm" />
        </label>
        <label class="space-y-1 text-xs">
          <span class="font-medium text-gray-600">Barras</span>
          <input v-model="form.barras" type="text" class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm" />
        </label>
        <label class="space-y-1 text-xs sm:col-span-2">
          <span class="font-medium text-gray-600">Ult Mov</span>
          <input v-model="form.ult_mov" type="date" class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm" />
        </label>
      </section>

      <section class="mt-4 rounded-md border border-gray-200 p-3">
        <h4 class="text-xs font-semibold uppercase tracking-wide text-gray-500">Categorias por raiz</h4>
        <p v-if="treeLoading" class="mt-2 text-xs text-gray-500">Carregando arvore...</p>
        <p v-else-if="treeError" class="mt-2 text-xs text-red-600">{{ treeError }}</p>
        <div v-else class="mt-3 grid gap-3 lg:grid-cols-2">
          <div v-for="root in roots" :key="root.id_conta" class="space-y-1">
            <label class="text-xs font-medium text-gray-600">{{ root.nome_conta }}</label>
            <select
              v-model="selectedByRoot[root.id_conta]"
              class="w-full appearance-none rounded-md border border-gray-200 bg-white px-3 py-2 text-sm"
            >
              <option value="">Selecione uma subcategoria</option>
              <option v-for="child in flattenCategorias(root)" :key="child.id_conta" :value="String(child.id_conta)">
                {{ child.label }}
              </option>
            </select>
          </div>
        </div>
      </section>

      <p v-if="modalError" class="mt-3 text-xs text-red-600">{{ modalError }}</p>

      <template #footer>
        <button
          type="button"
          class="rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50"
          @click="showModal = false"
        >
          Cancelar
        </button>
        <button
          type="button"
          class="rounded-md bg-black px-3 py-2 text-xs font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="saving"
          @click="save"
        >
          {{ saving ? 'Salvando...' : 'Salvar' }}
        </button>
      </template>
    </BaseModal>

    <ExportModal
      v-model="showExportModal"
      tabela="produtos"
      :available-columns="exportColumns"
      :loading="exporting"
      :error="exportError"
      @confirm="exportData"
    />
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { Download, HelpCircle, Pencil, Plus, Search, Trash2 } from "lucide-vue-next";
import BaseInput from "@/components/ui/BaseInput.vue";
import CurrencyInput from "@/components/ui/CurrencyInput.vue";
import BaseModal from "@/components/ui/BaseModal.vue";
import PercentInput from "@/components/ui/PercentInput.vue";
import BaseTable from "@/components/ui/BaseTable.vue";
import ExportModal from "@/components/ui/ExportModal.vue";

const API_BASE_URL = "http://127.0.0.1:8000";
const endpoint = `${API_BASE_URL}/api/cadastros/produtos`;

const columns = [
  { key: "id_produto", label: "ID" },
  { key: "produto", label: "Produto" },
  { key: "status", label: "Status" },
  { key: "custo", label: "Custo" },
  { key: "venda", label: "Venda" },
];

const rows = ref([]);
const loading = ref(false);
const error = ref("");
const count = ref(0);
const next = ref("");
const previous = ref("");
const search = ref("");
const categoriaFiltro = ref("");
const categoriaFiltroOptions = ref([]);
const showExportModal = ref(false);
const exporting = ref(false);
const exportError = ref("");

const showModal = ref(false);
const saving = ref(false);
const modalError = ref("");
const editing = ref(null);
const unidadesOptions = ref([]);
const aliquotasOptions = ref([]);
const treeLoading = ref(false);
const treeError = ref("");
const roots = ref([]);
const selectedByRoot = reactive({});

const baseDefaults = {
  id_produto: "",
  produto: "",
  status: true,
  custo: 0,
  venda: 0,
  id_und_medida: "",
  markup: 0,
  markup_inv: 0,
  perda: 0,
  fisico: 0,
  aliqefc: "",
  cod_g3n: 0,
  cod_rel: 0,
  usuario: "",
  gtin: "",
  barras: "",
  ult_mov: "",
};

const form = reactive({ ...baseDefaults });

const exportColumns = [
  { key: "id_produto", label: "ID Produto" },
  { key: "produto", label: "Nome" },
  { key: "status", label: "Status" },
  { key: "custo", label: "Custo" },
  { key: "venda", label: "Venda" },
  { key: "markup", label: "Markup" },
  { key: "markup_inv", label: "Markup Inv" },
  { key: "perda", label: "Perda" },
  { key: "fisico", label: "Fisico" },
  { key: "aliqefc", label: "AliqEFC" },
  { key: "cod_g3n", label: "Cod G3N" },
  { key: "cod_rel", label: "Cod Rel" },
  { key: "usuario", label: "Usuario" },
  { key: "gtin", label: "GTIN" },
  { key: "barras", label: "Barras" },
  { key: "ult_mov", label: "Ult Mov" },
];

function getFilenameFromDisposition(disposition, fallback) {
  const match = disposition?.match(/filename="?([^";]+)"?/i);
  return match?.[1] || fallback;
}

function withSearch(raw = endpoint) {
  const url = new URL(raw);
  if (search.value.trim()) {
    url.searchParams.set("search", search.value.trim());
  }
  if (categoriaFiltro.value !== "") {
    url.searchParams.set("categoria_id", String(categoriaFiltro.value));
  }
  return url.toString();
}

function asMoney(value) {
  return Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function toNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeDecimalInput(value, maxDecimals = 4) {
  const clean = String(value || "").replace(/[^\d,]/g, "");
  const parts = clean.split(",");
  if (parts.length === 1) return parts[0];
  return `${parts[0]},${parts.slice(1).join("").slice(0, maxDecimals)}`;
}

function parseLocaleDecimal(value) {
  return toNumber(String(value || "").replace(/\./g, "").replace(",", "."), 0);
}

async function load(url = endpoint) {
  loading.value = true;
  error.value = "";
  try {
    const response = await fetch(withSearch(url));
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    rows.value = data.results || [];
    count.value = data.count || 0;
    next.value = data.next || "";
    previous.value = data.previous || "";
  } catch (err) {
    console.error(err);
    error.value = "Falha ao carregar produtos.";
  } finally {
    loading.value = false;
  }
}

async function loadUnidades() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/cadastros/unidades-medida`);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    unidadesOptions.value = (data.results || []).map((item) => ({
      value: item.id_und_medida,
      label: `${item.sigla} - ${item.descricao}`,
    }));
  } catch (err) {
    console.error(err);
    unidadesOptions.value = [];
  }
}

async function loadAliquotas() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/cadastros/aliquotas`);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    aliquotasOptions.value = (data.results || []).map((item) => ({
      value: item.descricao || String(item.valor_percentual || ""),
      label: item.descricao || `${item.valor_percentual}%`,
    }));
  } catch (err) {
    console.error(err);
    aliquotasOptions.value = [];
  }
}

function resetForm() {
  Object.assign(form, { ...baseDefaults });
  for (const key of Object.keys(selectedByRoot)) {
    delete selectedByRoot[key];
  }
  modalError.value = "";
}

function flattenCategorias(root) {
  const result = [];
  function visit(nodes, depth) {
    for (const node of nodes || []) {
      const prefix = depth > 0 ? `${"  ".repeat(depth)}- ` : "";
      result.push({ id_conta: node.id_conta, label: `${prefix}${node.codigo_hierarquico} ${node.nome_conta}` });
      visit(node.filhas, depth + 1);
    }
  }
  visit(root.filhas || [], 0);
  return result;
}

function applyCategoriasToRoots(categoriasIds = []) {
  const desired = new Set((categoriasIds || []).map((id) => Number(id)).filter((id) => Number.isFinite(id) && id > 0));
  for (const root of roots.value) {
    selectedByRoot[root.id_conta] = "";
    const match = flattenCategorias(root).find((child) => desired.has(Number(child.id_conta)));
    if (match) selectedByRoot[root.id_conta] = String(match.id_conta);
  }
}

function selectedCategorias() {
  return Object.values(selectedByRoot)
    .filter((id) => id !== "")
    .map((id) => Number(id))
    .filter((id) => Number.isFinite(id) && id > 0);
}

function goNext() {
  if (next.value) load(next.value);
}

function goPrevious() {
  if (previous.value) load(previous.value);
}

async function reload() {
  await load(endpoint);
}

async function openCreate() {
  editing.value = null;
  resetForm();
  await Promise.all([loadUnidades(), loadAliquotas(), loadPlanoContasTree()]);
  showModal.value = true;
}

async function openEdit(row) {
  editing.value = row;
  resetForm();
  await Promise.all([loadUnidades(), loadAliquotas(), loadPlanoContasTree()]);
  Object.assign(form, {
    ...baseDefaults,
    ...row,
    status: String(row.status || "").toUpperCase() === "ATIVO",
    custo: Number(row.custo || 0),
    venda: Number(row.venda || 0),
    markup: Number(row.markup || 0),
    markup_inv: Number(row.markup_inv || 0),
    perda: Number(row.perda || 0),
    fisico: Number(row.fisico || 0),
    id_und_medida: row.id_und_medida || "",
    ult_mov: row.ult_mov || "",
  });
  applyCategoriasToRoots(Array.isArray(row.categorias) ? row.categorias : []);
  showModal.value = true;
}

async function loadPlanoContasTree() {
  treeLoading.value = true;
  treeError.value = "";
  try {
    const response = await fetch(`${API_BASE_URL}/api/cadastros/plano-contas/arvore`);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    roots.value = Array.isArray(data) ? data : [];

    const flattened = [];
    const walk = (nodes, depth) => {
      for (const node of nodes || []) {
        const prefix = depth > 0 ? `${"  ".repeat(depth)}- ` : "";
        flattened.push({
          value: node.id_conta,
          label: `${prefix}${node.codigo_hierarquico} ${node.nome_conta}`,
        });
        walk(node.filhas, depth + 1);
      }
    };
    walk(roots.value, 0);
    categoriaFiltroOptions.value = flattened;

    for (const root of roots.value) {
      selectedByRoot[root.id_conta] = "";
    }
  } catch (err) {
    console.error(err);
    roots.value = [];
    categoriaFiltroOptions.value = [];
    treeError.value = "Nao foi possivel carregar a arvore de plano de contas.";
  } finally {
    treeLoading.value = false;
  }
}

async function onCategoriaFiltroChange() {
  await reload();
}

async function save() {
  saving.value = true;
  modalError.value = "";

  const payload = {
    id_produto: toNumber(form.id_produto),
    produto: String(form.produto || "").trim(),
    status: form.status ? "ATIVO" : "INATIVO",
    custo: Number(form.custo || 0),
    venda: Number(form.venda || 0),
    id_und_medida: form.id_und_medida === "" ? null : toNumber(form.id_und_medida),
    markup: Number(form.markup || 0),
    markup_inv: Number(form.markup_inv || 0),
    perda: Number(form.perda || 0),
    fisico: parseLocaleDecimal(form.fisico),
    aliqefc: String(form.aliqefc || "").trim(),
    cod_g3n: toNumber(form.cod_g3n),
    cod_rel: toNumber(form.cod_rel),
    usuario: String(form.usuario || "").trim(),
    gtin: String(form.gtin || "").trim(),
    barras: String(form.barras || "").trim(),
    ult_mov: form.ult_mov || null,
    categorias: selectedCategorias(),
  };

  try {
    const url = editing.value ? `${endpoint}/${editing.value.id_produto}` : endpoint;
    const method = editing.value ? "PATCH" : "POST";
    const response = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(await response.text());

    showModal.value = false;
    await reload();
  } catch (err) {
    console.error(err);
    modalError.value = "Falha ao salvar produto.";
  } finally {
    saving.value = false;
  }
}

async function remove(row) {
  if (!confirm(`Excluir produto ${row.produto}?`)) return;
  try {
    const response = await fetch(`${endpoint}/${row.id_produto}`, { method: "DELETE" });
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    await reload();
  } catch (err) {
    console.error(err);
    error.value = "Falha ao excluir produto.";
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
          tabela: "produtos",
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
        tabela: "produtos",
        tipo,
        colunas,
        query_sql,
        formato,
        search: search.value.trim(),
      }),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }

    const blob = await response.blob();
    const filename = getFilenameFromDisposition(response.headers.get("Content-Disposition"), `exportacao_produtos.${formato}`);
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
  Promise.all([load(), loadUnidades(), loadAliquotas(), loadPlanoContasTree()]);
});
</script>
