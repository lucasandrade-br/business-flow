<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { BarChart2, CalendarDays, ChevronDown, ChevronRight, Layers3, PackageSearch, ShoppingCart, TrendingUp } from 'lucide-vue-next'
import { mainSidebarPinned } from '@/stores/mainSidebar.js'

onMounted(() => { mainSidebarPinned.value = false })

const route = useRoute()
const sectionOpen = ref({ visaoGeral: true, vendas: true, compras: true, categorias: true })

function toggleSection(key) {
  sectionOpen.value[key] = !sectionOpen.value[key]
}

const sidebarLeft = computed(() => mainSidebarPinned.value ? '16rem' : '4rem')
const currentTitle = computed(() => route.meta?.title ?? '')

function linkClass(to) {
  const active = route.path === to || route.path.startsWith(to + '/')
  return [
    'flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm transition-colors',
    active
      ? 'bg-[#373435] font-medium text-white shadow-sm'
      : 'text-gray-600 hover:bg-[#4b4948] hover:text-white',
  ]
}
</script>

<template>
  <!-- Sub-topbar: abaixo da topbar principal, acima da sidebar analítica -->
  <div
    class="fixed top-16 right-0 z-30 h-10 bg-white border-b border-gray-200 flex items-center px-4 transition-all duration-300"
    :style="{ left: sidebarLeft }"
  >
    <nav class="flex items-center gap-1.5 text-sm">
      <span class="font-medium text-gray-500">Módulo Analítico</span>
      <ChevronRight class="h-3.5 w-3.5 text-gray-300" />
      <span class="font-semibold text-gray-800">{{ currentTitle }}</span>
    </nav>
  </div>

  <!-- Sidebar analítica: inicia abaixo da sub-topbar -->
  <aside
    class="fixed z-20 w-56 bg-white border-r border-gray-200 flex flex-col px-3 py-4 transition-all duration-300"
    :style="{ top: '6.5rem', left: sidebarLeft, height: 'calc(100vh - 6.5rem)' }"
  >
    <!-- Cabeçalho do módulo -->
    <div class="mb-4 pb-3 border-b border-gray-200">
      <div class="flex items-center gap-2 px-1">
        <div class="flex h-6 w-6 items-center justify-center rounded-md bg-[#373435] shrink-0">
          <BarChart2 class="h-3.5 w-3.5 text-white" />
        </div>
        <span class="text-[10px] font-bold uppercase tracking-wider text-[#373435]">Módulo Analítico</span>
      </div>
    </div>

    <!-- Navegação -->
    <nav class="app-scrollbar app-scrollbar--compact flex-1 overflow-y-auto space-y-4">
      <section>
        <button
          type="button"
          class="flex w-full items-center justify-between rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-500 hover:bg-gray-100"
          @click="toggleSection('visaoGeral')"
        >
          <span>Visão Geral</span>
          <ChevronDown class="h-3.5 w-3.5 transition-transform duration-200" :class="sectionOpen.visaoGeral ? 'rotate-0' : '-rotate-90'" />
        </button>
        <div class="mt-1 space-y-1 overflow-hidden transition-all duration-200" :class="sectionOpen.visaoGeral ? 'max-h-56 opacity-100' : 'max-h-0 opacity-0'">
          <RouterLink to="/analise/visao-geral" :class="linkClass('/analise/visao-geral')">
            <BarChart2 class="h-4 w-4 shrink-0" />
            <span class="whitespace-nowrap">Geral</span>
          </RouterLink>
        </div>
      </section>

      <section>
        <button
          type="button"
          class="flex w-full items-center justify-between rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-500 hover:bg-gray-100"
          @click="toggleSection('vendas')"
        >
          <span>Vendas</span>
          <ChevronDown class="h-3.5 w-3.5 transition-transform duration-200" :class="sectionOpen.vendas ? 'rotate-0' : '-rotate-90'" />
        </button>
        <div class="mt-1 space-y-1 overflow-hidden transition-all duration-200" :class="sectionOpen.vendas ? 'max-h-56 opacity-100' : 'max-h-0 opacity-0'">
          <RouterLink to="/analise/vendas" :class="linkClass('/analise/vendas')">
            <TrendingUp class="h-4 w-4 shrink-0" />
            <span class="whitespace-nowrap">Análise de Vendas</span>
          </RouterLink>
          <RouterLink to="/analise/movimento-clientes" :class="linkClass('/analise/movimento-clientes')">
            <CalendarDays class="h-4 w-4 shrink-0" />
            <span class="whitespace-nowrap">Movimento Clientes</span>
          </RouterLink>
          <RouterLink to="/analise/categorias/vendas" :class="linkClass('/analise/categorias/vendas')">
            <Layers3 class="h-4 w-4 shrink-0" />
            <span class="whitespace-nowrap">Por Categoria</span>
          </RouterLink>
          <RouterLink to="/analise/categorias/produtos/vendas" :class="linkClass('/analise/categorias/produtos/vendas')">
            <PackageSearch class="h-4 w-4 shrink-0" />
            <span class="whitespace-nowrap">Por Produto</span>
          </RouterLink>


        </div>
      </section>

      <section>
        <button
          type="button"
          class="flex w-full items-center justify-between rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-500 hover:bg-gray-100"
          @click="toggleSection('compras')"
        >
          <span>Compras</span>
          <ChevronDown class="h-3.5 w-3.5 transition-transform duration-200" :class="sectionOpen.compras ? 'rotate-0' : '-rotate-90'" />
        </button>
        <div class="mt-1 space-y-1 overflow-hidden transition-all duration-200" :class="sectionOpen.compras ? 'max-h-56 opacity-100' : 'max-h-0 opacity-0'">
          <RouterLink to="/analise/compras" :class="linkClass('/analise/compras')">
            <ShoppingCart class="h-4 w-4 shrink-0" />
            <span class="whitespace-nowrap">Análise de Compras</span>
          </RouterLink>
          <RouterLink to="/analise/categorias/compras" :class="linkClass('/analise/categorias/compras')">
            <Layers3 class="h-4 w-4 shrink-0" />
            <span class="whitespace-nowrap">Por Categoria</span>
          </RouterLink>
          <RouterLink to="/analise/categorias/produtos/compras" :class="linkClass('/analise/categorias/produtos/compras')">
            <PackageSearch class="h-4 w-4 shrink-0" />
            <span class="whitespace-nowrap">Por Produto</span>
          </RouterLink>
        </div>
      </section>


    </nav>
  </aside>

  <!-- Área de conteúdo: offset exato para não cobrir sub-topbar (pt-10) e sidebar (pl-56) -->
  <div class="pt-10 pl-56">
    <RouterView />
  </div>
</template>

