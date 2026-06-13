<template>
  <div class="min-h-screen bg-white text-[#373435]">
    <aside
      class="group fixed inset-y-0 left-0 z-30 flex h-screen flex-col border-r border-gray-200 bg-gray-50 px-3 py-4 transition-all duration-300"
      :class="isExpanded ? 'w-64' : 'w-16'"
      @mouseenter="isHovered = true"
      @mouseleave="isHovered = false"
    >
      <div class="relative flex items-start px-1" :class="isExpanded ? 'gap-2' : 'justify-center'">
        <div class="flex h-9 w-9 items-center justify-center rounded-xl bg-[#373435] text-white shadow-sm ring-1 ring-[#373435]/10">
          <Network class="h-4 w-4" />
        </div>
        <div class="overflow-hidden transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">
          <p class="text-xs uppercase tracking-[0.2em] text-gray-500">Business Flow</p>
          <h1 class="text-sm font-semibold">Painel Operacional</h1>
        </div>
        <button
          type="button"
          class="absolute right-1 top-0 rounded-md border border-gray-200 bg-white p-1 text-gray-600 opacity-0 transition-opacity duration-200 pointer-events-none group-hover:pointer-events-auto group-hover:opacity-100 hover:bg-gray-100"
          :class="{ 'opacity-100 pointer-events-auto': isPinned }"
          :title="isPinned ? 'Desfixar menu lateral' : 'Fixar menu lateral aberto'"
          @click="isPinned = !isPinned"
        >
          <PanelRightOpen v-if="isPinned" class="h-4 w-4" />
          <PanelRightClose v-else class="h-4 w-4" />
        </button>
      </div>

      <nav
        class="mt-5 min-h-0 flex-1 space-y-4"
        :class="isExpanded ? 'sidebar-scroll overflow-y-auto pr-1' : 'overflow-y-hidden pr-0'"
      >
        <section>
          <button
            v-if="isExpanded"
            type="button"
            class="flex w-full items-center justify-between rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-500 hover:bg-gray-100"
            @click="toggleSection('operacoes')"
          >
            <span>Operações</span>
            <ChevronDown class="h-3.5 w-3.5 transition-transform duration-200" :class="sectionOpen.operacoes ? 'rotate-0' : '-rotate-90'" />
          </button>
          <div class="space-y-1 overflow-hidden transition-all duration-200" :class="sectionVisible('operacoes') ? 'max-h-56 opacity-100' : 'max-h-0 opacity-0'">
            <RouterLink :to="'/validacao/produtos'" :class="linkClass('/validacao/produtos')" class="mt-2">
              <CheckSquare class="h-4 w-4 shrink-0" />
              <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Hub de Validação</span>
            </RouterLink>
            <RouterLink :to="'/validacao/reconciliacao'" :class="linkClass('/validacao/reconciliacao')" class="mt-1">
              <ArrowRightLeft class="h-4 w-4 shrink-0" />
              <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Integração de Vendas</span>
            </RouterLink>
            <RouterLink :to="'/compras/reconciliacao'" :class="linkClass('/compras/reconciliacao')" class="mt-1">
              <ClipboardList class="h-4 w-4 shrink-0" />
              <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Integração de Compras</span>
            </RouterLink>
          </div>
        </section>

        <section>
          <button
            v-if="isExpanded"
            type="button"
            class="flex w-full items-center justify-between rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-500 hover:bg-gray-100"
            @click="toggleSection('compras')"
          >
            <span>Compras</span>
            <ChevronDown class="h-3.5 w-3.5 transition-transform duration-200" :class="sectionOpen.compras ? 'rotate-0' : '-rotate-90'" />
          </button>
          <div class="mt-2 space-y-1 overflow-hidden transition-all duration-200" :class="sectionVisible('compras') ? 'max-h-56 opacity-100' : 'max-h-0 opacity-0'">
            <RouterLink :to="'/compras/compras'" :class="linkClass('/compras/compras')">
              <Receipt class="h-4 w-4 shrink-0" />
              <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Compras</span>
            </RouterLink>
            <RouterLink :to="'/compras/itens'" :class="linkClass('/compras/itens')">
              <ShoppingCart class="h-4 w-4 shrink-0" />
              <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Itens</span>
            </RouterLink>
          </div>
        </section>

        

        <section>
          <button
            v-if="isExpanded"
            type="button"
            class="flex w-full items-center justify-between rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-500 hover:bg-gray-100"
            @click="toggleSection('vendas')"
          >
            <span>Vendas</span>
            <ChevronDown class="h-3.5 w-3.5 transition-transform duration-200" :class="sectionOpen.vendas ? 'rotate-0' : '-rotate-90'" />
          </button>
          <div class="mt-2 space-y-1 overflow-hidden transition-all duration-200" :class="sectionVisible('vendas') ? 'max-h-56 opacity-100' : 'max-h-0 opacity-0'">
            <RouterLink :to="'/vendas/vendas'" :class="linkClass('/vendas/vendas')">
              <Receipt class="h-4 w-4 shrink-0" />
              <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Vendas</span>
            </RouterLink>
            <RouterLink :to="'/vendas/itens'" :class="linkClass('/vendas/itens')">
              <ShoppingCart class="h-4 w-4 shrink-0" />
              <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Itens</span>
            </RouterLink>
            <RouterLink :to="'/vendas/pagamentos'" :class="linkClass('/vendas/pagamentos')">
              <CreditCard class="h-4 w-4 shrink-0" />
              <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Pagamentos</span>
            </RouterLink>
          </div>
        </section>

        <section>
          <button
            v-if="isExpanded"
            type="button"
            class="flex w-full items-center justify-between rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-500 hover:bg-gray-100"
            @click="toggleSection('cadastros')"
          >
            <span>Cadastros</span>
            <ChevronDown class="h-3.5 w-3.5 transition-transform duration-200" :class="sectionOpen.cadastros ? 'rotate-0' : '-rotate-90'" />
          </button>
          <div class="mt-2 space-y-1 overflow-hidden transition-all duration-200" :class="sectionVisible('cadastros') ? 'max-h-64 opacity-100' : 'max-h-0 opacity-0'">
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
          <button
            v-if="isExpanded"
            type="button"
            class="flex w-full items-center justify-between rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-500 hover:bg-gray-100"
            @click="toggleSection('sistema')"
          >
            <span>Sistema</span>
            <ChevronDown class="h-3.5 w-3.5 transition-transform duration-200" :class="sectionOpen.sistema ? 'rotate-0' : '-rotate-90'" />
          </button>
          <div class="mt-2 space-y-1 overflow-hidden transition-all duration-200" :class="sectionVisible('sistema') ? 'max-h-40 opacity-100' : 'max-h-0 opacity-0'">
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
  ClipboardList,
  ChevronDown,
  CheckSquare,
  CreditCard,
  FolderTree,
  Package,
  PanelRightClose,
  PanelRightOpen,
  Receipt,
  Network,
  SlidersHorizontal,
  ShoppingCart,
  Settings,
  Users,
} from "lucide-vue-next";
import { computed, ref } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

