<template>
  <article class="overflow-hidden rounded-md border border-gray-200 bg-white">
    <header
      class="flex flex-col gap-3 border-b border-gray-200 px-4 py-3 sm:flex-row sm:items-center"
      :class="hasHeaderText ? 'sm:justify-between' : 'sm:justify-start'"
    >
      <div v-if="hasHeaderText">
        <h2 class="text-sm font-semibold text-[#373435]">{{ title }}</h2>
        <p v-if="subtitle" class="mt-1 text-xs text-gray-500">{{ subtitle }}</p>
      </div>
      <slot name="header-extra" />
    </header>

    <div v-if="loading" class="px-4 py-6 text-sm text-gray-500">Carregando...</div>
    <div v-else-if="error" class="px-4 py-6 text-sm text-red-600">{{ error }}</div>
    <div v-else-if="!rows.length" class="px-4 py-6 text-sm text-gray-500">{{ emptyText }}</div>

    <div v-else class="overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead>
          <tr class="border-b border-gray-100 bg-white text-left text-xs uppercase tracking-wide text-gray-500">
            <th v-for="column in columns" :key="column.key" class="px-4 py-3 font-medium" :class="column.headerClass">
              {{ column.label }}
            </th>
            <th v-if="$slots.actions" class="px-4 py-3 text-right font-medium">Acoes</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row[rowKey]"
            class="border-b border-gray-100 transition-colors hover:bg-gray-50"
            :class="selectedRowKeySet.has(row[rowKey]) ? 'bg-[#f7fafc]' : ''"
          >
            <td v-for="column in columns" :key="column.key" class="px-4 py-3" :class="column.cellClass">
              <slot :name="`cell-${column.key}`" :row="row">
                {{ row[column.key] }}
              </slot>
            </td>
            <td v-if="$slots.actions" class="px-4 py-3 text-right">
              <slot name="actions" :row="row" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="flex items-center justify-between border-t border-gray-200 px-4 py-3 text-xs text-gray-600">
      <span>{{ count }} registro(s)</span>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="rounded-md border border-gray-200 px-3 py-1.5 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="!previous"
          @click="$emit('previous')"
        >
          Anterior
        </button>
        <button
          type="button"
          class="rounded-md border border-gray-200 px-3 py-1.5 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="!next"
          @click="$emit('next')"
        >
          Próxima
        </button>
      </div>
    </footer>
  </article>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  title: { type: String, default: "" },
  subtitle: { type: String, default: "" },
  columns: { type: Array, required: true },
  rows: { type: Array, default: () => [] },
  rowKey: { type: String, default: "id" },
  count: { type: Number, default: 0 },
  next: { type: String, default: "" },
  previous: { type: String, default: "" },
  loading: { type: Boolean, default: false },
  error: { type: String, default: "" },
  emptyText: { type: String, default: "Nenhum registro." },
  selectedRowKeys: { type: Array, default: () => [] },
});

defineEmits(["next", "previous"]);

const hasHeaderText = computed(() => {
  return Boolean(String(props.title || "").trim() || String(props.subtitle || "").trim());
});

const selectedRowKeySet = computed(() => new Set(props.selectedRowKeys || []));
</script>
