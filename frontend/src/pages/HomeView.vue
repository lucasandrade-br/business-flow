<script setup>
import { ArrowRight, ArrowRightLeft, CheckSquare, ClipboardList } from 'lucide-vue-next'

// placeholder — KPIs serão adicionados aqui futuramente

</script>

<template>
  <div class="flex flex-col gap-6">

    <!-- Título -->
    <div>
      <h1 class="text-xl font-bold text-gray-900">Painel de Controle</h1>
      <p class="text-sm text-gray-400 mt-0.5">
        Bem-vindo ao <span class="font-medium text-gray-600">PadariaDigital</span>. Selecione uma área para começar.
      </p>
    </div>

    <!-- Cards de acesso rápido -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-5">

      <!-- Card: Hub de Validação -->
      <RouterLink
        to="/validacao/produtos"
        class="group flex flex-col bg-white border border-gray-200 shadow-sm rounded-lg overflow-hidden hover:shadow-md transition-shadow"
      >
        <div class="flex-1 flex flex-col items-center justify-center p-8 gap-3">
          <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#373435] text-white shadow-sm">
            <CheckSquare class="h-6 w-6" />
          </div>
          <div class="text-center">
            <p class="font-semibold text-gray-800">Integração de Dados</p>
            <p class="text-xs text-gray-400 mt-1">Produtos pendentes de validação e conferência de cadastro</p>
          </div>
        </div>
        <div class="bg-[#373435] group-hover:bg-[#4b4948] text-white text-xs font-medium py-2.5 flex items-center justify-center gap-2 transition-colors">
          Acessar <ArrowRight class="h-3.5 w-3.5" />
        </div>
      </RouterLink>

      <!-- Card: Integração de Vendas -->
      <RouterLink
        to="/validacao/reconciliacao"
        class="group flex flex-col bg-white border border-gray-200 shadow-sm rounded-lg overflow-hidden hover:shadow-md transition-shadow"
      >
        <div class="flex-1 flex flex-col items-center justify-center p-8 gap-3">
          <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#373435] text-white shadow-sm">
            <ArrowRightLeft class="h-6 w-6" />
          </div>
          <div class="text-center">
            <p class="font-semibold text-gray-800">Integração de Vendas</p>
            <p class="text-xs text-gray-400 mt-1">Sincronização e reconciliação das vendas do sistema legado</p>
          </div>
        </div>
        <div class="bg-[#373435] group-hover:bg-[#4b4948] text-white text-xs font-medium py-2.5 flex items-center justify-center gap-2 transition-colors">
          Acessar <ArrowRight class="h-3.5 w-3.5" />
        </div>
      </RouterLink>

      <!-- Card: Integração de Compras -->
      <RouterLink
        to="/compras/reconciliacao"
        class="group flex flex-col bg-white border border-gray-200 shadow-sm rounded-lg overflow-hidden hover:shadow-md transition-shadow"
      >
        <div class="flex-1 flex flex-col items-center justify-center p-8 gap-3">
          <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#373435] text-white shadow-sm">
            <ClipboardList class="h-6 w-6" />
          </div>
          <div class="text-center">
            <p class="font-semibold text-gray-800">Integração de Compras</p>
            <p class="text-xs text-gray-400 mt-1">Importação e conciliação das notas fiscais de entrada</p>
          </div>
        </div>
        <div class="bg-[#373435] group-hover:bg-[#4b4948] text-white text-xs font-medium py-2.5 flex items-center justify-center gap-2 transition-colors">
          Acessar <ArrowRight class="h-3.5 w-3.5" />
        </div>
      </RouterLink>

    </div>
  </div>
</template>
