<template>
  <div ref="rootRef" class="relative">
    <button
      type="button"
      class="inline-flex min-w-[230px] items-center justify-between gap-2 rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
      @click="toggleOpen"
    >
      <span class="inline-flex items-center gap-1.5 truncate">
        <CalendarDays class="h-3.5 w-3.5 text-gray-400" />
        <span class="truncate">{{ displayLabel }}</span>
      </span>
      <ChevronDown class="h-3.5 w-3.5 text-gray-400" />
    </button>

    <div v-if="isOpen" class="absolute z-30 mt-1 w-[320px] rounded-md border border-gray-200 bg-white p-3 shadow-lg">
      <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <label class="flex flex-col gap-1">
          <span class="text-[11px] font-medium uppercase tracking-wide text-gray-500">Inicio</span>
          <input
            :value="start || ''"
            type="date"
            class="rounded-md border border-gray-200 px-2 py-1.5 text-xs outline-none focus:border-gray-300"
            @input="onStartInput"
          />
        </label>

        <label class="flex flex-col gap-1">
          <span class="text-[11px] font-medium uppercase tracking-wide text-gray-500">Fim</span>
          <input
            :value="end || ''"
            type="date"
            class="rounded-md border border-gray-200 px-2 py-1.5 text-xs outline-none focus:border-gray-300"
            @input="onEndInput"
          />
        </label>
      </div>

      <p v-if="isInvalidRange" class="mt-2 text-[11px] text-red-600">A data final nao pode ser menor que a inicial.</p>

      <div class="mt-3 flex flex-wrap gap-1.5">
        <button type="button" class="rounded border border-gray-200 px-2 py-1 text-[11px] text-gray-700 hover:bg-gray-50" @click="setToday">
          Hoje
        </button>
        <button type="button" class="rounded border border-gray-200 px-2 py-1 text-[11px] text-gray-700 hover:bg-gray-50" @click="setCurrentWeek">
          Semana atual
        </button>
        <button type="button" class="rounded border border-gray-200 px-2 py-1 text-[11px] text-gray-700 hover:bg-gray-50" @click="setLastDays(7)">
          Ultimos 7 dias
        </button>
        <button type="button" class="rounded border border-gray-200 px-2 py-1 text-[11px] text-gray-700 hover:bg-gray-50" @click="setLastDays(30)">
          Ultimos 30 dias
        </button>
        <button type="button" class="rounded border border-gray-200 px-2 py-1 text-[11px] text-gray-700 hover:bg-gray-50" @click="setCurrentMonth">
          Mes atual
        </button>
        <button type="button" class="rounded border border-gray-200 px-2 py-1 text-[11px] text-gray-700 hover:bg-gray-50" @click="setCurrentYear">
          Ano atual
        </button>
      </div>

      <div class="mt-3 flex items-center justify-between">
        <button type="button" class="text-[11px] text-gray-600 hover:text-gray-800" @click="clearRange">Limpar</button>
        <button
          type="button"
          class="rounded-md border border-gray-200 bg-white px-2.5 py-1 text-[11px] font-medium text-gray-700 hover:bg-gray-50"
          @click="isOpen = false"
        >
          Fechar
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { CalendarDays, ChevronDown } from "lucide-vue-next";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
  start: { type: String, default: "" },
  end: { type: String, default: "" },
  placeholder: { type: String, default: "Periodo (inicio e fim)" },
});

const emit = defineEmits(["update:start", "update:end"]);

const rootRef = ref(null);
const isOpen = ref(false);

const isInvalidRange = computed(() => {
  if (!props.start || !props.end) return false;
  return props.end < props.start;
});

const displayLabel = computed(() => {
  if (props.start && props.end) {
    return `${toBrDate(props.start)} ate ${toBrDate(props.end)}`;
  }
  if (props.start) {
    return `A partir de ${toBrDate(props.start)}`;
  }
  if (props.end) {
    return `Ate ${toBrDate(props.end)}`;
  }
  return props.placeholder;
});

function toBrDate(value) {
  if (!value) return "";
  const parts = value.split("-");
  if (parts.length !== 3) return value;
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
}

function toggleOpen() {
  isOpen.value = !isOpen.value;
}

function onStartInput(event) {
  const value = event?.target?.value || "";
  emit("update:start", value);
  if (value && props.end && value > props.end) {
    emit("update:end", value);
  }
}

function onEndInput(event) {
  const value = event?.target?.value || "";
  emit("update:end", value);
  if (value && props.start && value < props.start) {
    emit("update:start", value);
  }
}

function formatInputDate(date) {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function setRange(startDate, endDate) {
  emit("update:start", formatInputDate(startDate));
  emit("update:end", formatInputDate(endDate));
}

function setToday() {
  const today = new Date();
  setRange(today, today);
}

function setLastDays(days) {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(endDate.getDate() - (days - 1));
  setRange(startDate, endDate);
}

function setCurrentMonth() {
  const now = new Date();
  const startDate = new Date(now.getFullYear(), now.getMonth(), 1);
  const endDate = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  setRange(startDate, endDate);
}

function setCurrentWeek() {
  const now = new Date();
  const dayOfWeek = now.getDay();
  const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
  const startDate = new Date(now);
  startDate.setDate(now.getDate() + mondayOffset);
  const endDate = new Date(startDate);
  endDate.setDate(startDate.getDate() + 6);
  setRange(startDate, endDate);
}

function setCurrentYear() {
  const now = new Date();
  const startDate = new Date(now.getFullYear(), 0, 1);
  const endDate = new Date(now.getFullYear(), 11, 31);
  setRange(startDate, endDate);
}

function clearRange() {
  emit("update:start", "");
  emit("update:end", "");
}

function handleOutsideClick(event) {
  const root = rootRef.value;
  if (!root) return;
  if (!root.contains(event.target)) {
    isOpen.value = false;
  }
}

onMounted(() => {
  document.addEventListener("click", handleOutsideClick);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleOutsideClick);
});
</script>
