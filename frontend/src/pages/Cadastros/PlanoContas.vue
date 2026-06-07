<template>
  <section>
    <BaseTable
      title="Plano de Contas"
      subtitle="CRUD com busca e codificacao hierarquica automatica"
      :columns="columns"
      :rows="rows"
      row-key="id_conta"
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
            v-model="selectedRaiz"
            class="appearance-none rounded-md border border-gray-200 bg-white px-3 py-2 text-xs"
            @change="reload"
          >
            <option value="">Todas as familias</option>
            <option v-for="root in rootsOptions" :key="root.value" :value="String(root.value)">
              {{ root.label }}
            </option>
          </select>
          <div class="flex items-center gap-2 rounded-md border border-gray-200 bg-white px-2 py-1.5">
            <Search class="h-4 w-4 text-gray-400" />
            <input
              v-model="search"
              type="text"
              placeholder="Buscar conta"
              class="w-44 border-0 bg-transparent p-0 text-xs outline-none"
              @keyup.enter="reload"
            />
          </div>
          <button
            type="button"
            class="inline-flex items-center gap-1 rounded-md bg-black px-3 py-2 text-xs font-medium text-white hover:bg-gray-800"
            @click="openCreate"
          >
            <Plus class="h-3.5 w-3.5" />
            Novo Cadastro
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50"
            @click="openVinculos"
          >
            <Link class="h-3.5 w-3.5" />
            Gerenciar Vinculos
          </button>
        </div>
      </template>

      <template #cell-linha_sucessoria="{ row }">
        {{ row.linha_sucessoria || '-' }}
      </template>

      <template #cell-qtd_produtos="{ row }">
        <span class="inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-700">
          {{ row.qtd_produtos ?? 0 }}
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
      :title="editing ? 'Editar Conta' : 'Nova Conta'"
      :fields="formFields"
      :initial-values="initialValues"
      :saving="saving"
      :error="modalError"
      submit-label="Salvar"
      @submit="save"
    />

    <ModalLotePlanoContas
      v-model="showLoteModal"
      :parent-options="parentOptions"
      :loading="savingLote"
      :error="loteError"
      @submit="saveLote"
    />

    <ModalGerenciarVinculos
      v-model="showVinculosModal"
      :categorias-options="categoriaOptions"
      :loading="savingVinculos"
      :error="vinculosError"
      @submit="aplicarVinculos"
    />

    <div v-if="toastMessage" class="fixed bottom-5 right-5 z-50 rounded-md border border-gray-200 bg-white px-4 py-3 text-xs text-[#373435]">
      {{ toastMessage }}
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { Link, Pencil, Plus, Search, Trash2 } from "lucide-vue-next";
import BaseFormModal from "@/components/ui/BaseFormModal.vue";
import ModalGerenciarVinculos from "@/components/ui/ModalGerenciarVinculos.vue";
import ModalLotePlanoContas from "@/components/ui/ModalLotePlanoContas.vue";
import BaseTable from "@/components/ui/BaseTable.vue";

const API_BASE_URL = "http://127.0.0.1:8000";
const endpoint = `${API_BASE_URL}/api/cadastros/plano-contas`;

const columns = [
  { key: "codigo_hierarquico", label: "Codigo" },
  { key: "nome_conta", label: "Nome" },
  { key: "linha_sucessoria", label: "Hierarquia" },
  { key: "qtd_produtos", label: "Qtd. Produtos" },
];

const rows = ref([]);
const loading = ref(false);
const error = ref("");
const count = ref(0);
const next = ref("");
const previous = ref("");
const search = ref("");
const selectedRaiz = ref("");
const rootsOptions = ref([]);
const categoriaOptions = ref([]);

const showModal = ref(false);
const saving = ref(false);
const modalError = ref("");
const showLoteModal = ref(false);
const savingLote = ref(false);
const loteError = ref("");
const showVinculosModal = ref(false);
const savingVinculos = ref(false);
const vinculosError = ref("");
const toastMessage = ref("");
let toastTimer;
const editing = ref(null);
const parentOptions = ref([]);

