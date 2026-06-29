<template>
  <BaseModal
    :model-value="modelValue"
    title="Exportar dados"
    description="Selecione colunas, use SQL avancado ou aplique um padrao salvo."
    @update:model-value="(value) => emit('update:modelValue', value)"
  >
    <div class="grid gap-4 lg:grid-cols-[220px_1fr]">
      <aside class="space-y-2 rounded-md border border-gray-200 p-3">
        <h4 class="text-xs font-semibold uppercase tracking-wide text-gray-500">Meus Padroes</h4>
        <p v-if="templatesLoading" class="text-xs text-gray-500">Carregando...</p>
        <p v-else-if="templates.length === 0" class="text-xs text-gray-500">Nenhum padrao salvo.</p>
        <div v-else class="space-y-2">
          <button
            v-for="template in templates"
            :key="template.id"
            type="button"
            class="w-full rounded-md border border-gray-200 px-2 py-2 text-left text-xs text-gray-700 hover:bg-gray-50"
            @click="applyTemplate(template)"
          >
            <div class="flex items-center justify-between gap-2">
              <span class="truncate font-medium">{{ template.nome }}</span>
              <span
                class="rounded-full px-2 py-0.5 text-[10px] font-semibold"
                :class="template.tipo === 'SQL' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'"
              >
                {{ template.tipo === 'SQL' ? 'SQL' : 'Colunas' }}
              </span>
            </div>
          </button>
        </div>
      </aside>

      <section class="space-y-4 rounded-md border border-gray-200 p-3">
        <div class="inline-flex rounded-md border border-gray-200 p-1 text-xs">
          <button
            type="button"
            class="rounded px-3 py-1.5"
            :class="activeMode === 'BASICO' ? 'bg-black text-white' : 'text-gray-700 hover:bg-gray-50'"
            @click="activeMode = 'BASICO'"
          >
            Basico
          </button>
          <button
            type="button"
            class="rounded px-3 py-1.5"
            :class="activeMode === 'SQL' ? 'bg-black text-white' : 'text-gray-700 hover:bg-gray-50'"
            @click="activeMode = 'SQL'"
          >
            Avancado
          </button>
        </div>

        <section v-if="activeMode === 'BASICO'">
          <h4 class="text-xs font-semibold uppercase tracking-wide text-gray-500">Colunas</h4>
          <div class="mt-2 grid gap-2 sm:grid-cols-2">
            <label
              v-for="column in availableColumns"
              :key="column.key"
              class="inline-flex items-center gap-2 rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700"
            >
              <input
                v-model="selectedColumns"
                type="checkbox"
                :value="column.key"
                class="h-4 w-4 rounded border-gray-300"
              />
              <span>{{ column.label }}</span>
            </label>
          </div>
        </section>

        <section v-else>
          <h4 class="text-xs font-semibold uppercase tracking-wide text-gray-500">Query SQL</h4>
          <textarea
            v-model="sqlQuery"
            rows="10"
            class="mt-2 w-full rounded-md border border-gray-200 px-3 py-2 font-mono text-xs"
            placeholder="SELECT id_produto, produto, custo FROM produtos"
          />
        </section>

        <section>
          <h4 class="text-xs font-semibold uppercase tracking-wide text-gray-500">Formato</h4>
        <div class="mt-2 grid gap-2 sm:grid-cols-3">
          <label
            v-for="option in formatOptions"
            :key="option.value"
            class="inline-flex cursor-pointer items-center justify-center gap-2 rounded-md border px-3 py-2 text-xs font-medium transition-colors"
            :class="selectedFormat === option.value ? 'border-black bg-black text-white' : 'border-gray-200 text-gray-700 hover:bg-gray-50'"
          >
            <input v-model="selectedFormat" type="radio" :value="option.value" class="sr-only" />
            {{ option.label }}
          </label>
        </div>
        </section>

        <section>
          <label class="space-y-1 text-xs">
            <span class="font-medium text-gray-600">Salvar formato como...</span>
            <input
              v-model="saveTemplateName"
              type="text"
              class="w-full rounded-md border border-gray-200 px-3 py-2 text-xs"
              placeholder="Ex: Exportacao de auditoria"
            />
          </label>
        </section>

        <p v-if="localError" class="text-xs text-red-600">{{ localError }}</p>
        <p v-if="error" class="text-xs text-red-600">{{ error }}</p>
      </section>
    </div>

    <template #footer>
      <button
        type="button"
        class="rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50"
        :disabled="loading"
        @click="emit('update:modelValue', false)"
      >
        Cancelar
      </button>
      <button
        type="button"
        class="rounded-md bg-black px-3 py-2 text-xs font-medium text-white hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="loading"
        @click="confirm"
      >
        {{ loading ? 'Exportando...' : 'Exportar' }}
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
  tabela: { type: String, required: true },
  availableColumns: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue", "confirm"]);

const formatOptions = [
  { value: "csv", label: "CSV" },
  { value: "xlsx", label: "Excel" },
  { value: "pdf", label: "PDF" },
];

const selectedColumns = ref([]);
const selectedFormat = ref("csv");
const activeMode = ref("BASICO");
const sqlQuery = ref("");
const saveTemplateName = ref("");
const templates = ref([]);
const templatesLoading = ref(false);
const localError = ref("");

async function loadTemplates() {
  templatesLoading.value = true;
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/cadastros/templates-exportacao/?tabela=${encodeURIComponent(props.tabela)}`,
    );
    if (!response.ok) {
      throw new Error(`Erro ${response.status}`);
    }
    const data = await response.json();
    templates.value = Array.isArray(data.results) ? data.results : Array.isArray(data) ? data : [];
  } catch (err) {
    console.error(err);
    templates.value = [];
  } finally {
    templatesLoading.value = false;
  }
}

function applyTemplate(template) {
  activeMode.value = template.tipo;
  if (template.tipo === "SQL") {
    sqlQuery.value = template.query_sql || "";
    return;
  }
  selectedColumns.value = Array.isArray(template.colunas_selecionadas)
    ? [...template.colunas_selecionadas]
    : props.availableColumns.map((item) => item.key);
}

watch(
  () => props.modelValue,
  async (value) => {
    if (!value) {
      localError.value = "";
      return;
    }
    await loadTemplates();
    selectedColumns.value = props.availableColumns.map((item) => item.key);
    selectedFormat.value = "csv";
    activeMode.value = "BASICO";
    sqlQuery.value = "";
    saveTemplateName.value = "";
    localError.value = "";
  },
);

function confirm() {
  if (activeMode.value === "BASICO" && !selectedColumns.value.length) {
    localError.value = "Selecione ao menos uma coluna para exportacao.";
    return;
  }

  if (activeMode.value === "SQL" && !sqlQuery.value.trim()) {
    localError.value = "Informe uma query SQL para exportacao avancada.";
    return;
  }

  localError.value = "";
  emit("confirm", {
    tipo: activeMode.value,
    colunas: [...selectedColumns.value],
    query_sql: sqlQuery.value,
    formato: selectedFormat.value,
    salvar_nome: String(saveTemplateName.value || "").trim(),
  });
}
</script>
