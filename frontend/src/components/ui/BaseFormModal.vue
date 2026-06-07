<template>
  <transition
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition duration-150 ease-in"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div v-if="modelValue" class="fixed inset-0 z-50 bg-black/40 backdrop-blur-[1px]" @click.self="close">
      <div class="absolute inset-0 flex items-end justify-center p-4 sm:items-center">
        <article class="w-full max-w-2xl rounded-md border border-gray-200 bg-white">
          <header class="flex items-center justify-between border-b border-gray-200 px-4 py-3">
            <h3 class="text-sm font-semibold text-[#373435]">{{ title }}</h3>
            <button
              type="button"
              class="rounded-md border border-gray-200 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
              @click="close"
            >
              Fechar
            </button>
          </header>

          <section class="max-h-[70vh] overflow-auto px-4 py-4">
            <div class="grid gap-3 sm:grid-cols-2">
              <label v-for="field in fields" :key="field.name" class="space-y-1 text-xs">
                <span class="inline-flex items-center gap-1 font-medium text-gray-600">
                  {{ field.label }}
                  <span v-if="field.required" class="text-red-500">*</span>
                  <span v-if="field.helpText" class="group relative inline-flex items-center">
                    <HelpCircle class="h-4 w-4 text-gray-400" />
                    <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-56 -translate-x-1/2 rounded-md bg-[#1f1f1f] px-2 py-1 text-[11px] font-normal text-white group-hover:block">
                      {{ field.helpText }}
                    </span>
                  </span>
                </span>

                <select
                  v-if="field.type === 'select'"
                  v-model="form[field.name]"
                  @blur="handleBlur(field)"
                  :required="field.required"
                  class="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm"
                >
                  <option :value="field.emptyValue ?? ''">{{ field.placeholder || 'Selecione' }}</option>
                  <option v-for="option in field.options || []" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </option>
                </select>

                <textarea
                  v-else-if="field.type === 'textarea'"
                  v-model="form[field.name]"
                  @blur="handleBlur(field)"
                  :required="field.required"
                  class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm"
                  :rows="field.rows || 3"
                />

                <input
                  v-else
                  v-model="form[field.name]"
                  @blur="handleBlur(field)"
                  :required="field.required"
                  :type="field.type || 'text'"
                  :step="field.step"
                  :maxlength="field.maxlength"
                  class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm"
                />
              </label>
            </div>

            <p v-if="error" class="mt-3 text-xs text-red-600">{{ error }}</p>
          </section>

          <footer class="flex items-center justify-end gap-2 border-t border-gray-200 px-4 py-3">
            <button
              type="button"
              class="rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50"
              @click="close"
            >
              Cancelar
            </button>
            <button
              type="button"
              class="rounded-md bg-black px-3 py-2 text-xs font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="saving"
              @click="submit"
            >
              {{ saving ? 'Salvando...' : submitLabel }}
            </button>
          </footer>
        </article>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { HelpCircle } from "lucide-vue-next";
import { reactive, watch } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: "Cadastro" },
  fields: { type: Array, default: () => [] },
  initialValues: { type: Object, default: () => ({}) },
  submitLabel: { type: String, default: "Salvar" },
  saving: { type: Boolean, default: false },
  error: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue", "submit"]);
const form = reactive({});

watch(
  () => [props.modelValue, props.initialValues],
  () => {
    if (props.modelValue) {
      Object.keys(form).forEach((key) => delete form[key]);
      Object.assign(form, props.initialValues || {});
    }
  },
  { immediate: true, deep: true },
);

function close() {
  emit("update:modelValue", false);
}

function submit() {
  emit("submit", { ...form });
}

function handleBlur(field) {
  if (typeof field?.onBlur !== "function") {
    return;
  }

  form[field.name] = field.onBlur(form[field.name], { ...form });
}
</script>
