<template>
  <div class="min-h-screen bg-white text-[#373435]">
    <aside
      class="group fixed inset-y-0 left-0 z-30 h-screen border-r border-gray-200 bg-gray-50 px-3 py-4 transition-all duration-300"
      :class="isExpanded ? 'w-64' : 'w-16'"
      @mouseenter="isHovered = true"
      @mouseleave="isHovered = false"
    >
      <div class="flex items-start justify-between gap-2 px-1">
        <div class="flex h-8 w-8 items-center justify-center rounded-md bg-white text-[#373435]">BF</div>
        <div class="overflow-hidden transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">
          <p class="text-xs uppercase tracking-[0.2em] text-gray-500">Business Flow</p>
          <h1 class="text-sm font-semibold">Painel Operacional</h1>
        </div>
        <button
          type="button"
          class="rounded-md border border-gray-200 bg-white p-1 text-gray-600 opacity-0 transition-opacity duration-200 pointer-events-none group-hover:pointer-events-auto group-hover:opacity-100 hover:bg-gray-100"
          :class="{ 'opacity-100 pointer-events-auto': isPinned }"
          :title="isPinned ? 'Desfixar menu lateral' : 'Fixar menu lateral aberto'"
          @click="isPinned = !isPinned"
        >
          <PanelRightOpen v-if="isPinned" class="h-4 w-4" />
          <PanelRightClose v-else class="h-4 w-4" />
        </button>
      </div>

      <nav class="mt-5 space-y-5">
        <section>
          <p class="overflow-hidden px-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-400 transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">OPERAÇÕES</p>
          <RouterLink :to="'/validacao/produtos'" :class="linkClass('/validacao/produtos')" class="mt-2">
            <CheckSquare class="h-4 w-4 shrink-0" />
            <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Hub de Validação</span>
          </RouterLink>
          <RouterLink :to="'/validacao/reconciliacao'" :class="linkClass('/validacao/reconciliacao')" class="mt-1">
            <ArrowRightLeft class="h-4 w-4 shrink-0" />
            <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Integração de Vendas</span>
          </RouterLink>
        </section>

        <section>
          <p class="overflow-hidden px-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-400 transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">CADASTROS</p>
          <div class="mt-2 space-y-1">
            <RouterLink :to="'/cadastros/clientes'" :class="linkClass('/cadastros/clientes')">
              <Users class="h-4 w-4 shrink-0" />
              <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Clientes</span>
            </RouterLink>
            <RouterLink :to="'/cadastros/fornecedores'" :class="linkClass('/cadastros/fornecedores')">
              <Building2 class="h-4 w-4 shrink-0" />
              <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Fornecedores</span>
            </RouterLink>
            <RouterLink :to="'/cadastros/produtos'" :class="linkClass('/cadastros/produtos')">
              <Package class="h-4 w-4 shrink-0" />
              <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Produtos</span>
            </RouterLink>
            <RouterLink :to="'/cadastros/plano-contas'" :class="linkClass('/cadastros/plano-contas')">
              <FolderTree class="h-4 w-4 shrink-0" />
              <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Plano de Contas</span>
            </RouterLink>
          </div>
        </section>

        <section>
          <p class="overflow-hidden px-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-400 transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">SISTEMA</p>
          <div class="mt-2 space-y-1">
            <RouterLink :to="'/cadastros/parametros'" :class="linkClass('/cadastros/parametros')">
              <SlidersHorizontal class="h-4 w-4 shrink-0" />
              <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Parâmetros</span>
            </RouterLink>
            <RouterLink :to="'/sistema'" :class="linkClass('/sistema')">
              <Settings class="h-4 w-4 shrink-0" />
              <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Configurações</span>
            </RouterLink>
          </div>
        </section>
      </nav>
    </aside>

    <div class="min-h-screen transition-all duration-300 ease-in-out" :class="isPinned ? 'pl-64' : 'pl-16'">
      <main class="min-h-screen p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup>
import {
  ArrowRightLeft,
  Building2,
  CheckSquare,
  FolderTree,
  Package,
  PanelRightClose,
  PanelRightOpen,
  SlidersHorizontal,
  Settings,
  Users,
} from "lucide-vue-next";
import { computed, ref } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

const route = useRoute();
const isPinned = ref(false);
const isHovered = ref(false);
const isExpanded = computed(() => isPinned.value || isHovered.value);

function linkClass(prefix) {
  const active = route.path.startsWith(prefix);
  return [
    `flex items-center gap-2 rounded-md px-2 py-2 text-sm transition-all ${isExpanded.value ? 'justify-start' : 'justify-center'}`,
    active ? "bg-white font-medium text-[#373435]" : "text-gray-600 hover:bg-white",
  ];
}
</script>
