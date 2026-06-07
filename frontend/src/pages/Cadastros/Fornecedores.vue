<template>
  <section>
    <BaseTable
      title="Fornecedores"
      subtitle="CRUD com busca rapida"
      :columns="columns"
      :rows="rows"
      row-key="id_fornecedor"
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
          <div class="flex items-center gap-2 rounded-md border border-gray-200 bg-white px-2 py-1.5">
            <Search class="h-4 w-4 text-gray-400" />
            <input
              v-model="search"
              type="text"
              placeholder="Buscar fornecedor"
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

    <BaseFormModal
      v-model="showModal"
      :title="editing ? 'Editar Fornecedor' : 'Novo Fornecedor'"
      :fields="formFields"
      :initial-values="initialValues"
      :saving="saving"
      :error="modalError"
      submit-label="Salvar"
      @submit="save"
    />

    <ExportModal
      v-model="showExportModal"
      tabela="fornecedores"
      :available-columns="exportColumns"
      :loading="exporting"
      :error="exportError"
      @confirm="exportData"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { Download, Pencil, Plus, Search, Trash2 } from "lucide-vue-next";
import BaseFormModal from "@/components/ui/BaseFormModal.vue";
import BaseTable from "@/components/ui/BaseTable.vue";
import ExportModal from "@/components/ui/ExportModal.vue";

const API_BASE_URL = "http://127.0.0.1:8000";
const endpoint = `${API_BASE_URL}/api/cadastros/fornecedores`;

const columns = [
  { key: "id_fornecedor", label: "ID" },
  { key: "nome_fornecedor", label: "Fornecedor" },
  { key: "raz_social", label: "Razao Social" },
  { key: "codigo", label: "Codigo" },
];

const rows = ref([]);
const loading = ref(false);
const error = ref("");
const count = ref(0);
const next = ref("");
const previous = ref("");
const search = ref("");
const showExportModal = ref(false);
const exporting = ref(false);
const exportError = ref("");

const showModal = ref(false);
const saving = ref(false);
const modalError = ref("");
const editing = ref(null);

const exportColumns = [
  { key: "id_fornecedor", label: "ID Fornecedor" },
  { key: "nome_fornecedor", label: "Nome" },
  { key: "raz_social", label: "Razao Social" },
  { key: "dt_cadastro", label: "Data Cadastro" },
  { key: "id_codsis", label: "CodSis" },
  { key: "codigo", label: "Codigo" },
  { key: "operador", label: "Operador" },
  { key: "usuario", label: "Usuario" },
  { key: "hash_md5", label: "Hash" },
];

function getFilenameFromDisposition(disposition, fallback) {
  const match = disposition?.match(/filename="?([^";]+)"?/i);
  return match?.[1] || fallback;
}

function padCodigo(value) {
  const clean = String(value || "").replace(/\D/g, "").slice(0, 5);
  return clean ? clean.padStart(5, "0") : "";
}

const formFields = [
  { name: "id_fornecedor", label: "ID Fornecedor", type: "number", required: true },
  { name: "nome_fornecedor", label: "Nome", type: "text", required: true },
  { name: "raz_social", label: "Razao Social", type: "text" },
  { name: "dt_cadastro", label: "Data Cadastro", type: "date" },
  { name: "id_codsis", label: "ID CodSis", type: "number", helpText: "ID interno do sistema legado" },
  { name: "codigo", label: "Codigo (5)", type: "text", maxlength: 5, onBlur: padCodigo, helpText: "Codigo padrao de 5 digitos" },
  {
    name: "operador",
    label: "Operador",
    type: "select",
    emptyValue: 0,
    placeholder: "0",
    helpText: "Nivel de operacao e acesso: 0, 1 ou 10",
    options: [
      { value: 0, label: "0" },
      { value: 1, label: "1" },
      { value: 10, label: "10" },
    ],
  },
  { name: "usuario", label: "Usuario", type: "text" },
];

const initialValues = computed(() => {
  if (!editing.value) {
    return {
      id_fornecedor: "",
      nome_fornecedor: "",
      raz_social: "",
      dt_cadastro: "",
      id_codsis: "",
      codigo: "",
      operador: 0,
      usuario: "",
    };
  }
  return {
    id_fornecedor: editing.value.id_fornecedor,
    nome_fornecedor: editing.value.nome_fornecedor || "",
    raz_social: editing.value.raz_social || "",
    dt_cadastro: editing.value.dt_cadastro || "",
    id_codsis: editing.value.id_codsis || "",
    codigo: editing.value.codigo || "",
    operador: editing.value.operador || 0,
    usuario: editing.value.usuario || "",
  };
});

function withSearch(raw = endpoint) {
  const url = new URL(raw);
  if (search.value.trim()) {
    url.searchParams.set("search", search.value.trim());
  }
  return url.toString();
}

function toNumberOrNull(value) {
  if (typeof value === "object" && value !== null) {
    value = value.id_codsis ?? value.value ?? null;
  }
  if (value === "" || value === null || value === undefined) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
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
    error.value = "Falha ao carregar fornecedores.";
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

async function reload() {
  await load(endpoint);
}

function openCreate() {
  editing.value = null;
  modalError.value = "";
  showModal.value = true;
}

function openEdit(row) {
  editing.value = row;
  modalError.value = "";
  showModal.value = true;
}

async function save(values) {
  saving.value = true;
  modalError.value = "";

  const payload = {
    id_fornecedor: Number(values.id_fornecedor),
    nome_fornecedor: String(values.nome_fornecedor || "").trim(),
    raz_social: String(values.raz_social || "").trim(),
    dt_cadastro: values.dt_cadastro || null,
    id_codsis: toNumberOrNull(values.id_codsis),
    codigo: padCodigo(values.codigo),
    operador: Number(values.operador || 0),
    usuario: String(values.usuario || "").trim(),
  };

  try {
    const url = editing.value ? `${endpoint}/${editing.value.id_fornecedor}` : endpoint;
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
    modalError.value = "Falha ao salvar fornecedor.";
  } finally {
    saving.value = false;
  }
}

async function remove(row) {
  if (!confirm(`Excluir fornecedor ${row.nome_fornecedor}?`)) return;
  try {
    const response = await fetch(`${endpoint}/${row.id_fornecedor}`, { method: "DELETE" });
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    await reload();
  } catch (err) {
    console.error(err);
    error.value = "Falha ao excluir fornecedor.";
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
          tabela: "fornecedores",
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
        tabela: "fornecedores",
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
    const filename = getFilenameFromDisposition(response.headers.get("Content-Disposition"), `exportacao_fornecedores.${formato}`);
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
