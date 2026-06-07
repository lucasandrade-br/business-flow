<template>
  <transition
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition duration-150 ease-in"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div v-if="modelValue" class="fixed inset-0 z-40 bg-black/30" @click.self="close">
      <div class="absolute inset-0 flex items-end justify-center p-4 sm:items-center">
        <article class="w-full max-w-4xl rounded-md border border-gray-200 bg-white">
          <header class="flex items-start justify-between border-b border-gray-200 px-4 py-3">
            <div>
              <h3 class="text-sm font-semibold text-[#373435]">{{ title }}</h3>
              <p v-if="description" class="mt-1 text-xs text-gray-500">{{ description }}</p>
            </div>
            <button
              type="button"
              class="rounded-md border border-gray-200 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
              @click="close"
            >
              Fechar
            </button>
          </header>

          <section class="max-h-[75vh] overflow-auto px-4 py-4">
            <slot />
          </section>

          <footer class="flex items-center justify-end gap-2 border-t border-gray-200 px-4 py-3">
            <slot name="footer" />
          </footer>
        </article>
      </div>
    </div>
  </transition>
</template>

<script setup>
defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: "" },
  description: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue"]);

function close() {
  emit("update:modelValue", false);
}
</script>