const formFields = computed(() => [
  { name: "nome_conta", label: "Nome da Conta", type: "text" },
  {
    name: "conta_pai",
    label: "Conta Pai",
    type: "select",
    emptyValue: "",
    placeholder: "Sem pai (raiz)",
    options: parentOptions.value,
  },
]);

const initialValues = computed(() => {
  if (!editing.value) {
    return { nome_conta: "", conta_pai: "" };
  }
  return {
    nome_conta: editing.value.nome_conta || "",
    conta_pai: editing.value.conta_pai || "",
  };
});

function withSearch(raw = endpoint) {
  const url = new URL(raw);
  if (search.value.trim()) {
    url.searchParams.set("search", search.value.trim());
  }
  if (selectedRaiz.value !== "") {
    url.searchParams.set("raiz_id", selectedRaiz.value);
  }
  return url.toString();
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
    error.value = "Falha ao carregar plano de contas.";
  } finally {
    loading.value = false;
  }
}

async function loadParentOptions() {
  try {
    const response = await fetch(endpoint);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    parentOptions.value = (data.results || []).map((item) => ({
      value: item.id_conta,
      label: `${item.codigo_hierarquico || '-'} ${item.nome_conta}`,
    }));
  } catch (err) {
    console.error(err);
    parentOptions.value = [];
  }
}

async function loadRootsOptions() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/cadastros/plano-contas/arvore`);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();

    const tree = Array.isArray(data) ? data : [];
    rootsOptions.value = tree.map((item) => ({
      value: item.id_conta,
      label: `${item.codigo_hierarquico} ${item.nome_conta}`,
    }));

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
    walk(tree, 0);
    categoriaOptions.value = flattened;
  } catch (err) {
    console.error(err);
    rootsOptions.value = [];
    categoriaOptions.value = [];
  }
}

function notify(message) {
  toastMessage.value = message;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toastMessage.value = "";
  }, 2800);
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
  loteError.value = "";
  await loadParentOptions();
  showLoteModal.value = true;
}

async function openEdit(row) {
  editing.value = row;
  modalError.value = "";
  await loadParentOptions();
  showModal.value = true;
}

async function save(values) {
  saving.value = true;
  modalError.value = "";

  const payload = {
    nome_conta: String(values.nome_conta || "").trim(),
    conta_pai: values.conta_pai === "" ? null : Number(values.conta_pai),
  };

  try {
    const url = editing.value ? `${endpoint}/${editing.value.id_conta}` : endpoint;
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
    modalError.value = "Falha ao salvar conta.";
  } finally {
    saving.value = false;
  }
}

async function remove(row) {
  if (!confirm(`Excluir conta ${row.nome_conta}?`)) return;
  try {
    const response = await fetch(`${endpoint}/${row.id_conta}`, { method: "DELETE" });
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    await reload();
  } catch (err) {
    console.error(err);
    error.value = "Falha ao excluir conta.";
  }
}

async function saveLote(payload) {
  savingLote.value = true;
  loteError.value = "";

  try {
    const response = await fetch(`${endpoint}/lote/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }

    showLoteModal.value = false;
    await Promise.all([reload(), loadParentOptions(), loadRootsOptions()]);
  } catch (err) {
    console.error(err);
    loteError.value = "Falha ao salvar lote de contas.";
  } finally {
    savingLote.value = false;
  }
}

async function openVinculos() {
  vinculosError.value = "";
  if (!categoriaOptions.value.length) {
    await loadRootsOptions();
  }
  showVinculosModal.value = true;
}

async function aplicarVinculos({ categoria_id, adicionar_ids, remover_ids }) {
  savingVinculos.value = true;
  vinculosError.value = "";

  try {
    const response = await fetch(`${endpoint}/${categoria_id}/vincular-produtos/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ adicionar_ids, remover_ids }),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }

    showVinculosModal.value = false;
    notify("Vinculos aplicados com sucesso.");
  } catch (err) {
    console.error(err);
    vinculosError.value = "Falha ao aplicar vinculos.";
  } finally {
    savingVinculos.value = false;
  }
}

onMounted(() => {
  Promise.all([load(), loadRootsOptions()]);
});
</script>
