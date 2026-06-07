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

    <input
      :value="modelValue"
      :type="type"
      :inputmode="inputmode"
      :step="step"
      :required="required"
      :disabled="disabled"
      :readonly="readonly"
      :maxlength="maxlength"
      :class="[
        'w-full rounded-md border border-gray-200 px-3 py-2 text-sm',
        inputClass,
      ]"
      @input="onInput"
    />
  </label>
</template>

<script setup>
import { HelpCircle } from "lucide-vue-next";

const props = defineProps({
  modelValue: { type: [String, Number], default: "" },
  label: { type: String, default: "" },
  required: { type: Boolean, default: false },
  helpText: { type: String, default: "" },
  type: { type: String, default: "text" },
  inputmode: { type: String, default: undefined },
  step: { type: [String, Number], default: undefined },
  maxlength: { type: [String, Number], default: undefined },
  disabled: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },
  inputClass: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue"]);

function onInput(event) {
  emit("update:modelValue", event.target.value);
}
</script>
