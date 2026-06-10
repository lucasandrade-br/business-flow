<template>
  <BaseModal
    :model-value="modelValue"
    title="Mapeamento por Tipo de Documento"
    description="Associe as formas de origem (NFCE, DAV, NFE) a uma forma canônica do sistema."
    @update:model-value="(value) => emit('update:modelValue', value)"
  >
    <div class="space-y-4">
      <label class="space-y-1 text-xs">
        <span class="font-medium text-gray-600">Forma Canônica</span>
        <select v-model="selectedFormaId" class="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm">
          <option value="">Selecione uma forma</option>
          <option v-for="option in formasOptions" :key="option.value" :value="String(option.value)">
            {{ option.label }}
          </option>
        </select>
      </label>

      <label class="space-y-1 text-xs">
        <span class="font-medium text-gray-600">Buscar Formas de Origem</span>
        <div class="flex items-center gap-2">
          <input
            v-model="search"
            type="text"
            class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm"
            placeholder="Buscar por tipo, codigo ou descricao..."
          />
          <button
            type="button"
            class="inline-flex shrink-0 items-center gap-1 rounded-md border px-3 py-2 text-xs font-medium transition-colors"
            :class="mostrarApenasVinculados ? 'border-black bg-black text-white' : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'"
            @click="mostrarApenasVinculados = !mostrarApenasVinculados"
          >
            Mostrar apenas vinculados
          </button>
        </div>
      </label>

      <section class="space-y-2">
        <div class="flex items-center justify-between text-xs text-gray-500">
          <span>Resultado da busca</span>
          <span>{{ totalAlteracoes }} alteracao(oes)</span>
        </div>

        <div class="rounded-md border border-gray-200 px-2 py-1.5">
          <label class="flex cursor-pointer items-center gap-2 text-xs text-gray-700">
            <input
              ref="selectAllRef"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300"
              :checked="allRenderedChecked"
              @change="toggleSelecionarTodos($event.target.checked)"
            />
            Selecionar Todos
          </label>
        </div>

        <div class="max-h-72 space-y-1 overflow-y-auto rounded-md border border-gray-200 p-2">
          <p v-if="searching" class="px-2 py-2 text-xs text-gray-500">Buscando formas de origem...</p>
          <p v-else-if="!opcoes.length" class="px-2 py-2 text-xs text-gray-500">Nenhuma opcao encontrada.</p>

          <label
            v-for="opcao in opcoes"
            :key="opcao.chave"
            class="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-gray-50"
          >
            <input
              :checked="isOpcaoSelecionada(opcao)"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300"
              @change="toggleOpcao(opcao, $event.target.checked)"
            />
            <span class="inline-flex rounded-full bg-gray-100 px-2 py-0.5 font-semibold text-gray-700">{{ opcao.tipo_documento }}</span>
            <span class="font-medium text-gray-700">#{{ opcao.id_forma_origem }}</span>
            <span class="truncate text-gray-500">{{ opcao.descricao_origem || '-' }}</span>
          </label>
        </div>
      </section>

      <p v-if="localError" class="text-xs text-red-600">{{ localError }}</p>
      <p v-if="error" class="text-xs text-red-600">{{ error }}</p>
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
        class="rounded-md bg-black px-3 py-2 text-xs font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="loading"
        @click="submit"
      >
        {{ loading ? 'Aplicando...' : 'Aplicar Mapeamentos' }}
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import BaseModal from "@/components/ui/BaseModal.vue";

const API_BASE_URL = "http://127.0.0.1:8000";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  formasOptions: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue", "submit"]);

const selectedFormaId = ref("");
const search = ref("");
const mostrarApenasVinculados = ref(false);
const opcoes = ref([]);
const searching = ref(false);
const paraAdicionar = ref([]);
const paraRemover = ref([]);
const localError = ref("");
const selectAllRef = ref(null);

let debounceTimer;

function buildKey(item) {
  return `${item.tipo_documento}:${Number(item.id_forma_origem)}`;
}

function resetState() {
  selectedFormaId.value = "";
  search.value = "";
  mostrarApenasVinculados.value = false;
  opcoes.value = [];
  paraAdicionar.value = [];
  paraRemover.value = [];
  localError.value = "";
}

function removeFromArray(listRef, value) {
  listRef.value = listRef.value.filter((item) => item !== value);
}

function pushUnique(listRef, value) {
  if (!listRef.value.includes(value)) {
    listRef.value.push(value);
  }
}

