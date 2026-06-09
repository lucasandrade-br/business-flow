<template>
  <section class="space-y-4">
    <header>
      <h2 class="text-sm font-semibold text-[#373435]">Parâmetros</h2>
      <p class="mt-1 text-xs text-gray-500">Gestão centralizada de tabelas auxiliares e relacionais.</p>
    </header>

    <nav class="border-b border-gray-200">
      <ul class="flex flex-wrap gap-1">
        <li v-for="tab in tabs" :key="tab.key">
          <button
            type="button"
            class="-mb-px border-b-4 px-3 py-2 text-xs font-medium transition-colors"
            :class="activeTab === tab.key ? 'border-black text-[#373435]' : 'border-transparent text-gray-500 hover:text-[#373435]'"
            @click="selectTab(tab.key)"
          >
            {{ tab.label }}
          </button>
        </li>
      </ul>
    </nav>

    <BaseTable
      :title="current.title"
      subtitle="CRUD e busca rápida"
      :columns="current.columns"
      :rows="rows"
      :row-key="current.rowKey"
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
              placeholder="Buscar"
              class="w-44 border-0 bg-transparent p-0 text-xs outline-none"
              @keyup.enter="reload"
            />
          </div>
          <button
            v-if="current.key !== 'templates_exportacao'"
            type="button"
            class="inline-flex items-center gap-1 rounded-md bg-black px-3 py-2 text-xs font-medium text-white hover:bg-gray-800"
            @click="openCreate"
          >
            <Plus class="h-3.5 w-3.5" />
            Novo Cadastro
          </button>
        </div>
      </template>

      <template #cell-valor_percentual="{ row }">
        {{ row.valor_percentual ?? '-' }}
      </template>

      <template #cell-tipo="{ row }">
        <span
          class="inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold"
          :class="row.tipo === 'SQL' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'"
        >
          {{ row.tipo }}
        </span>
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
      :title="editing ? `Editar ${current.singular}` : `Novo ${current.singular}`"
      :fields="current.fields"
      :initial-values="initialValues"
      :saving="saving"
      :error="modalError"
      submit-label="Salvar"
      @submit="save"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { Pencil, Plus, Search, Trash2 } from "lucide-vue-next";
import BaseFormModal from "@/components/ui/BaseFormModal.vue";
import BaseTable from "@/components/ui/BaseTable.vue";

const API_BASE_URL = "http://127.0.0.1:8000";

const tabs = [
  {
    key: "unidades",
    label: "Unidades de Medida",
    title: "Unidades de Medida",
    singular: "Unidade",
    endpoint: `${API_BASE_URL}/api/cadastros/unidades-medida`,
    rowKey: "id_und_medida",
    lookup: "id_und_medida",
    columns: [
      { key: "sigla", label: "Sigla" },
      { key: "descricao", label: "Descricao" },
    ],
    fields: [
      { name: "sigla", label: "Sigla", type: "text" },
      { name: "descricao", label: "Descricao", type: "text" },
    ],
    defaults: { sigla: "", descricao: "" },
  },
  {
    key: "aliquotas",
    label: "Alíquotas",
    title: "Alíquotas",
    singular: "Alíquota",
    endpoint: `${API_BASE_URL}/api/cadastros/aliquotas`,
    rowKey: "id_aliquota",
    lookup: "id_aliquota",
    columns: [
      { key: "descricao", label: "Descricao" },
      { key: "valor_percentual", label: "Valor (%)" },
    ],
    fields: [
      { name: "descricao", label: "Descricao", type: "text" },
      { name: "valor_percentual", label: "Valor Percentual", type: "number", step: "0.01" },
    ],
    defaults: { descricao: "", valor_percentual: "" },
  },
  {
    key: "grupos",
    label: "Grupos de Cliente",
    title: "Grupos de Cliente",
    singular: "Grupo",
    endpoint: `${API_BASE_URL}/api/cadastros/grupos-cliente`,
    rowKey: "id_grupo",
    lookup: "id_grupo",
    columns: [
      { key: "descricao", label: "Descricao" },
    ],
    fields: [{ name: "descricao", label: "Descricao", type: "text" }],
    defaults: { descricao: "" },
  },
  {
    key: "tipos",
    label: "Tipos de Venda",
    title: "Tipos de Venda",
    singular: "Tipo de Venda",
    endpoint: `${API_BASE_URL}/api/cadastros/tipos-venda`,
    rowKey: "id_tipo_venda",
    lookup: "id_tipo_venda",
    columns: [
      { key: "descricao", label: "Descricao" },
    ],
    fields: [{ name: "descricao", label: "Descricao", type: "text" }],
    defaults: { descricao: "" },
  },
  {
    key: "formas_pagamento",
    label: "Formas de Pagamento",
    title: "Formas de Pagamento",
    singular: "Forma de Pagamento",
    endpoint: `${API_BASE_URL}/api/cadastros/formas-pagamento`,
    rowKey: "id_forma",
    lookup: "id_forma",
    columns: [
      { key: "id_forma", label: "Codigo" },
      { key: "descricao", label: "Descricao" },
    ],
    fields: [
      { name: "id_forma", label: "Codigo", type: "number", step: "1" },
      { name: "descricao", label: "Descricao", type: "text" },
    ],
    defaults: { id_forma: "", descricao: "" },
  },
  {
    key: "templates_exportacao",
    label: "Padroes de Exportacao",
    title: "Padroes de Exportacao",
    singular: "Template",
    endpoint: `${API_BASE_URL}/api/cadastros/templates-exportacao/`,
    rowKey: "id",
    lookup: "id",
    columns: [
      { key: "nome", label: "Nome" },
      { key: "tabela", label: "Tabela Alvo" },
      { key: "tipo", label: "Tipo" },
    ],
    fields: [{ name: "nome", label: "Nome", type: "text" }],
    defaults: { nome: "" },
  },
];

