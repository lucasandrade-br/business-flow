<template>
  <label class="space-y-1 text-xs">
    <span v-if="label" class="inline-flex items-center gap-1 font-medium text-gray-600">
      {{ label }}
      <span v-if="required" class="text-red-500">*</span>
      <span v-if="helpText" class="group relative inline-flex items-center">
        <HelpCircle class="h-4 w-4 text-gray-400" />
        <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-56 -translate-x-1/2 rounded-md bg-[#1f1f1f] px-2 py-1 text-[11px] font-normal text-white group-hover:block">
          {{ helpText }}
        </span>
      </span>
    </span>

    <div class="relative">
      <input
        ref="inputRef"
        type="text"
        inputmode="decimal"
        :required="required"
        class="w-full rounded-md border border-gray-200 px-3 py-2 pr-8 text-sm"
        :disabled="disabled"
      />
      <span class="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-gray-500">%</span>
    </div>
  </label>
</template>

<script setup>
import { HelpCircle } from "lucide-vue-next";
import { CurrencyDisplay, useCurrencyInput } from "vue-currency-input";
import { watch } from "vue";

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  disabled: { type: Boolean, default: false },
  label: { type: String, default: "" },
  required: { type: Boolean, default: false },
  helpText: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue"]);

const { inputRef, numberValue, setValue } = useCurrencyInput(
  {
    locale: "pt-BR",
    currency: "BRL",
    currencyDisplay: CurrencyDisplay.hidden,
    valueRange: { min: 0 },
    autoDecimalDigits: true,
    hideCurrencySymbolOnFocus: false,
    hideGroupingSeparatorOnFocus: false,
  },
  false,
);

watch(
  () => props.modelValue,
  (value) => {
    setValue(Number(value || 0));
  },
  { immediate: true },
);

watch(numberValue, (value) => {
  emit("update:modelValue", Number(value || 0));
});
</script>
