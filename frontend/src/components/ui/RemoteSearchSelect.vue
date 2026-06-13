<template>
  <div ref="rootRef" class="relative">
    <button
      type="button"
      class="inline-flex min-w-[180px] items-center justify-between gap-2 rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
      @click="toggleOpen"
    >
      <span class="truncate">{{ selectedLabel }}</span>
      <ChevronDown class="h-3.5 w-3.5 text-gray-400" />
    </button>

    <div v-if="isOpen" class="absolute z-30 mt-1 w-72 rounded-md border border-gray-200 bg-white p-2 shadow-lg">
      <div class="relative">
        <Search class="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
        <input
          v-model="searchTerm"
          type="text"
          class="w-full rounded-md border border-gray-200 py-1.5 pl-7 pr-6 text-xs outline-none focus:border-gray-300"
          :placeholder="searchPlaceholder"
          @keydown.esc="isOpen = false"
        />
        <button
          v-if="searchTerm"
          type="button"
          class="absolute right-1.5 top-1/2 -translate-y-1/2 rounded p-0.5 text-gray-400 hover:bg-gray-100"
          @click="clearSearch"
        >
          <X class="h-3.5 w-3.5" />
        </button>
      </div>

      <p v-if="searchTerm && searchTerm.trim().length < minChars" class="mt-2 text-[11px] text-gray-500">
        Digite ao menos {{ minChars }} caracteres para pesquisar.
      </p>
      <p v-else-if="loading" class="mt-2 text-[11px] text-gray-500">Pesquisando...</p>

      <div class="mt-2 max-h-60 overflow-auto">
        <button
          type="button"
          class="w-full rounded px-2 py-1.5 text-left text-xs text-gray-700 hover:bg-gray-50"
          @click="selectAll"
        >
          {{ allLabel }}
        </button>

        <button
          v-for="option in options"
          :key="String(option.value)"
          type="button"
          class="w-full rounded px-2 py-1.5 text-left text-xs text-gray-700 hover:bg-gray-50"
          @click="selectOption(option)"
        >
          {{ option.label }}
        </button>

        <p v-if="showNoResults" class="px-2 py-2 text-[11px] text-gray-500">Nenhum resultado encontrado.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ChevronDown, Search, X } from "lucide-vue-next";

const props = defineProps({
  modelValue: { type: [String, Number, null], default: "" },
  endpoint: { type: String, required: true },
  valueField: { type: String, required: true },
  labelField: { type: String, default: "" },
  formatOptionLabel: { type: Function, default: null },
  allLabel: { type: String, default: "Todos" },
  searchPlaceholder: { type: String, default: "Pesquisar..." },
  minChars: { type: Number, default: 2 },
  limit: { type: Number, default: 20 },
});

const emit = defineEmits(["update:modelValue"]);

const rootRef = ref(null);
const isOpen = ref(false);
const loading = ref(false);
const options = ref([]);
const searchTerm = ref("");
const selectedLabelRef = ref("");
const cache = ref({});
let debounceId = null;

const selectedLabel = computed(() => {
  if (props.modelValue === "" || props.modelValue === null || props.modelValue === undefined) {
    return props.allLabel;
  }
  if (selectedLabelRef.value) {
    return selectedLabelRef.value;
  }
  return `Selecionado: ${props.modelValue}`;
});

const showNoResults = computed(() => {
  if (loading.value) return false;
  const hasMinChars = !searchTerm.value || searchTerm.value.trim().length >= props.minChars;
  return hasMinChars && options.value.length === 0;
});

function normalizeLabel(item) {
  if (props.formatOptionLabel) {
    return String(props.formatOptionLabel(item));
  }
  if (props.labelField && item?.[props.labelField] !== undefined) {
    return String(item[props.labelField]);
  }
  if (item?.[props.valueField] !== undefined) {
    return String(item[props.valueField]);
  }
  return "";
}

async function fetchOptions(term = "") {
  const normalized = String(term || "").trim();
  if (normalized && normalized.length < props.minChars) {
    options.value = [];
    return;
  }

  const cacheKey = normalized.toLowerCase();
  if (cache.value[cacheKey]) {
    options.value = cache.value[cacheKey];
    syncSelectedLabelFromOptions();
    return;
  }

  loading.value = true;
  try {
    const url = new URL(props.endpoint);
    url.searchParams.set("limit", String(props.limit));
    if (normalized) {
      url.searchParams.set("search", normalized);
    }

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`Erro ${response.status}`);

    const payload = await response.json();
    const items = Array.isArray(payload?.results) ? payload.results : Array.isArray(payload) ? payload : [];
    const mapped = items.map((item) => ({
      value: item?.[props.valueField],
      label: normalizeLabel(item),
    }));

    cache.value[cacheKey] = mapped;
    options.value = mapped;
    syncSelectedLabelFromOptions();
  } catch (err) {
    console.error(err);
    options.value = [];
  } finally {
    loading.value = false;
  }
}

function syncSelectedLabelFromOptions() {
  const current = options.value.find((item) => String(item.value) === String(props.modelValue));
  if (current) {
    selectedLabelRef.value = current.label;
  }
}

function selectOption(option) {
  selectedLabelRef.value = option.label;
  emit("update:modelValue", option.value);
  isOpen.value = false;
}

function selectAll() {
  selectedLabelRef.value = "";
  emit("update:modelValue", "");
  isOpen.value = false;
}

function clearSearch() {
  searchTerm.value = "";
}

function toggleOpen() {
  isOpen.value = !isOpen.value;
  if (isOpen.value) {
    fetchOptions(searchTerm.value);
  }
}

function handleOutsideClick(event) {
  const root = rootRef.value;
  if (!root) return;
  if (!root.contains(event.target)) {
    isOpen.value = false;
  }
}

watch(searchTerm, (value) => {
  if (!isOpen.value) return;
  if (debounceId) {
    clearTimeout(debounceId);
  }
  debounceId = setTimeout(() => {
    fetchOptions(value);
  }, 300);
});

watch(
  () => props.modelValue,
  (value) => {
    if (value === "" || value === null || value === undefined) {
      selectedLabelRef.value = "";
    } else {
      syncSelectedLabelFromOptions();
    }
  },
);

onMounted(() => {
  document.addEventListener("click", handleOutsideClick);
});

onBeforeUnmount(() => {
  if (debounceId) {
    clearTimeout(debounceId);
  }
  document.removeEventListener("click", handleOutsideClick);
});
</script>