const activeTab = ref("unidades");
const rows = ref([]);
const loading = ref(false);
const error = ref("");
const count = ref(0);
const next = ref("");
const previous = ref("");
const search = ref("");

const showModal = ref(false);
const saving = ref(false);
const modalError = ref("");
const editing = ref(null);

const current = computed(() => tabs.find((tab) => tab.key === activeTab.value) || tabs[0]);

const initialValues = computed(() => {
  if (!editing.value) return { ...current.value.defaults };
  return {
    ...current.value.defaults,
    ...editing.value,
  };
});

function withSearch(raw) {
  const url = new URL(raw);
  if (search.value.trim()) {
    url.searchParams.set("search", search.value.trim());
  }
  return url.toString();
}

async function load(url = current.value.endpoint) {
  loading.value = true;
  error.value = "";
  try {
    const response = await fetch(withSearch(url));
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    if (Array.isArray(data)) {
      rows.value = data;
      count.value = data.length;
      next.value = "";
      previous.value = "";
    } else {
      rows.value = data.results || [];
      count.value = data.count || 0;
      next.value = data.next || "";
      previous.value = data.previous || "";
    }
  } catch (err) {
    console.error(err);
    error.value = "Falha ao carregar dados de parâmetros.";
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
  await load(current.value.endpoint);
}

async function selectTab(tabKey) {
  activeTab.value = tabKey;
  search.value = "";
  editing.value = null;
  await reload();
}

function openCreate() {
  if (current.value.key === "templates_exportacao") {
    return;
  }
  editing.value = null;
  modalError.value = "";
  showModal.value = true;
}

function openEdit(row) {
  editing.value = row;
  modalError.value = "";
  showModal.value = true;
}

function normalizePayload(values) {
  if (current.value.key === "templates_exportacao") {
    return {
      nome: String(values.nome || "").trim(),
    };
  }

  if (current.value.key === "aliquotas") {
    return {
      descricao: String(values.descricao || "").trim(),
      valor_percentual: values.valor_percentual === "" ? null : Number(values.valor_percentual),
    };
  }

  if (current.value.key === "unidades") {
    return {
      sigla: String(values.sigla || "").trim(),
      descricao: String(values.descricao || "").trim(),
    };
  }

  if (current.value.key === "formas_pagamento") {
    const payload = {
      descricao: String(values.descricao || "").trim(),
    };
    if (!editing.value) {
      payload.id_forma = values.id_forma === "" ? null : Number(values.id_forma);
    }
    return payload;
  }

  return {
    descricao: String(values.descricao || "").trim(),
  };
}

async function save(values) {
  saving.value = true;
  modalError.value = "";
  const payload = normalizePayload(values);

  try {
    const id = editing.value?.[current.value.lookup];
    const isTemplateTab = current.value.key === "templates_exportacao";
    const url = isTemplateTab
      ? id
        ? `${current.value.endpoint}${id}/`
        : current.value.endpoint
      : id
        ? `${current.value.endpoint}/${id}`
        : current.value.endpoint;
    const method = isTemplateTab ? "PATCH" : id ? "PATCH" : "POST";

    if (isTemplateTab && !id) {
      throw new Error("Criacao de template acontece no modal de exportacao.");
    }

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
    modalError.value = "Falha ao salvar parâmetro.";
  } finally {
    saving.value = false;
  }
}

async function remove(row) {
  const id = row[current.value.lookup];
  if (!confirm(`Excluir ${current.value.singular.toLowerCase()} ${id}?`)) return;

  try {
    const deleteUrl = current.value.key === "templates_exportacao" ? `${current.value.endpoint}${id}/` : `${current.value.endpoint}/${id}`;
    const response = await fetch(deleteUrl, { method: "DELETE" });
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    await reload();
  } catch (err) {
    console.error(err);
    error.value = "Falha ao excluir parâmetro.";
  }
}

onMounted(() => {
  load();
});
</script>
