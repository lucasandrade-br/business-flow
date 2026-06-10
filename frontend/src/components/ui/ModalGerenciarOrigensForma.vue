<template>
  <BaseModal
    :model-value="modelValue"
    title="Cadastro de Formas de Origem"
    description="Cadastre as formas de origem por tipo de documento para preparar o mapeamento antes das importacoes."
    @update:model-value="(value) => emit('update:modelValue', value)"
  >
    <div class="space-y-4">
      <label class="space-y-1 text-xs">
        <span class="font-medium text-gray-600">Buscar</span>
        <input
          v-model="search"
          type="text"
          class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm"
          placeholder="Buscar por tipo, codigo ou descricao..."
        />
      </label>

      <div class="rounded-md border border-gray-200 p-3">
        <p class="mb-2 text-xs font-semibold text-gray-700">{{ editingId ? 'Editar Origem' : 'Nova Origem' }}</p>
        <div class="grid gap-2 sm:grid-cols-4">
          <select v-model="form.tipo_documento" class="rounded-md border border-gray-200 px-2 py-1.5 text-xs">
            <option value="NFCE">NFCE</option>
            <option value="DAV">DAV</option>
            <option value="NFE">NFE</option>
          </select>
          <input
            v-model="form.id_forma_origem"
            type="number"
            min="1"
            step="1"
            class="rounded-md border border-gray-200 px-2 py-1.5 text-xs"
            placeholder="Codigo origem"
          />
          <input
            v-model="form.descricao_origem"
            type="text"
            class="rounded-md border border-gray-200 px-2 py-1.5 text-xs"
            placeholder="Descricao origem"
          />
          <label class="flex items-center gap-2 rounded-md border border-gray-200 px-2 py-1.5 text-xs text-gray-700">
            <input v-model="form.ativo" type="checkbox" class="h-4 w-4 rounded border-gray-300" />
            Ativo
          </label>
        </div>
        <div class="mt-2 flex items-center gap-2">
          <button
            type="button"
            class="rounded-md bg-black px-3 py-1.5 text-xs font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="saving"
            @click="save"
          >
            {{ saving ? 'Salvando...' : editingId ? 'Atualizar' : 'Cadastrar' }}
          </button>
          <button
            v-if="editingId"
            type="button"
            class="rounded-md border border-gray-200 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
            :disabled="saving"
            @click="resetForm"
          >
            Cancelar Edicao
          </button>
        </div>
      </div>

      <div class="max-h-72 overflow-auto rounded-md border border-gray-200">
        <table class="min-w-full text-xs">
          <thead>
            <tr class="border-b border-gray-100 bg-gray-50 text-left text-gray-500">
              <th class="px-2 py-1">Tipo</th>
              <th class="px-2 py-1">Codigo</th>
              <th class="px-2 py-1">Descricao</th>
              <th class="px-2 py-1">Ativo</th>
              <th class="px-2 py-1">Acoes</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading" class="border-b border-gray-100">
              <td colspan="5" class="px-2 py-2 text-gray-500">Carregando origens...</td>
            </tr>
            <tr v-else-if="!rows.length" class="border-b border-gray-100">
              <td colspan="5" class="px-2 py-2 text-gray-500">Nenhuma origem cadastrada.</td>
            </tr>
            <tr v-for="row in rows" :key="row.id_origem" class="border-b border-gray-100">
              <td class="px-2 py-1">{{ row.tipo_documento }}</td>
              <td class="px-2 py-1">{{ row.id_forma_origem }}</td>
              <td class="px-2 py-1">{{ row.descricao_origem }}</td>
              <td class="px-2 py-1">{{ row.ativo ? 'Sim' : 'Nao' }}</td>
              <td class="px-2 py-1">
                <div class="inline-flex items-center gap-2">
                  <button
                    type="button"
                    class="rounded-md border border-gray-200 px-2 py-1 text-[11px] text-gray-700 hover:bg-gray-50"
                    @click="startEdit(row)"
                  >
                    Editar
                  </button>
                  <button
                    type="button"
                    class="rounded-md border border-red-200 px-2 py-1 text-[11px] text-red-600 hover:bg-red-50"
                    @click="remove(row)"
                  >
                    Excluir
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p v-if="localError" class="text-xs text-red-600">{{ localError }}</p>
    </div>

    <template #footer>
      <button
        type="button"
        class="rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50"
        @click="emit('update:modelValue', false)"
      >
        Fechar
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch } from "vue";
import BaseModal from "@/components/ui/BaseModal.vue";