function isOriginalmenteVinculado(opcao) {
  if (!selectedFormaId.value) {
    return false;
  }
  return Number(opcao.forma_pagamento_id) === Number(selectedFormaId.value);
}

function isOpcaoSelecionada(opcao) {
  const chave = opcao.chave;
  if (paraAdicionar.value.includes(chave)) {
    return true;
  }
  if (paraRemover.value.includes(chave)) {
    return false;
  }
  return isOriginalmenteVinculado(opcao);
}

function toggleOpcao(opcao, checked) {
  const chave = opcao.chave;
  const originalmenteVinculado = isOriginalmenteVinculado(opcao);

  if (checked) {
    if (originalmenteVinculado) {
      removeFromArray(paraRemover, chave);
    } else {
      pushUnique(paraAdicionar, chave);
      removeFromArray(paraRemover, chave);
    }
    return;
  }

  if (originalmenteVinculado) {
    pushUnique(paraRemover, chave);
    removeFromArray(paraAdicionar, chave);
  } else {
    removeFromArray(paraAdicionar, chave);
    removeFromArray(paraRemover, chave);
  }
}

const totalAlteracoes = computed(() => paraAdicionar.value.length + paraRemover.value.length);

const allRenderedChecked = computed(() => {
  if (!opcoes.value.length) return false;
  return opcoes.value.every((opcao) => isOpcaoSelecionada(opcao));
});

const someRenderedChecked = computed(() => {
  return opcoes.value.some((opcao) => isOpcaoSelecionada(opcao));
});

watch([allRenderedChecked, someRenderedChecked], () => {
  if (!selectAllRef.value) return;
  selectAllRef.value.indeterminate = !allRenderedChecked.value && someRenderedChecked.value;
});

function toggleSelecionarTodos(checked) {
  for (const opcao of opcoes.value) {
    toggleOpcao(opcao, checked);
  }
}

async function fetchOpcoes(term = "") {
  searching.value = true;
  try {
    const url = new URL(`${API_BASE_URL}/api/cadastros/formas-pagamento/mapeamentos/opcoes`);
    if (selectedFormaId.value) {
      url.searchParams.set("forma_id", selectedFormaId.value);
    }
    if (term.trim()) {
      url.searchParams.set("search", term.trim());
    }
    if (mostrarApenasVinculados.value) {
      url.searchParams.set("somente_vinculados", "1");
    }

    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`Erro ${response.status}`);
    }

    const data = await response.json();
    opcoes.value = (data.rows || []).map((item) => ({
      ...item,
      chave: buildKey(item),
    }));
  } catch (err) {
    console.error(err);
    opcoes.value = [];
  } finally {
    searching.value = false;
  }
}

function parseKey(key) {
  const [tipo_documento, idRaw] = String(key || "").split(":");
  return {
    tipo_documento: String(tipo_documento || "").trim().toUpperCase(),
    id_forma_origem: Number(idRaw),
  };
}

function buildPayloadFromKeys(keys) {
  const opcoesPorChave = new Map(opcoes.value.map((item) => [item.chave, item]));
  return keys
    .map((key) => {
      const parsed = parseKey(key);
      const opcao = opcoesPorChave.get(key);
      return {
        ...parsed,
        descricao_origem: String(opcao?.descricao_origem || "").trim(),
      };
    })
    .filter((item) => item.tipo_documento && Number.isInteger(item.id_forma_origem));
}

function submit() {
  if (!selectedFormaId.value) {
    localError.value = "Selecione a forma canônica para aplicar o mapeamento.";
    return;
  }

  if (!paraAdicionar.value.length && !paraRemover.value.length) {
    localError.value = "Nenhuma alteracao foi detectada.";
    return;
  }

  localError.value = "";
  emit("submit", {
    id_forma: Number(selectedFormaId.value),
    adicionar: buildPayloadFromKeys(paraAdicionar.value),
    remover: buildPayloadFromKeys(paraRemover.value),
  });
}

watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      resetState();
      fetchOpcoes("");
    }
  },
);

watch(search, (value) => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    fetchOpcoes(value);
  }, 300);
});

watch(mostrarApenasVinculados, () => {
  fetchOpcoes(search.value);
});

watch(selectedFormaId, () => {
  paraAdicionar.value = [];
  paraRemover.value = [];
  localError.value = "";
  fetchOpcoes(search.value);
});
</script>
