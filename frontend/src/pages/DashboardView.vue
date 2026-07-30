<script setup>
import { LayoutDashboard } from 'lucide-vue-next'
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-xl font-bold text-gray-900">Visão Geral</h1>
      <p class="text-sm text-gray-400 mt-0.5">Painel consolidado do negócio.</p>
    </div>
    <div class="rounded-xl border border-dashed border-gray-200 bg-gray-50/50 flex flex-col items-center justify-center gap-4 py-20">
      <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-gray-100">
        <LayoutDashboard class="h-5 w-5 text-gray-400" />
      </div>
      <div class="text-center">
        <p class="font-medium text-gray-600">Em definição</p>
        <p class="text-sm text-gray-400 mt-1">O conteúdo deste painel será definido em breve.</p>
      </div>
    </div>
  </div>
</template>