const route = useRoute();
const isPinned = ref(false);
const isHovered = ref(false);
const isExpanded = computed(() => isPinned.value || isHovered.value);
const sectionOpen = ref({
  operacoes: true,
  cadastros: true,
  vendas: true,
  compras: true,
  sistema: true,
});

function toggleSection(key) {
  sectionOpen.value[key] = !sectionOpen.value[key];
}

function sectionVisible(key) {
  if (!isExpanded.value) return true;
  return sectionOpen.value[key];
}

function linkClass(prefix) {
  const active = route.path.startsWith(prefix);
  return [
    `flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm transition-all ${isExpanded.value ? 'justify-start' : 'justify-center'}`,
    active ? "bg-[#373435] font-medium text-white shadow-sm" : "text-gray-600 hover:bg-[#4b4948] hover:text-white",
  ];
}
</script>

<style scoped>
.sidebar-scroll {
  scrollbar-width: thin;
  scrollbar-color: #c4c4c4 transparent;
}

.sidebar-scroll::-webkit-scrollbar {
  width: 8px;
}

.sidebar-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-scroll::-webkit-scrollbar-thumb {
  background-color: #c4c4c4;
  border-radius: 9999px;
}

.sidebar-scroll::-webkit-scrollbar-thumb:hover {
  background-color: #9c9c9c;
}
</style>
