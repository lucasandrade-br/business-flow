<template>
  <BaseModal
    :model-value="modelValue"
    title="Central de Vinculos"
    description="Associe multiplos produtos a uma categoria do Plano de Contas."
    @update:model-value="(value) => emit('update:modelValue', value)"
  >
    <div class="space-y-4">
      <label class="space-y-1 text-xs">
        <span class="font-medium text-gray-600">Categoria</span>
        <select v-model="selectedCategoriaId" class="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm">
          <option value="">Selecione uma categoria</option>
          <option v-for="option in categoriasOptions" :key="option.value" :value="String(option.value)">
            {{ option.label }}
          </option>
        </select>
      </label>

      <label class="space-y-1 text-xs">
        <span class="font-medium text-gray-600">Buscar Produtos</span>
        <div class="flex items-center gap-2">
          <input
            v-model="search"
            type="text"
            class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm"
            placeholder="Buscar produtos por nome ou codigo..."
          />
          <button
            type="button"
            class="inline-flex shrink-0 items-center gap-1 rounded-md border px-3 py-2 text-xs font-medium transition-colors"
            :class="mostrarApenasVinculados ? 'border-black bg-black text-white' : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'"
            @click="mostrarApenasVinculados = !mostrarApenasVinculados"
          >
            <Filter class="h-3.5 w-3.5" />
            Mostrar apenas vinculados
          </button>
        </div>
      </label>

      <section class="space-y-2">
        <div class="flex items-center justify-between text-xs text-gray-500">
          <span>Resultado da busca</span>
          <span>{{ totalSelecionados }} alteracao(oes)</span>
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
          <p v-if="searching" class="px-2 py-2 text-xs text-gray-500">Buscando produtos...</p>
          <p v-else-if="!produtos.length" class="px-2 py-2 text-xs text-gray-500">Nenhum produto encontrado.</p>

          <label
            v-for="produto in produtos"
            :key="produto.id_produto"
            class="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-gray-50"
          >
            <input
              :checked="isProdutoSelecionado(produto)"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300"
              @change="toggleProduto(produto, $event.target.checked)"
            />
            <span class="font-medium text-gray-700">{{ produto.produto }}</span>
            <span class="text-gray-400">#{{ produto.id_produto }}</span>
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
        {{ loading ? 'Aplicando...' : 'Aplicar Vinculos' }}
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Filter } from "lucide-vue-next";
import BaseModal from "@/components/ui/BaseModal.vue";

const API_BASE_URL = "http://127.0.0.1:8000";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  categoriasOptions: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue", "submit"]);

const selectedCategoriaId = ref("");
const search = ref("");
const mostrarApenasVinculados = ref(false);
const produtos = ref([]);
const searching = ref(false);
const idsParaAdicionar = ref([]);
const idsParaRemover = ref([]);
const localError = ref("");
const selectAllRef = ref(null);

let debounceTimer;

function resetState() {
  selectedCategoriaId.value = "";
  search.value = "";
  mostrarApenasVinculados.value = false;
  produtos.value = [];
  idsParaAdicionar.value = [];
  idsParaRemover.value = [];
  localError.value = "";
}

const totalSelecionados = computed(() => {
  return idsParaAdicionar.value.length + idsParaRemover.value.length;
});

function isOriginalmenteVinculado(produto) {
  if (!selectedCategoriaId.value) {
    return false;
  }
  const categoriaAtualId = Number(selectedCategoriaId.value);
  const categoriasProduto = Array.isArray(produto.categorias) ? produto.categorias.map((id) => Number(id)) : [];
  return categoriasProduto.includes(categoriaAtualId);
}

function isProdutoSelecionado(produto) {
  const idProduto = Number(produto.id_produto);
  if (idsParaAdicionar.value.includes(idProduto)) {
    return true;
  }
  if (idsParaRemover.value.includes(idProduto)) {
    return false;
  }
  return isOriginalmenteVinculado(produto);
}

function removeFromArray(listRef, idProduto) {
  listRef.value = listRef.value.filter((id) => id !== idProduto);
}

function pushUnique(listRef, idProduto) {
  if (!listRef.value.includes(idProduto)) {
    listRef.value.push(idProduto);
  }
}

function toggleProduto(produto, checked) {
  const idProduto = Number(produto.id_produto);
  const originalmenteVinculado = isOriginalmenteVinculado(produto);

  if (checked) {
    if (originalmenteVinculado) {
      removeFromArray(idsParaRemover, idProduto);
    } else {
      pushUnique(idsParaAdicionar, idProduto);
      removeFromArray(idsParaRemover, idProduto);
    }
    return;
  }

  if (originalmenteVinculado) {
    pushUnique(idsParaRemover, idProduto);
    removeFromArray(idsParaAdicionar, idProduto);
  } else {
    removeFromArray(idsParaAdicionar, idProduto);
    removeFromArray(idsParaRemover, idProduto);
  }
}

const allRenderedChecked = computed(() => {
  if (!produtos.value.length) return false;
  return produtos.value.every((produto) => isProdutoSelecionado(produto));
});

const someRenderedChecked = computed(() => {
  return produtos.value.some((produto) => isProdutoSelecionado(produto));
});

watch([allRenderedChecked, someRenderedChecked], () => {
  if (!selectAllRef.value) return;
  selectAllRef.value.indeterminate = !allRenderedChecked.value && someRenderedChecked.value;
});

function toggleSelecionarTodos(checked) {
  for (const produto of produtos.value) {
    toggleProduto(produto, checked);
  }
}

async function fetchProdutos(term = "") {
  searching.value = true;
  try {
    const url = new URL(`${API_BASE_URL}/api/cadastros/produtos`);
    if (term.trim()) {
      url.searchParams.set("search", term.trim());
    }
    if (mostrarApenasVinculados.value && selectedCategoriaId.value !== "") {
      url.searchParams.set("categoria_id", selectedCategoriaId.value);
    }
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`Erro ${response.status}`);
    }
    const data = await response.json();
    produtos.value = data.results || [];
  } catch (err) {
    console.error(err);
    produtos.value = [];
  } finally {
    searching.value = false;
  }
}

function submit() {
  if (selectedCategoriaId.value === "") {
    localError.value = "Selecione uma categoria para aplicar os vinculos.";
    return;
  }

  if (!idsParaAdicionar.value.length && !idsParaRemover.value.length) {
    localError.value = "Nenhuma alteracao foi detectada.";
    return;
  }

  localError.value = "";
  emit("submit", {
    categoria_id: Number(selectedCategoriaId.value),
    adicionar_ids: [...idsParaAdicionar.value],
    remover_ids: [...idsParaRemover.value],
  });
}

watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      resetState();
      fetchProdutos("");
    }
  },
);

watch(search, (value) => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    fetchProdutos(value);
  }, 300);
});

watch(mostrarApenasVinculados, () => {
  fetchProdutos(search.value);
});

watch(selectedCategoriaId, () => {
  idsParaAdicionar.value = [];
  idsParaRemover.value = [];
  localError.value = "";
  fetchProdutos(search.value);
});
</script>
