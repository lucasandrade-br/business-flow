<template>
  <section class="rounded-md border border-gray-200 p-3">
    <h4 class="text-xs font-semibold uppercase tracking-wide text-gray-500">{{ title }}</h4>
    <p v-if="loading" class="mt-2 text-xs text-gray-500">Carregando categorias...</p>
    <p v-else-if="error" class="mt-2 text-xs text-red-600">{{ error }}</p>
    <p v-else-if="!roots.length" class="mt-2 text-xs text-gray-500">Nenhuma categoria raiz cadastrada.</p>
    <div v-else class="mt-3 grid gap-3 lg:grid-cols-2">
      <div v-for="root in roots" :key="root.id_conta" class="space-y-1">
        <label class="text-xs font-medium text-gray-600">{{ root.nome_conta }}</label>
        <RemoteSearchSelect
          :model-value="selectedByRoot[root.id_conta] ?? ''"
          :endpoint="opcoesEndpoint"
          value-field="id_conta"
          label-field="label"
          resolve-param="ids"
          :extra-params="{ raiz_id: root.id_conta, somente_folhas: 1 }"
          :disabled="disabled"
          all-label="Selecione uma subcategoria"
          search-placeholder="Buscar por codigo ou nome"
          :limit="50"
          button-class="inline-flex w-full items-center justify-between gap-2 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
          dropdown-class="absolute z-30 mt-1 w-full min-w-[18rem] rounded-md border border-gray-200 bg-white p-2 shadow-lg"
          @update:model-value="(value) => onSelect(root.id_conta, value)"
        />
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from "vue";
import RemoteSearchSelect from "@/components/ui/RemoteSearchSelect.vue";
import { getApiBaseUrl } from "@/services/firebirdSync";

const API_BASE_URL = getApiBaseUrl();
const opcoesEndpoint = `${API_BASE_URL}/api/cadastros/plano-contas/opcoes`;

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  title: { type: String, default: "Categorias por raiz" },
  disabled: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const roots = ref([]);
const loading = ref(false);
const error = ref("");
const selectedByRoot = reactive({});

async function loadRoots() {
  if (roots.value.length) return;
  loading.value = true;
  error.value = "";
  try {
    const response = await fetch(`${API_BASE_URL}/api/cadastros/plano-contas/raizes`);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    roots.value = Array.isArray(data) ? data : data.results || [];
    hydrate();
  } catch (err) {
    console.error(err);
    roots.value = [];
    error.value = "Nao foi possivel carregar as categorias raiz.";
  } finally {
    loading.value = false;
  }
}

// Sem a arvore completa em memoria, cada id selecionado e atribuido a raiz pelo prefixo do codigo hierarquico.
async function hydrate() {
  for (const root of roots.value) {
    selectedByRoot[root.id_conta] = "";
  }

  const ids = (props.modelValue || [])
    .map((id) => Number(id))
    .filter((id) => Number.isFinite(id) && id > 0);
  if (!ids.length || !roots.value.length) return;

  try {
    const response = await fetch(`${opcoesEndpoint}?ids=${ids.join(",")}`);
    if (!response.ok) throw new Error(`Erro ${response.status}`);
    const data = await response.json();
    const items = Array.isArray(data) ? data : data.results || [];

    for (const item of items) {
      const root = roots.value.find((candidate) =>
        String(item.codigo_hierarquico || "").startsWith(String(candidate.codigo_hierarquico || "")),
      );
      if (root) {
        selectedByRoot[root.id_conta] = item.id_conta;
      }
    }
  } catch (err) {
    console.error(err);
  }
}

function currentIds() {
  return Object.values(selectedByRoot)
    .map((id) => Number(id))
    .filter((id) => Number.isFinite(id) && id > 0);
}

function onSelect(rootId, value) {
  selectedByRoot[rootId] = value === "" || value === null || value === undefined ? "" : Number(value);
  emit("update:modelValue", currentIds());
}

watch(
  () => props.modelValue,
  (value) => {
    const incoming = (value || [])
      .map((id) => Number(id))
      .filter((id) => Number.isFinite(id) && id > 0)
      .sort((a, b) => a - b);
    const atual = currentIds().sort((a, b) => a - b);
    if (incoming.join(",") === atual.join(",")) return;
    hydrate();
  },
);

onMounted(loadRoots);
</script>
