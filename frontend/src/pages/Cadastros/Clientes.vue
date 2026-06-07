<template>
  <section>
    <BaseTable
      title="Clientes"
      subtitle="CRUD com busca rapida"
      :columns="columns"
      :rows="rows"
      row-key="id_cliente"
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
              placeholder="Buscar cliente"
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
      :title="editing ? 'Editar Cliente' : 'Novo Cliente'"
      :fields="formFields"
      :initial-values="initialValues"
      :saving="saving"
      :error="modalError"
      submit-label="Salvar"
      @submit="save"
    />

    <ExportModal
      v-model="showExportModal"
      tabela="clientes"
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
const endpoint = `${API_BASE_URL}/api/cadastros/clientes`;

const columns = [
  { key: "id_cliente", label: "ID" },
  { key: "nome_cliente", label: "Cliente" },
  { key: "raz_social", label: "Razao Social" },
  { key: "prazo_cob", label: "Prazo Cob" },
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
const gruposOptions = ref([]);
const tiposVendaOptions = ref([]);

const exportColumns = [
  { key: "id_cliente", label: "ID Cliente" },
  { key: "nome_cliente", label: "Nome" },
  { key: "raz_social", label: "Razao Social" },
  { key: "prazo_cob", label: "Prazo Cob" },
  { key: "id_grupo", label: "Grupo" },
  { key: "id_tipo_venda", label: "Tipo Venda" },
  { key: "hash_md5", label: "Hash" },
];

function getFilenameFromDisposition(disposition, fallback) {
  const match = disposition?.match(/filename="?([^";]+)"?/i);
  return match?.[1] || fallback;
}

const formFields = computed(() => [
  { name: "id_cliente", label: "ID Cliente", type: "number", required: true },
  { name: "nome_cliente", label: "Nome", type: "text", required: true },
  { name: "raz_social", label: "Razao Social", type: "text" },
  { name: "prazo_cob", label: "Prazo Cob", type: "number", required: true },
  {
    name: "id_grupo",
    label: "Grupo",
    type: "select",
    emptyValue: "",
    placeholder: "Selecione",
    options: gruposOptions.value,
  },
  {
    name: "id_tipo_venda",
    label: "Tipo Venda",
    type: "select",
    emptyValue: "",
    placeholder: "Selecione",
    options: tiposVendaOptions.value,
  },
]);

const initialValues = computed(() => {
  if (!editing.value) {
    return {
      id_cliente: "",
      nome_cliente: "",
      raz_social: "",
      prazo_cob: 0,
      id_grupo: "",
      id_tipo_venda: "",
    };
  }
  return {
    id_cliente: editing.value.id_cliente,
    nome_cliente: editing.value.nome_cliente || "",
    raz_social: editing.value.raz_social || "",
    prazo_cob: editing.value.prazo_cob || 0,
    id_grupo: editing.value.id_grupo || "",
    id_tipo_venda: editing.value.id_tipo_venda || "",
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
    error.value = "Falha ao carregar clientes.";
  } finally {
    loading.value = false;
  }
}

async function loadGrupos() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/cadastros/grupos-cliente`);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    gruposOptions.value = (data.results || []).map((item) => ({
      value: item.id_grupo,
      label: item.descricao,
    }));
  } catch (err) {
    console.error(err);
    gruposOptions.value = [];
  }
}

async function loadTiposVenda() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/cadastros/tipos-venda`);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    tiposVendaOptions.value = (data.results || []).map((item) => ({
      value: item.id_tipo_venda,
      label: item.descricao,
    }));
  } catch (err) {
    console.error(err);
    tiposVendaOptions.value = [];
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
    id_cliente: Number(values.id_cliente),
    nome_cliente: String(values.nome_cliente || "").trim(),
    raz_social: String(values.raz_social || "").trim(),
    prazo_cob: Number(values.prazo_cob || 0),
    id_grupo: toNumberOrNull(values.id_grupo),
    id_tipo_venda: toNumberOrNull(values.id_tipo_venda),
  };

  try {
    const url = editing.value ? `${endpoint}/${editing.value.id_cliente}` : endpoint;
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
    modalError.value = "Falha ao salvar cliente.";
  } finally {
    saving.value = false;
  }
}

async function remove(row) {
  if (!confirm(`Excluir cliente ${row.nome_cliente}?`)) return;
  try {
    const response = await fetch(`${endpoint}/${row.id_cliente}`, { method: "DELETE" });
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    await reload();
  } catch (err) {
    console.error(err);
    error.value = "Falha ao excluir cliente.";
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
          tabela: "clientes",
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
        tabela: "clientes",
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
    const filename = getFilenameFromDisposition(response.headers.get("Content-Disposition"), `exportacao_clientes.${formato}`);
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
  Promise.all([load(), loadGrupos(), loadTiposVenda()]);
});
</script>
