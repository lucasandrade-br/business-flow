<template>
  <BaseModal
    :model-value="modelValue"
    title="Cadastro em Lote - Plano de Contas"
    description="Selecione a conta pai e adicione varias contas filhas de uma vez."
    @update:model-value="(value) => emit('update:modelValue', value)"
  >
    <div class="space-y-4">
      <label class="space-y-1 text-xs">
        <span class="font-medium text-gray-600">Conta Pai</span>
        <select v-model="selectedContaPai" class="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm">
          <option value="">Nenhuma (Contas Raizes)</option>
          <option v-for="option in parentOptions" :key="option.value" :value="String(option.value)">
            {{ option.label }}
          </option>
        </select>
      </label>

      <section class="space-y-2">
        <h4 class="text-xs font-semibold uppercase tracking-wide text-gray-500">Contas Filhas</h4>
        <div v-for="(row, index) in rows" :key="row.id" class="flex items-center gap-2">
          <input
            :ref="(el) => setRowInputRef(el, index)"
            v-model="row.nome"
            type="text"
            class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm"
            placeholder="Nome da conta filha"
            @keydown.enter.prevent="onEnter(index)"
          />
          <button
            type="button"
            class="rounded-md border border-red-200 p-2 text-red-600 hover:bg-red-50"
            @click="removeRow(index)"
          >
            <Trash2 class="h-4 w-4" />
          </button>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-1 text-xs font-medium text-gray-700 hover:text-[#373435]"
          @click="addRowAndFocus()"
        >
          <Plus class="h-3.5 w-3.5" />
          Adicionar Nova Linha
        </button>
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
        {{ loading ? 'Salvando...' : 'Salvar Lote' }}
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { nextTick, ref, watch } from "vue";
import { Plus, Trash2 } from "lucide-vue-next";
import BaseModal from "@/components/ui/BaseModal.vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  parentOptions: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue", "submit"]);

const selectedContaPai = ref("");
const rows = ref([]);
const inputRefs = ref([]);
const localError = ref("");

function makeRow() {
  return { id: `${Date.now()}-${Math.random()}`, nome: "" };
}

function resetForm() {
  selectedContaPai.value = "";
  rows.value = [makeRow()];
  inputRefs.value = [];
  localError.value = "";
}

function setRowInputRef(el, index) {
  if (el) {
    inputRefs.value[index] = el;
  }
}

async function addRowAndFocus() {
  rows.value.push(makeRow());
  await nextTick();
  const lastIndex = rows.value.length - 1;
  inputRefs.value[lastIndex]?.focus();
}

function removeRow(index) {
  if (rows.value.length === 1) {
    rows.value[0].nome = "";
    return;
  }
  rows.value.splice(index, 1);
  inputRefs.value.splice(index, 1);
}

async function onEnter(index) {
  if (index === rows.value.length - 1) {
    await addRowAndFocus();
  }
}

function submit() {
  const filhas = rows.value
    .map((item) => String(item.nome || "").trim())
    .filter((item) => item.length > 0);

  if (!filhas.length) {
    localError.value = "Preencha ao menos uma conta filha para o lote.";
    return;
  }

  localError.value = "";
  emit("submit", {
    conta_pai_id: selectedContaPai.value === "" ? null : Number(selectedContaPai.value),
    filhas,
  });
}

watch(
  () => props.modelValue,
  async (value) => {
    if (value) {
      resetForm();
      await nextTick();
      inputRefs.value[0]?.focus();
    }
  },
);
</script>