const API_BASE_URL = "http://127.0.0.1:8000";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const loading = ref(false);
const saving = ref(false);
const localError = ref("");
const rows = ref([]);
const search = ref("");
const editingId = ref(null);
const form = ref({
  tipo_documento: "NFCE",
  id_forma_origem: "",
  descricao_origem: "",
  ativo: true,
});

let debounceTimer;

function resetForm() {
  editingId.value = null;
  form.value = {
    tipo_documento: "NFCE",
    id_forma_origem: "",
    descricao_origem: "",
    ativo: true,
  };
}

function toPayload() {
  const idRaw = Number(form.value.id_forma_origem);
  return {
    tipo_documento: String(form.value.tipo_documento || "").trim().toUpperCase(),
    id_forma_origem: Number.isInteger(idRaw) ? idRaw : null,
    descricao_origem: String(form.value.descricao_origem || "").trim(),
    ativo: Boolean(form.value.ativo),
  };
}

async function load() {
  loading.value = true;
  localError.value = "";
  try {
    const url = new URL(`${API_BASE_URL}/api/cadastros/formas-pagamento/origens`);
    if (search.value.trim()) {
      url.searchParams.set("search", search.value.trim());
    }

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`Erro ${response.status}`);

    const data = await response.json();
    rows.value = Array.isArray(data) ? data : data.results || [];
  } catch (err) {
    console.error(err);
    rows.value = [];
    localError.value = "Falha ao carregar origens.";
  } finally {
    loading.value = false;
  }
}

function startEdit(row) {
  editingId.value = Number(row.id_origem);
  form.value = {
    tipo_documento: String(row.tipo_documento || "").toUpperCase() || "NFCE",
    id_forma_origem: Number(row.id_forma_origem),
    descricao_origem: String(row.descricao_origem || ""),
    ativo: Boolean(row.ativo),
  };
}

async function save() {
  const payload = toPayload();
  if (!payload.tipo_documento || !payload.id_forma_origem || !payload.descricao_origem) {
    localError.value = "Tipo, codigo e descricao sao obrigatorios.";
    return;
  }

  saving.value = true;
  localError.value = "";
  try {
    const url = editingId.value
      ? `${API_BASE_URL}/api/cadastros/formas-pagamento/origens/${editingId.value}`
      : `${API_BASE_URL}/api/cadastros/formas-pagamento/origens`;
    const method = editingId.value ? "PATCH" : "POST";

    const response = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(await response.text());
    }

    resetForm();
    await load();
  } catch (err) {
    console.error(err);
    localError.value = "Falha ao salvar origem. Verifique se tipo+codigo ja existe.";
  } finally {
    saving.value = false;
  }
}

async function remove(row) {
  if (!confirm(`Excluir origem ${row.tipo_documento} #${row.id_forma_origem}?`)) return;

  localError.value = "";
  try {
    const response = await fetch(`${API_BASE_URL}/api/cadastros/formas-pagamento/origens/${row.id_origem}`, { method: "DELETE" });
    if (!response.ok) {
      throw new Error(`Erro ${response.status}`);
    }

    if (editingId.value === Number(row.id_origem)) {
      resetForm();
    }
    await load();
  } catch (err) {
    console.error(err);
    localError.value = "Falha ao excluir origem.";
  }
}

watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      resetForm();
      search.value = "";
      load();
    }
  },
);

watch(search, () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    load();
  }, 300);
});
</script>
