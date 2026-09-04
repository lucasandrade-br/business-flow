<template>
  <div class="min-h-screen bg-white text-[#373435]">

    <!-- ═══════════════════════════ TOPBAR ════════════════════════════════════ -->
    <header class="fixed top-0 w-full z-50 bg-gray-50 border-b border-gray-200">
      <div class="h-16 flex items-center justify-between px-4">
        <div class="flex items-center gap-3">
          <button
            type="button"
            class="p-2 rounded-md text-gray-500 hover:bg-gray-100 transition-colors"
            :title="isPinned ? 'Recolher menu lateral' : 'Fixar menu lateral aberto'"
            @click="isPinned = !isPinned"
          >
            <PanelRightOpen v-if="isPinned" class="h-5 w-5" />
            <PanelRightClose v-else class="h-5 w-5" />
          </button>
          <div class="flex items-center gap-2">
            <span class="text-lg font-semibold tracking-tight text-gray-800">
              Padaria<span class="text-[#2f6f4f] font-bold">Digital</span>
            </span>
          </div>
        </div>

        <!-- Direita: seletor de filial -->
        <div class="relative" ref="dropdownRef">
          <button
            type="button"
            class="flex items-center gap-2 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            @click="dropdownOpen = !dropdownOpen"
          >
            <Building2 class="h-4 w-4 text-gray-400" />
            <span class="hidden sm:block font-medium">{{ filialAtiva.nome }}</span>
            <ChevronDown
              class="h-3.5 w-3.5 text-gray-400 transition-transform duration-150"
              :class="dropdownOpen ? 'rotate-180' : ''"
            />
          </button>

          <div
            v-if="dropdownOpen"
            class="absolute right-0 top-full mt-1.5 w-52 rounded-md border border-gray-200 bg-white shadow-lg overflow-hidden"
          >
            <p class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-gray-400 border-b border-gray-100">
              Selecionar Filial
            </p>
            <button
              v-for="f in FILIAIS"
              :key="f.id"
              type="button"
              class="flex w-full items-center gap-2.5 px-3 py-2.5 text-sm transition-colors"
              :class="f.id === filialAtiva.id ? 'bg-[#373435] text-white' : 'text-gray-700 hover:bg-gray-50'"
              @click="selectFilial(f)"
            >
              <Check v-if="f.id === filialAtiva.id" class="h-3.5 w-3.5 shrink-0" />
              <span v-else class="h-3.5 w-3.5 shrink-0" />
              {{ f.nome }}
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- ══════════════════════════ SIDEBAR ════════════════════════════════════ -->
    <aside
      class="group fixed top-16 left-0 z-40 flex h-[calc(100vh-4rem)] flex-col border-r border-gray-200 bg-gray-50 px-3 py-4 transition-all duration-300"
      :class="isExpanded ? 'w-64' : 'w-16'"
      @mouseenter="isHovered = true"
      @mouseleave="isHovered = false"
    >
      <nav
        class="min-h-0 flex-1 space-y-4"
        :class="isExpanded ? 'app-scrollbar overflow-y-auto pr-1' : 'overflow-y-hidden pr-0'"
      >
        <!-- Início -->
        <RouterLink
          to="/"
          :class="[
            `flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm transition-all ${isExpanded ? 'justify-start' : 'justify-center'}`,
            route.path === '/' ? 'bg-[#373435] font-medium text-white shadow-sm' : 'text-gray-600 hover:bg-[#4b4948] hover:text-white',
          ]"
        >
          <Home class="h-4 w-4 shrink-0" />
          <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Início</span>
        </RouterLink>

        <!-- Análises -->
        <RouterLink
          to="/analise"
          :class="[
            `flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm transition-all ${isExpanded ? 'justify-start' : 'justify-center'}`,
            route.path.startsWith('/analise') ? 'bg-[#373435] font-medium text-white shadow-sm' : 'text-gray-600 hover:bg-[#4b4948] hover:text-white',
          ]"
        >
          <BarChart2 class="h-4 w-4 shrink-0" />
          <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Análises</span>
        </RouterLink>

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
              <span class="overflow-hidden whitespace-nowrap transition-all duration-200" :class="isExpanded ? 'max-w-[180px] opacity-100' : 'max-w-0 opacity-0'">Integração de Dados</span>
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

    <div class="min-h-screen pt-16 transition-all duration-300 ease-in-out" :class="isPinned ? 'pl-64' : 'pl-16'">
      <main class="min-h-screen p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup>
import {
  ArrowRightLeft,
  BarChart2,
  Building2,
  Check,
  ClipboardList,
  ChevronDown,
  CheckSquare,
  CreditCard,
  FolderTree,
  Home,
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
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";
import { FILIAIS } from "@/config/filiais.js";
import { filialAtiva, setFilial } from "@/stores/filial.js";
import { mainSidebarPinned } from "@/stores/mainSidebar.js";

const route = useRoute();

// ── Seletor de filial ────────────────────────────────────────────────────────────────
const dropdownOpen = ref(false);
const dropdownRef = ref(null);

function selectFilial(f) {
  dropdownOpen.value = false;
  if (f.id !== filialAtiva.value.id) {
    setFilial(f);
    window.location.reload();
  }
}

function handleClickOutside(e) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target)) {
    dropdownOpen.value = false;
  }
}

watch(dropdownOpen, (isOpen) => {
  if (isOpen) {
    document.addEventListener("click", handleClickOutside, true);
  } else {
    document.removeEventListener("click", handleClickOutside, true);
  }
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleClickOutside, true);
});

const isPinned = mainSidebarPinned;
const isHovered = ref(false);
const isExpanded = computed(() => isPinned.value || isHovered.value);
const sectionOpen = ref({
  operacoes: true,
  cadastros: false,
  vendas: true,
  compras: true,
  sistema: false,
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

