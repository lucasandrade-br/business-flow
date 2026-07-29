<template>
  <article class="rounded-md border border-gray-200 bg-white p-4 space-y-3">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <h3 class="text-xs font-semibold uppercase tracking-wide text-gray-500">Resumo da Importação e Validação</h3>
      <button type="button" class="rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50" @click="abrirConfirmacaoNovaImportacao">
        Nova importação
      </button>
    </div>

    <!-- KPIs colapsáveis -->
    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <button
        type="button"
        class="flex w-full items-center justify-between bg-gradient-to-r from-gray-50 to-white px-4 py-2.5 text-left"
        @click="mostrarKpis = !mostrarKpis"
      >
        <div class="flex items-center gap-2">
          <div class="flex h-5 w-5 items-center justify-center rounded-full bg-[#373435] shadow-sm">
            <BarChart2 class="h-3 w-3 text-white" />
          </div>
          <span class="text-xs font-bold uppercase tracking-wider text-[#373435]">KPIs da Reconciliação</span>
          <span
            v-if="Number(kpis.vendas_divergentes || 0) > 0"
            class="rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-semibold text-red-700"
          >{{ kpis.vendas_divergentes }} pendentes</span>
        </div>
        <ChevronDown
          class="h-4 w-4 text-gray-400 transition-transform duration-200"
          :class="mostrarKpis ? 'rotate-180' : ''"
        />
      </button>

      <div v-if="mostrarKpis" class="border-t border-gray-200 px-4 py-3 space-y-2">
        <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <div class="rounded-md border border-gray-200 p-3 lg:col-span-2">
            <p class="text-[11px] text-gray-500">Vendas Validadas</p>
            <div class="mt-1 flex items-baseline justify-between gap-2">
              <p class="text-sm font-semibold text-[#2f6f4f]">{{ asMoney(kpis.soma_valor_vendas_validadas) }}</p>
              <p class="text-[10px] text-gray-500">Qtd: {{ kpis.qtd_vendas_validadas || 0 }}</p>
            </div>
          </div>
          <div class="rounded-md border border-gray-200 p-3">
            <p class="text-[11px] text-gray-500">Negadas</p>
            <p class="text-sm font-semibold text-[#373435]">{{ kpis.vendas_negadas || 0 }}</p>
          </div>
          <div class="rounded-md border border-gray-200 p-3">
            <p class="text-[11px] text-gray-500">Pendentes de validação</p>
            <p class="text-lg font-semibold text-[#a82631]">{{ kpis.vendas_divergentes || 0 }}</p>
          </div>
        </div>

        <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <div class="rounded-md border border-gray-200 p-3">
            <p class="text-[11px] text-gray-500">Vendas Finalizadas (HOST)</p>
            <div class="mt-1 flex items-baseline justify-between gap-2">
              <p class="text-sm font-semibold text-[#373435]">{{ asMoney(kpis.soma_valor_stg) }}</p>
              <p class="text-[10px] text-gray-400">Canceladas: {{ asMoney(kpis.soma_valor_stg_canceladas) }}</p>
            </div>
          </div>
          <div class="rounded-md border border-gray-200 p-3">
            <p class="text-[11px] text-gray-500">Total Auditoria</p>
            <div class="mt-1 flex items-baseline justify-between gap-2">
              <p class="text-sm font-semibold text-[#373435]">{{ asMoney(kpis.soma_valor_auditoria) }}</p>
              <p class="text-[10px] text-gray-500">Qtd: {{ kpis.qtd_vendas_auditoria || 0 }}</p>
            </div>
          </div>
          <div class="rounded-md border border-gray-200 p-3">
            <p class="text-[11px] text-gray-500">Diferença Validadas x Auditoria</p>
            <p class="text-sm font-semibold" :class="Number(kpis.diferenca_total || 0) === 0 ? 'text-[#2f6f4f]' : 'text-[#a82631]'">{{ asMoney(kpis.diferenca_total) }}</p>
          </div>
          <div class="rounded-md border p-3 transition-colors" :class="periodosDivergem ? 'border-red-300 bg-red-50' : 'border-gray-200'">
            <p class="text-[11px]" :class="periodosDivergem ? 'text-red-500 font-semibold' : 'text-gray-500'">Período{{ periodosDivergem ? ' — divergente!' : '' }}</p>
            <div class="mt-1 space-y-0.5">
              <p class="text-xs font-semibold" :class="periodosDivergem ? 'text-red-700 animate-pulse' : 'text-[#373435]'">Host: {{ periodoHostTexto }}</p>
              <p class="text-xs font-semibold" :class="periodosDivergem ? 'text-red-700 animate-pulse' : 'text-[#373435]'">Audit: {{ periodoAuditoriaTexto }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Rotina do Dia -->
    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <button
        type="button"
        class="flex w-full items-center justify-between bg-gradient-to-r from-gray-50 to-white px-4 py-2.5 text-left"
        @click="mostrarRotina = !mostrarRotina"
      >
        <div class="flex items-center gap-2">
          <div class="flex h-5 w-5 items-center justify-center rounded-full bg-[#373435] shadow-sm">
            <Zap class="h-3 w-3 text-white" />
          </div>
          <span class="text-xs font-bold uppercase tracking-wider text-[#373435]">Rotina do dia</span>
          <span class="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-semibold text-[#373435]">5 passos</span>
        </div>
        <ChevronDown
          class="h-4 w-4 text-gray-400 transition-transform duration-200"
          :class="mostrarRotina ? 'rotate-180' : ''"
        />
      </button>

      <div v-if="mostrarRotina" class="border-t border-gray-200 px-4 py-3">
        <div class="flex items-center gap-2">
          <template v-for="(passo, idx) in PASSOS_ROTINA" :key="idx">
            <button
              type="button"
              class="group relative flex-1 rounded-xl border-2 p-3 text-left transition-all duration-200"
              :class="rotinaPasso === idx
                ? 'border-[#373435] bg-gradient-to-br from-[#373435] to-[#1a1618] shadow-lg shadow-gray-200'
                : 'border-gray-200 bg-white hover:border-gray-400 hover:shadow-sm'"
              @click="aplicarPassoRotina(idx)"
            >
              <div class="flex flex-col gap-1.5">
                <div class="flex items-center gap-1.5">
                  <span
                    class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold"
                    :class="rotinaPasso === idx ? 'bg-white/20 text-white' : 'bg-gray-100 text-[#373435]'"
                  >{{ idx + 1 }}</span>
                  <span
                    class="text-[10px] uppercase tracking-wide"
                    :class="rotinaPasso === idx ? 'text-gray-300' : 'text-gray-400'"
                  >{{ passo.categoria }}</span>
                </div>
                <p
                  class="text-sm font-bold leading-tight"
                  :class="rotinaPasso === idx ? 'text-white' : 'text-gray-800'"
                >{{ passo.sublabel }}</p>
              </div>
            </button>
            <ChevronRight
              v-if="idx < PASSOS_ROTINA.length - 1"
              class="h-4 w-4 shrink-0"
              :class="rotinaPasso !== null && rotinaPasso > idx ? 'text-[#373435]' : 'text-gray-200'"
            />
          </template>
        </div>

        <div v-if="rotinaPasso !== null" class="mt-3 space-y-2">
          <div class="flex items-center gap-2 rounded-lg bg-gray-50 px-3 py-2 border border-gray-200">
            <span class="h-1.5 w-1.5 animate-pulse rounded-full bg-[#373435]" />
            <p class="text-[11px] font-medium text-[#373435]">
              Passo {{ rotinaPasso + 1 }} ativo —
              <strong>{{ PASSOS_ROTINA[rotinaPasso].sublabel }}</strong>.
              Realize as ações necessárias na tabela abaixo.
            </p>
          </div>

          <div v-if="rotinaPasso < PASSOS_ROTINA.length - 1" class="flex items-center gap-2">
            <button
              type="button"
              class="inline-flex items-center gap-1.5 rounded-md bg-[#373435] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#1a1618] disabled:opacity-60"
              :disabled="macroRunning"
              @click="executarMacroRotina(rotinaPasso)"
            >
              <Loader2 v-if="macroRunning" class="h-3.5 w-3.5 animate-spin" />
              <Zap v-else class="h-3.5 w-3.5" />
              {{ macroRunning ? "Executando..." : "Executar macro" }}
            </button>
            <span
              v-if="(rotinaPasso === 0 && !macroFormaTransferenciaId) || (rotinaPasso === 1 && !macroFormaPixId)"
              class="text-[11px] text-amber-700"
            >
              Forma não configurada. Acesse Sistema → Painel para configurar.
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Filtros colapsáveis -->
    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <button
        type="button"
        class="flex w-full items-center justify-between bg-gradient-to-r from-gray-50 to-white px-4 py-2.5 text-left"
        @click="mostrarFiltros = !mostrarFiltros"
      >
        <div class="flex items-center gap-2">
          <div class="flex h-5 w-5 items-center justify-center rounded-full bg-[#373435] shadow-sm">
            <Filter class="h-3 w-3 text-white" />
          </div>
          <span class="text-xs font-bold uppercase tracking-wider text-[#373435]">Filtros</span>
          <span v-if="temFiltrosAtivos" class="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-semibold text-[#373435]">Ativos</span>
        </div>
        <ChevronDown
          class="h-4 w-4 text-gray-400 transition-transform duration-200"
          :class="mostrarFiltros ? 'rotate-180' : ''"
        />
      </button>

      <div v-if="mostrarFiltros" class="border-t border-gray-200 px-4 py-3 space-y-2">
        <!-- Linha 1: filtros categóricos -->
        <div class="flex flex-wrap items-center gap-2">
          <select v-model="filtroMotivo" class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs">
            <option value="">Todos os motivos</option>
            <option v-for="item in motivoOptions" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
          <select v-model="filtroStatusValidacao" class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs">
            <option value="">Todas as validações</option>
            <option value="PENDENTE">Pendente</option>
            <option value="NEGADO">Negado</option>
            <option value="APROVADO">Aprovado</option>
          </select>

          <select v-model="filtroTratamento" class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs">
            <option value="">Todos os tratamentos</option>
            <option value="PENDENTE">Pendente</option>
            <option value="AUTOMATICO">Automático</option>
            <option value="MANUAL">Manual</option>
          </select>

          <select v-model="filtroStatusVenda" class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs">
            <option value="">Todas as vendas</option>
            <option value="F">Finalizadas</option>
            <option value="C">Canceladas</option>
          </select>

          <select v-model="filtroTipoDocumento" class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs">
            <option value="">Todos os tipos</option>
            <option value="DAV">DAV</option>
            <option value="NFCE">NFCE</option>
          </select>

          <select v-model="filtroFormatoPagamentoVenda" class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs">
            <option value="">Todos formatos (venda)</option>
            <option v-for="forma in opcoesFiltroPagamento.formas_pagamento_venda" :key="forma" :value="forma">
              {{ forma }}
            </option>
          </select>

          <select v-model="filtroFormatoPagamentoAuditoria" class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs">
            <option value="">Todos formatos (auditoria)</option>
            <option v-for="forma in opcoesFiltroPagamento.formas_pagamento_auditoria" :key="forma" :value="forma">
              {{ forma }}
            </option>
          </select>

          <input
            v-model="filtroDataVenda"
            type="date"
            class="rounded-md border border-gray-200 px-2 py-1.5 text-xs"
          />
        </div>

        <!-- Linha 2: lookup (limpa outros filtros ao aplicar) + botões -->
        <div class="flex flex-wrap items-center gap-2">
          <input
            v-model="filtroIdLegado"
            type="text"
            placeholder="ID da venda (busca única)"
            class="rounded-md border border-gray-200 px-2 py-1.5 text-xs w-44"
            title="Ao filtrar por ID, todos os outros filtros são limpos"
          />

          <input
            v-model="filtroValorVenda"
            type="text"
            placeholder="Valor da venda (busca única)"
            class="rounded-md border border-gray-200 px-2 py-1.5 text-xs w-44"
            title="Ao filtrar por valor, todos os outros filtros são limpos"
          />

          <button
            type="button"
            class="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-black px-3 py-1.5 text-xs text-white hover:bg-gray-500"
            @click="aplicarFiltros"
          >
            <Filter class="h-3.5 w-3.5" />
            Filtrar
          </button>
          <button
            type="button"
            class="rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
            @click="limparFiltrosERecarregar"
          >
            Limpar filtros
          </button>
        </div>
      </div>
    </div>

    <BaseTable
      :columns="tableColumns"
      :rows="rows"
      row-key="row_key"
      :row-class="rowHighlightClass"
      :row-clickable="true"
      :selected-row-keys="selectedRows.map((row) => row.row_key)"
      :count="count"
      :next="next"
      :previous="previous"
      :loading="loading"
      :error="tableError"
      empty-text="Nenhuma divergencia encontrada."
      @row-click="toggleLinha"
      @next="goNext"
      @previous="goPrevious"
    >
      <template #header-extra>
        <div class="flex w-full items-center justify-between gap-3">
          <label class="inline-flex items-center gap-1 text-xs text-gray-700">
            <input :checked="allPaginaSelecionada" type="checkbox" @change="toggleSelecionarTodos($event.target.checked)" />
            Selecionar todos da página
          </label>
          <div class="flex flex-wrap justify-end gap-2">
            <button
              type="button"
              class="rounded-md bg-[#1f4f8a] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#193f6e] disabled:opacity-60"
              :disabled="!selectedRows.length || applyingBatch"
              @click="abrirModalEdicaoLote"
            >
              Editar Selecionados
            </button>
            <button
              type="button"
              class="rounded-md bg-[#a82631] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#901f29] disabled:opacity-60"
              :disabled="!selectedRows.length || applyingBatch"
              @click="abrirConfirmacao('negligenciar', 'lote')"
            >
              Negligenciar Selecionados
            </button>
            <button
              type="button"
              class="rounded-md bg-[#03ad12] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#029910] disabled:opacity-60"
              :disabled="!selectedRows.length || applyingBatch"
              @click="abrirConfirmacao('validar', 'lote')"
            >
              Validar Selecionados
            </button>
          </div>
        </div>
      </template>

      <template #cell-select="{ row }">
        <div class="flex items-center">
          <input
            :checked="selectedMap[row.row_key] || false"
            type="checkbox"
            @click.stop
            @change="toggleRow(row, $event.target.checked)"
          />
        </div>
      </template>

      <template #cell-venda="{ row }">
        <span class="font-semibold text-[#373435]">
          {{ row.venda }}
        </span>
      </template>

      <template #cell-status_venda="{ row }">
        <span
          class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold"
          :class="statusBadgeClass(row.status_venda)"
        >
          {{ row.status_venda || 'N/A' }}
        </span>
      </template>

      <template #cell-total_documento="{ row }">
        <span :class="financialDivergenciaClass(row, 'total_documento')">
          {{ asMoney(row.totais?.total_documento) }}
        </span>
      </template>

      <template #cell-total_itens="{ row }">
        <span class="relative inline-flex" :class="financialDivergenciaClass(row, 'total_itens')">
          {{ asMoney(row.totais?.total_itens) }}
          <span
            v-if="row.totais?.total_itens_via_fallback"
            class="absolute -right-1.5 -top-1.5 h-2 w-2 rounded-full bg-amber-500"
            title="Total de itens calculado com base em itens cancelados (nao havia itens ativos)."
            aria-label="Indicador de fallback no total de itens"
          />
        </span>
      </template>

      <template #cell-total_pagamentos="{ row }">
        <span :class="financialDivergenciaClass(row, 'total_pagamentos')">
          {{ asMoney(row.totais?.total_pagamentos) }}
        </span>
      </template>

      <template #cell-total_auditoria="{ row }">
        {{ asMoney(row.totais?.total_auditoria) }}
      </template>

      <template #cell-formato_venda="{ row }">
        <span :class="formatoVendaDivergenciaClass(row)">
          {{ (row.stg?.pagamentos || []).join('/') || 'N/A' }}
        </span>
      </template>

      <template #cell-formato_auditoria="{ row }">
        {{ (row.auditoria?.pagamentos || []).join('/') || 'N/A' }}
      </template>

      <template #cell-cliente="{ row }">
        <span :title="row.nome_cliente_legado || '-'">{{ formatCliente(row.nome_cliente_legado) }}</span>
      </template>

      <template #actions="{ row }">
        <button
          v-if="row.tipo_documento === 'NFCE' && row.importacao_origem === 'DAV' && row.status_validacao === 'PENDENTE'"
          type="button"
          class="rounded-md bg-purple-100 px-3 py-1.5 text-xs font-semibold text-purple-700 hover:bg-purple-600 hover:text-white"
          @click.stop="abrirResolucaoDavNfce(row)"
        >
          Resolver DAV/NFCE
        </button>
        <button type="button" class="rounded-md bg-[#fcfcfc] px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-[#373435] hover:text-white" @click="openEditModal(row)">
          Ajustar
        </button>
      </template>
    </BaseTable>

    <div v-if="(importSummary.erros_importacao || []).length > 0" class="space-y-1">
      <h4 class="text-xs font-semibold text-gray-700">Erros de importacao</h4>
      <ul class="max-h-44 overflow-auto rounded-md border border-red-100 bg-red-50 p-2 text-xs text-red-700 space-y-1">
        <li v-for="(item, idx) in importSummary.erros_importacao.slice(0, 30)" :key="`${item.arquivo}-${item.linha}-${idx}`">
          {{ item.arquivo }} (linha {{ item.linha }}): {{ item.motivo }}
        </li>
      </ul>
    </div>

    <div class="rounded-md border border-gray-200 p-3 space-y-2">
      <p class="text-xs font-semibold text-gray-700">Consolidacao para tabelas oficiais (SOT)</p>
      <p v-if="canConsolidar" class="text-xs text-gray-600">Tudo consistente. A consolidacao pode ser aprovada.</p>
      <ul v-else class="list-disc pl-4 text-xs text-red-600 space-y-0.5">
        <li v-for="motivo in consolidacaoBloqueios" :key="motivo">{{ motivo }}</li>
      </ul>
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-md bg-[#1f4f8a] px-3 py-2 text-xs font-semibold text-white hover:bg-[#193f6e] disabled:cursor-not-allowed disabled:opacity-70"
        :disabled="consolidating || !canConsolidar"
        @click="consolidarSot"
      >
        <Loader2 v-if="consolidating" class="h-4 w-4 animate-spin" />
        <span>{{ consolidating ? "Consolidando..." : "Aprovar e Inserir no SOT" }}</span>
      </button>

      <div v-if="consolidacaoResult" class="rounded-md border border-green-100 bg-green-50 p-2 text-xs text-green-800">
        <p>Vendas inseridas: {{ consolidacaoResult.vendas_inseridas || 0 }}</p>
        <p>Ignoradas (duplicadas): {{ consolidacaoResult.vendas_ignoradas_duplicadas || 0 }}</p>
        <p>Ignoradas (incompletas): {{ consolidacaoResult.vendas_ignoradas_incompletas || 0 }}</p>
      </div>
    </div>

    <p v-if="uploadError" class="text-xs text-red-600">{{ uploadError }}</p>

    <div
      v-if="lastBloqueioResumo"
      class="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900"
    >
      {{ lastBloqueioResumo }}
    </div>
  </article>

  <ModalAjusteVendaStg
    v-model="showEditModal"
    :row="activeRow"
    :saving="savingEdit"
    :formas-pagamento="formasPagamento"
    @save="saveEdit"
  />

  <ModalResolucaoDavNfce
    v-model="showResolucaoDavNfce"
    :nfce-id-legado="resolucaoDavNfceRow?.id_legado ?? null"
    @resolved="onResolvedDavNfce"
  />

  <BaseModal
    v-model="showEditLoteModal"
    title="Editar formato de pagamento em lote"
    description="Escolha a forma de pagamento destino para todas as vendas selecionadas nesta operacao."
  >
    <div class="space-y-2">
      <label class="text-xs font-semibold text-gray-700">Forma de pagamento destino</label>
      <select v-model="editLoteFormaId" class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm">
        <option value="">Selecione uma forma de pagamento</option>
        <option v-for="fp in formasPagamento" :key="fp.id_forma" :value="String(fp.id_forma)">
          {{ fp.descricao }}
        </option>
      </select>
    </div>

    <template #footer>
      <button
        type="button"
        class="rounded-md border border-gray-200 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
        :disabled="editLoteRunning"
        @click="showEditLoteModal = false"
      >
        Cancelar
      </button>
      <button
        type="button"
        class="rounded-md bg-[#1f4f8a] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#193f6e] disabled:opacity-60"
        :disabled="editLoteRunning || !editLoteFormaId"
        @click="confirmarEdicaoLote"
      >
        {{ editLoteRunning ? 'Salvando...' : 'Aplicar em lote' }}
      </button>
    </template>
  </BaseModal>

  <BaseModal
    v-model="showConfirmModal"
    title="Confirmar ação"
    :description="confirmDescription"
  >
    <template #footer>
      <button
        type="button"
        class="rounded-md border border-gray-200 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
        :disabled="confirmRunning"
        @click="showConfirmModal = false"
      >
        Cancelar
      </button>
      <button
        type="button"
        class="inline-flex items-center gap-1.5 rounded-md bg-[#050203] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#901f29] disabled:opacity-60"
        :disabled="confirmRunning"
        @click="confirmarAcao"
      >
        <Loader2 v-if="confirmRunning" class="h-3.5 w-3.5 animate-spin" />
        {{ confirmRunning ? 'Processando...' : 'Confirmar' }}
      </button>
    </template>
  </BaseModal>

  <BaseModal
    v-model="showBloqueioModal"
    title="Bloqueios identificados"
    :description="bloqueioModalDescricao"
  >
    <div class="space-y-3">
      <div class="rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900">
        {{ bloqueioModalMensagem }}
      </div>

      <div v-if="bloqueioResumoPorCodigo.length" class="flex flex-wrap gap-2">
        <span
          v-for="item in bloqueioResumoPorCodigo"
          :key="item.codigo"
          class="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-2 py-1 text-[11px] font-semibold text-amber-900"
        >
          {{ item.label }}: {{ item.total }}
        </span>
      </div>

      <div class="max-h-72 overflow-auto rounded-md border border-gray-200">
        <table class="min-w-full text-xs">
          <thead>
            <tr class="border-b border-gray-100 bg-gray-50 text-left text-[11px] uppercase tracking-wide text-gray-500">
              <th class="px-3 py-2">Venda</th>
              <th class="px-3 py-2">Codigos</th>
              <th class="px-3 py-2">Erros</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, idx) in bloqueioModalItems" :key="`${item.venda || 'SEM-VENDA'}-${idx}`" class="border-b border-gray-100 align-top">
              <td class="px-3 py-2 font-semibold text-[#373435]">{{ item.venda || '-' }}</td>
              <td class="px-3 py-2 text-gray-700">{{ formatarCodigosBloqueio(item.codigos) }}</td>
              <td class="px-3 py-2 text-gray-700">
                <ul class="list-disc pl-4 space-y-1">
                  <li v-for="(erro, eidx) in (item.erros || [])" :key="`${idx}-${eidx}`">{{ erro }}</li>
                </ul>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <template #footer>
      <button
        type="button"
        class="rounded-md border border-gray-200 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
        :disabled="bloqueioModalRunning"
        @click="cancelarBloqueioModal"
      >
        Cancelar
      </button>
      <button
        v-if="bloqueioModalPodeProsseguir"
        type="button"
        class="rounded-md bg-[#1f4f8a] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#193f6e] disabled:opacity-60"
        :disabled="bloqueioModalRunning"
        @click="prosseguirBloqueioModal"
      >
        {{ bloqueioModalRunning ? 'Processando...' : 'Prosseguir mesmo assim' }}
      </button>
    </template>
  </BaseModal>

  <BaseModal
    v-model="showNovaImportacaoModal"
    title="Nova importação"
    description="Isso apagará os dados temporários atuais de reconciliação (STG e auditoria). Deseja continuar?"
  >
    <template #footer>
      <button
        type="button"
        class="rounded-md border border-gray-200 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
        :disabled="resettingFluxo"
        @click="showNovaImportacaoModal = false"
      >
        Cancelar
      </button>
      <button
        type="button"
        class="rounded-md bg-[#a82631] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#901f29] disabled:opacity-60"
        :disabled="resettingFluxo"
        @click="confirmarNovaImportacao"
      >
        {{ resettingFluxo ? 'Limpando...' : 'Confirmar e Limpar' }}
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { BarChart2, ChevronDown, ChevronRight, Filter, Loader2, Zap } from "lucide-vue-next";
import BaseModal from "@/components/ui/BaseModal.vue";
import BaseTable from "@/components/ui/BaseTable.vue";
import ModalAjusteVendaStg from "@/pages/Validacao/ModalAjusteVendaStg.vue";
import ModalResolucaoDavNfce from "@/pages/Validacao/ModalResolucaoDavNfce.vue";
import { getApiBaseUrl } from "@/services/firebirdSync";
import { applyKpis, useSharedKpis } from "./composables/useSharedKpis";
import { notify } from "./composables/useToast";
import { useImportSummary } from "./composables/useImportSummary";
import { useBloqueioModal } from "./composables/useBloqueioModal";
import { useReconciliacaoFiltros } from "./composables/useReconciliacaoFiltros";
import { useSelecaoLinhas } from "./composables/useSelecaoLinhas";
import { motivoOptions, STATUS_VALIDACAO_NEGADO, MOTIVO_DUPLICADO_SOT, TABLE_COLUMNS } from "@/constants/reconciliacaoVendas";

const emit = defineEmits(["nova-importacao-confirmada"]);

const API_BASE_URL = getApiBaseUrl();

// --- Estado compartilhado (singletons) ---
const { kpis } = useSharedKpis();
const { importSummary } = useImportSummary();

// --- Composables de instância ---
const {
  showBloqueioModal,
  bloqueioModalRunning,
  bloqueioModalItems,
  bloqueioModalMensagem,
  bloqueioModalCodigo,
  bloqueioModalPodeProsseguir,
  bloqueioModalOrigem,
  bloqueioModalDescricao,
  bloqueioResumoPorCodigo,
  formatarCodigoBloqueio,
  formatarCodigosBloqueio,
  abrirBloqueioModal,
  cancelarBloqueioModal,
  prosseguirBloqueioModal: _prosseguirBloqueioModal,
} = useBloqueioModal();

const {
  filtroMotivo,
  filtroStatusValidacao,
  filtroTratamento,
  filtroStatusVenda,
  filtroIdLegado,
  filtroTipoDocumento,
  filtroImportacaoOrigem,
  filtroFormatoPagamentoVenda,
  filtroFormatoPagamentoAuditoria,
  filtroValorVenda,
  filtroDataVenda,
  buildUrl,
  limparFiltros,
} = useReconciliacaoFiltros();

// --- Estado da tabela ---
const rows = ref([]);
const loading = ref(false);
const tableError = ref("");
const count = ref(0);
const next = ref("");
const previous = ref("");

const { selectedMap, selectedRows, allPaginaSelecionada, clearSelection, toggleRow, toggleLinha, toggleSelecionarTodos } =
  useSelecaoLinhas(rows);

// --- Estado dos modais de gestão ---
const showEditModal = ref(false);
const savingEdit = ref(false);
const activeRow = ref(null);
const showEditLoteModal = ref(false);
const editLoteFormaId = ref("");
const editLoteRunning = ref(false);
const showConfirmModal = ref(false);
const confirmRunning = ref(false);
const confirmAction = ref("");
const confirmScope = ref("");
const confirmRow = ref(null);
const showNovaImportacaoModal = ref(false);
const resettingFluxo = ref(false);
const showResolucaoDavNfce = ref(false);
const resolucaoDavNfceRow = ref(null);

// --- Estado de lote, consolidação e pendências ---
const applyingBatch = ref(false);
const consolidating = ref(false);
const consolidacaoResult = ref(null);
const formasPagamento = ref([]);
const opcoesFiltroPagamento = reactive({ formas_pagamento_venda: [], formas_pagamento_auditoria: [] });
const uploadError = ref("");
const lastBloqueioResumo = ref("");

const pendenciasResumo = { produtos: 0, clientes: 0, fornecedores: 0 };
const resumoPendenciasDisponivel = ref(true);

const tableColumns = TABLE_COLUMNS;

// --- Estado das seções colapsáveis ---
const mostrarKpis = ref(true);
const mostrarFiltros = ref(false);

// --- Rotina do dia ---
const mostrarRotina = ref(true);
const rotinaPasso = ref(null);
const macroFormaTransferenciaId = ref(null);
const macroFormaPixId = ref(null);
const macroRunning = ref(false);
const PASSOS_ROTINA = [
  { categoria: "Auditoria", sublabel: "Transferência" },
  { categoria: "Auditoria", sublabel: "PIX" },
  { categoria: "Status venda", sublabel: "Canceladas" },
  { categoria: "DAV / NFCE", sublabel: "Resolver pares" },
  { categoria: "Pendentes", sublabel: "Check" },
];

// --- Computed ---
function formatDateShort(value) {
  const raw = String(value || "").trim();
  if (!raw) return "-";
  const parts = raw.slice(0, 10).split("-");
  if (parts.length === 3 && parts[0].length === 4) return `${parts[2]}/${parts[1]}`;
  return raw.slice(0, 5);
}

const periodoHostTexto = computed(() => {
  const ini = formatDateShort(kpis.periodo_data_inicial);
  const fin = formatDateShort(kpis.periodo_data_final);
  if (ini === "-" && fin === "-") return "-";
  if (ini === fin) return ini;
  return `${ini} - ${fin}`;
});

const periodoAuditoriaTexto = computed(() => {
  const ini = formatDateShort(kpis.periodo_auditoria_data_inicial);
  const fin = formatDateShort(kpis.periodo_auditoria_data_final);
  if (ini === "-" && fin === "-") return "-";
  if (ini === fin) return ini;
  return `${ini} - ${fin}`;
});

const periodosDivergem = computed(() => {
  const hostIni = kpis.periodo_data_inicial || "";
  const hostFin = kpis.periodo_data_final || "";
  const audIni = kpis.periodo_auditoria_data_inicial || "";
  const audFin = kpis.periodo_auditoria_data_final || "";
  if (!hostIni && !audIni) return false;
  return hostIni !== audIni || hostFin !== audFin;
});

const hasPendenciasCadastro = computed(
  () =>
    Number(pendenciasResumo.produtos || 0) > 0 ||
    Number(pendenciasResumo.clientes || 0) > 0 ||
    Number(pendenciasResumo.fornecedores || 0) > 0,
);

const consolidacaoBloqueios = computed(() => {
  const motivos = [];
  if (Number(kpis.vendas_aprovadas || 0) <= 0) motivos.push("Nao ha vendas aprovadas para consolidar.");
  if (Number(kpis.vendas_divergentes || 0) > 0) motivos.push(`Ainda existem ${kpis.vendas_divergentes} venda(s) pendentes de validacao. Trate todas antes de consolidar.`);
  if (!resumoPendenciasDisponivel.value) motivos.push("Nao foi possivel validar pendencias de cadastro no momento.");
  if (hasPendenciasCadastro.value) {
    motivos.push(
      `Existem pendencias de cadastro (produtos: ${pendenciasResumo.produtos}, clientes: ${pendenciasResumo.clientes}, fornecedores: ${pendenciasResumo.fornecedores}).`,
    );
  }
  return motivos;
});

const canConsolidar = computed(
  () =>
    Number(kpis.vendas_aprovadas || 0) > 0 &&
    Number(kpis.vendas_divergentes || 0) === 0 &&
    resumoPendenciasDisponivel.value &&
    !hasPendenciasCadastro.value,
);

const confirmDescription = computed(() => {
  if (confirmScope.value === "linha" && confirmRow.value) {
    const verbo = confirmAction.value === "validar" ? "validar" : "negligenciar";
    return `Deseja realmente ${verbo} a venda ${confirmRow.value.venda}?`;
  }
  const verbo = confirmAction.value === "validar" ? "validar" : "negligenciar";
  return `Deseja realmente ${verbo} ${selectedRows.value.length} venda(s) selecionada(s)?`;
});

const temFiltrosAtivos = computed(() =>
  !!(filtroMotivo.value || filtroStatusValidacao.value || filtroTratamento.value ||
    filtroStatusVenda.value || filtroTipoDocumento.value || filtroImportacaoOrigem.value ||
    filtroFormatoPagamentoVenda.value || filtroFormatoPagamentoAuditoria.value ||
    filtroDataVenda.value || filtroIdLegado.value || filtroValorVenda.value)
);

// --- Helpers de formatação ---
function asMoney(value) {
  return Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatDateBr(value) {
  const raw = String(value || "").trim();
  if (!raw) return "-";
  const iso = raw.slice(0, 10);
  const parts = iso.split("-");
  if (parts.length === 3 && parts[0].length === 4) return `${parts[2]}/${parts[1]}/${parts[0]}`;
  return raw;
}

function toNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function hasDifferentFinancialValue(row, vendaKey) {
  const totais = row?.totais || {};
  return Math.abs(toNumber(totais[vendaKey]) - toNumber(totais.total_auditoria)) > 0.0001;
}

function normalizePaymentList(values) {
  return (values || []).map((item) => String(item || "").trim().toUpperCase()).filter(Boolean).sort().join("|");
}

function hasDifferentPaymentFormat(row) {
  return normalizePaymentList(row?.stg?.pagamentos || []) !== normalizePaymentList(row?.auditoria?.pagamentos || []);
}

function divergenceBadgeClass(active) {
  return active ? "inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-900" : "";
}

function financialDivergenciaClass(row, vendaKey) {
  return divergenceBadgeClass(hasDifferentFinancialValue(row, vendaKey));
}

function formatoVendaDivergenciaClass(row) {
  return divergenceBadgeClass(hasDifferentPaymentFormat(row));
}

function formatCliente(value) {
  const text = String(value || "").trim();
  if (!text) return "-";
  return text.length > 10 ? `${text.slice(0, 10)}..` : text;
}

function motivosDaLinha(row) {
  return (row?.motivos || []).map((m) => String(m || "").trim().toLowerCase()).filter(Boolean);
}

function rowHighlightClass(row) {
  const statusValidacao = String(row?.status_validacao || "").trim().toUpperCase();
  if (statusValidacao === "APROVADO") return "bg-[#d7fce1]";
  if (statusValidacao === STATUS_VALIDACAO_NEGADO) return "bg-[#fff5f6]";
  if (motivosDaLinha(row).includes(MOTIVO_DUPLICADO_SOT)) return "bg-[#fff9db]";
  return "";
}

function statusBadgeClass(status) {
  const norm = String(status || "").toUpperCase();
  if (norm === "F") return "bg-green-100 text-green-800";
  if (norm === "C") return "bg-amber-100 text-amber-800";
  return "bg-gray-100 text-gray-700";
}

// --- Helpers de erro de API ---
const MENSAGENS_AMIGAVEIS_BLOQUEIO = {
  validacao_bloqueada_precheck: "Validacao bloqueada por inconsistencias estruturais.",
  consolidacao_bloqueada_divergencia_reconciliacao: "Consolidacao bloqueada por divergencias estruturais na reconciliacao.",
  consolidacao_bloqueada_precheck: "Consolidacao bloqueada por inconsistencias estruturais de pre-check.",
};

function parseApiErrorPayload(payload, statusCode) {
  const codigo = String(payload?.codigo || "").trim();
  const bloqueios = Array.isArray(payload?.bloqueios) ? payload.bloqueios : [];
  const mensagemOriginal = String(payload?.detail || `Erro ${statusCode}`).trim();
  const mensagemBase = MENSAGENS_AMIGAVEIS_BLOQUEIO[codigo] || mensagemOriginal;
  const codigosEncontrados = new Set(
    bloqueios.flatMap((item) => (item?.codigos || []).map((c) => String(c || "").trim()).filter(Boolean)),
  );
  const somenteFormato = codigosEncontrados.size === 1 && codigosEncontrados.has("divergencia_formato_pagamento");
  const permiteOverride = Boolean(payload?.permite_override);
  let mensagem = mensagemBase;
  if (somenteFormato && permiteOverride) {
    mensagem = `${mensagemBase} Foram encontradas divergencias somente de tipo de pagamento. Voce pode prosseguir agora ou cancelar para ajustar antes.`;
  } else if (somenteFormato) {
    mensagem = `${mensagemBase} Foram encontradas divergencias de tipo de pagamento que exigem ajuste previo.`;
  }
  return { message: mensagem, codigo, bloqueios, permiteOverride };
}

function resumirBloqueios(mensagem, bloqueios) {
  const total = Array.isArray(bloqueios) ? bloqueios.length : 0;
  if (!total) return mensagem || "Operacao bloqueada por inconsistencias.";
  return `${mensagem || "Operacao bloqueada."} (${total} venda(s) com restricao)`;
}

// Wrapper para prosseguirBloqueioModal que passa uploadError como callback
function prosseguirBloqueioModal() {
  _prosseguirBloqueioModal((msg) => { uploadError.value = msg; });
}

// --- Carregamento de dados ---
async function loadDivergencias(url = "") {
  loading.value = true;
  tableError.value = "";
  try {
    const response = await fetch(buildUrl(url));
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `Erro ${response.status}`);
    const result = payload.results || {};
    rows.value = (result.rows || []).map((row) => ({
      ...row,
      row_key: `${row.tipo_documento}-${row.id_legado}`,
      venda: row.venda || `${row.tipo_documento} #${String(row.id_legado).padStart(6, "0")}`,
    }));
    count.value = Number(payload.count || 0);
    next.value = payload.next || "";
    previous.value = payload.previous || "";
    applyKpis(result.kpis || {});
    clearSelection();
  } catch (err) {
    console.error(err);
    tableError.value = err?.message || "Falha ao carregar divergencias.";
  } finally {
    loading.value = false;
  }
}

function reloadDivergencias(resetPage = false) {
  return resetPage ? loadDivergencias("") : loadDivergencias();
}

function goNext() {
  if (next.value) loadDivergencias(next.value);
}

function goPrevious() {
  if (previous.value) loadDivergencias(previous.value);
}

function limparFiltrosERecarregar() {
  rotinaPasso.value = null;
  limparFiltros(() => reloadDivergencias(true));
}

function aplicarFiltros() {
  const idLegadoNorm = String(filtroIdLegado.value || "").trim();
  const valorVendaNorm = String(filtroValorVenda.value || "").trim();

  // Modo lookup: limpa todos os outros filtros, aplica apenas o campo de busca
  if (idLegadoNorm) {
    filtroMotivo.value = "";
    filtroStatusValidacao.value = "";
    filtroTratamento.value = "";
    filtroStatusVenda.value = "";
    filtroTipoDocumento.value = "";
    filtroImportacaoOrigem.value = "";
    filtroFormatoPagamentoVenda.value = "";
    filtroFormatoPagamentoAuditoria.value = "";
    filtroValorVenda.value = "";
    filtroDataVenda.value = "";
  } else if (valorVendaNorm) {
    filtroMotivo.value = "";
    filtroStatusValidacao.value = "";
    filtroTratamento.value = "";
    filtroStatusVenda.value = "";
    filtroTipoDocumento.value = "";
    filtroImportacaoOrigem.value = "";
    filtroFormatoPagamentoVenda.value = "";
    filtroFormatoPagamentoAuditoria.value = "";
    filtroIdLegado.value = "";
    filtroDataVenda.value = "";
  }

  reloadDivergencias(true);
}

function aplicarPassoRotina(index) {
  rotinaPasso.value = index;
  filtroMotivo.value = "";
  filtroStatusValidacao.value = "PENDENTE";
  filtroTratamento.value = "PENDENTE";
  filtroStatusVenda.value = "";
  filtroTipoDocumento.value = "";
  filtroImportacaoOrigem.value = "";
  filtroFormatoPagamentoVenda.value = "";
  filtroFormatoPagamentoAuditoria.value = "";
  filtroDataVenda.value = "";
  filtroIdLegado.value = "";
  filtroValorVenda.value = "";
  if (index === 0) filtroFormatoPagamentoAuditoria.value = "Transferencia";
  else if (index === 1) filtroFormatoPagamentoAuditoria.value = "PIX";
  else if (index === 2) filtroStatusVenda.value = "C";
  else if (index === 3) {
    filtroTipoDocumento.value = "NFCE";
    filtroImportacaoOrigem.value = "DAV";
    filtroTratamento.value = "";
  }
  mostrarFiltros.value = false;
  reloadDivergencias(true);
}

async function carregarConfigMacro() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/integracao/firebird-config`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) return;
    macroFormaTransferenciaId.value = payload.forma_macro_transferencia_id || null;
    macroFormaPixId.value = payload.forma_macro_pix_id || null;
  } catch (err) {
    console.error(err);
  }
}

async function executarMacroRotina(index) {
  const ROTINAS = ["transferencia", "pix", "canceladas", "dav_nfce"];
  const rotina = ROTINAS[index];
  if (!rotina) return;

  let idForma = null;
  if (index === 0) {
    if (!macroFormaTransferenciaId.value) {
      uploadError.value = "Configure a forma de pagamento para a Rotina Transferência em Sistema → Painel.";
      return;
    }
    idForma = macroFormaTransferenciaId.value;
  } else if (index === 1) {
    if (!macroFormaPixId.value) {
      uploadError.value = "Configure a forma de pagamento para a Rotina PIX em Sistema → Painel.";
      return;
    }
    idForma = macroFormaPixId.value;
  }

  macroRunning.value = true;
  try {
    const body = { rotina };
    if (idForma !== null) body.id_forma = idForma;

    const response = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/macro-rotina`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `Erro ${response.status}`);

    applyKpis(payload.kpis || {});
    await reloadDivergencias(false);
    notify(`Macro concluída: ${payload.processadas ?? 0} venda(s) processada(s).`);
  } catch (err) {
    console.error(err);
    uploadError.value = err?.message || "Falha ao executar macro.";
  } finally {
    macroRunning.value = false;
  }
}

async function carregarResumoPendencias() {  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/resumo`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `Erro ${response.status}`);
    pendenciasResumo.produtos = Number(payload.produtos || 0);
    pendenciasResumo.clientes = Number(payload.clientes || 0);
    pendenciasResumo.fornecedores = Number(payload.fornecedores || 0);
    resumoPendenciasDisponivel.value = true;
  } catch (err) {
    console.error(err);
    pendenciasResumo.produtos = 0;
    pendenciasResumo.clientes = 0;
    pendenciasResumo.fornecedores = 0;
    resumoPendenciasDisponivel.value = false;
  }
}

async function carregarFormasPagamento() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/formas-pagamento`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `Erro ${response.status}`);
    formasPagamento.value = payload.rows || [];
  } catch (err) {
    console.error(err);
    formasPagamento.value = [];
  }
}

async function carregarOpcoesFiltro() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/opcoes-filtro`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `Erro ${response.status}`);
    opcoesFiltroPagamento.formas_pagamento_venda = payload.formas_pagamento_venda || [];
    opcoesFiltroPagamento.formas_pagamento_auditoria = payload.formas_pagamento_auditoria || [];
  } catch (err) {
    console.error(err);
  }
}

// --- Tratamento de divergências ---
async function validarLinha(row, options = {}) {
  const forcarDivergenciaFormato = Boolean(options.forcarDivergenciaFormato);
  const response = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/divergencias/tratar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tipo_documento: row.tipo_documento,
      id_legado: row.id_legado,
      acao: "validar",
      payload: { forcar_divergencia_formato: forcarDivergenciaFormato },
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const erroApi = parseApiErrorPayload(payload, response.status);
    lastBloqueioResumo.value = resumirBloqueios(erroApi.message, erroApi.bloqueios);
    if (erroApi.bloqueios.length && !forcarDivergenciaFormato) {
      abrirBloqueioModal({
        origem: "validar_linha",
        mensagem: erroApi.message,
        codigo: erroApi.codigo,
        bloqueios: erroApi.bloqueios,
        permiteOverride: erroApi.permiteOverride,
        onConfirm: erroApi.permiteOverride
          ? async () => { await validarLinha(row, { forcarDivergenciaFormato: true }); }
          : null,
      });
      return false;
    }
    throw new Error(erroApi.message);
  }
  lastBloqueioResumo.value = "";
  applyKpis(payload.kpis || {});
  await reloadDivergencias(false);
  notify("Venda validada com sucesso.");
  return true;
}

async function negligenciarLinha(row) {
  const response = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/divergencias/tratar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tipo_documento: row.tipo_documento, id_legado: row.id_legado, acao: "negligenciar", payload: {} }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `Erro ${response.status}`);
  applyKpis(payload.kpis || {});
  await reloadDivergencias(false);
  notify("Venda negligenciada com sucesso.");
  return true;
}

function abrirConfirmacao(acao, escopo, row = null) {
  if (escopo === "lote" && selectedRows.value.length === 0) return;
  confirmAction.value = acao;
  confirmScope.value = escopo;
  confirmRow.value = row;
  showConfirmModal.value = true;
}

async function confirmarAcao() {
  confirmRunning.value = true;
  try {
    let sucesso = false;
    if (confirmScope.value === "linha" && confirmRow.value) {
      sucesso = confirmAction.value === "validar"
        ? await validarLinha(confirmRow.value)
        : await negligenciarLinha(confirmRow.value);
    } else if (confirmScope.value === "lote") {
      sucesso = confirmAction.value === "validar"
        ? await validarSelecionados()
        : await negligenciarSelecionados();
    }
    if (sucesso || showBloqueioModal.value) showConfirmModal.value = false;
  } catch (err) {
    console.error(err);
    uploadError.value = err?.message || "Falha ao aplicar acao em lote.";
    showConfirmModal.value = false;
  } finally {
    confirmRunning.value = false;
  }
}

// --- Modal de ajuste individual ---
function openEditModal(row) {
  activeRow.value = row;
  showEditModal.value = true;
}

// --- Modal Resolver DAV/NFCE ---
function abrirResolucaoDavNfce(row) {
  resolucaoDavNfceRow.value = row;
  showResolucaoDavNfce.value = true;
}

function onResolvedDavNfce(payload) {
  applyKpis(payload.kpis || {});
  reloadDivergencias(false);
  notify("Par DAV/NFCE resolvido com sucesso.");
}

async function saveEdit(payload) {
  if (!activeRow.value) return;
  savingEdit.value = true;
  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/divergencias/tratar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tipo_documento: activeRow.value.tipo_documento,
        id_legado: activeRow.value.id_legado,
        acao: "ajustar",
        payload,
      }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || `Erro ${response.status}`);
    applyKpis(result.kpis || {});
    showEditModal.value = false;
    await reloadDivergencias(false);
    notify("Ajustes aplicados com sucesso.");
  } catch (err) {
    console.error(err);
    uploadError.value = err?.message || "Falha ao salvar ajustes da venda.";
  } finally {
    savingEdit.value = false;
  }
}

// --- Operações em lote ---
async function aplicarLote(acao, payload = {}, options = {}) {
  const vendasSelecionadas = Array.isArray(options.vendasOverride) && options.vendasOverride.length
    ? options.vendasOverride
    : selectedRows.value.map((row) => ({ tipo_documento: row.tipo_documento, id_legado: row.id_legado }));
  if (!vendasSelecionadas.length) return false;
  applyingBatch.value = true;
  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/divergencias/tratar-lote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ acao, payload, vendas: vendasSelecionadas }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      const erroApi = parseApiErrorPayload(result, response.status);
      lastBloqueioResumo.value = resumirBloqueios(erroApi.message, erroApi.bloqueios);
      throw new Error(erroApi.message);
    }
    const bloqueios = Array.isArray(result.bloqueios) ? result.bloqueios : [];
    const totalBloqueadas = Number(result.bloqueadas || 0);
    if (acao === "validar" && totalBloqueadas > 0 && bloqueios.length) {
      const podeOverride = bloqueios.every((item) => Boolean(item?.permite_override));
      const vendasBloqueadas = bloqueios
        .filter((item) => item?.tipo_documento && item?.id_legado !== null && item?.id_legado !== undefined)
        .map((item) => ({ tipo_documento: item.tipo_documento, id_legado: item.id_legado }));
      const mensagemBloqueio = `Validacao em lote bloqueou ${totalBloqueadas} venda(s).`;
      lastBloqueioResumo.value = mensagemBloqueio;
      abrirBloqueioModal({
        origem: "validar_lote",
        mensagem: mensagemBloqueio,
        codigo: "validacao_lote_bloqueada",
        bloqueios,
        permiteOverride: podeOverride,
        onConfirm: podeOverride
          ? async () => {
              await aplicarLote("validar", { ...payload, forcar_divergencia_formato: true }, { vendasOverride: vendasBloqueadas });
            }
          : null,
      });
    } else {
      lastBloqueioResumo.value = "";
    }
    applyKpis(result.kpis || {});
    await reloadDivergencias(false);
    notify(result.detail || "Processamento em lote concluido.");
    return true;
  } finally {
    applyingBatch.value = false;
  }
}

function validarSelecionados() { return aplicarLote("validar"); }
function negligenciarSelecionados() { return aplicarLote("negligenciar"); }

function abrirModalEdicaoLote() {
  if (!selectedRows.value.length) return;
  editLoteFormaId.value = "";
  showEditLoteModal.value = true;
}

async function confirmarEdicaoLote() {
  if (!editLoteFormaId.value) return;
  editLoteRunning.value = true;
  try {
    const sucesso = await aplicarLote("editar_pagamento", { id_forma: Number(editLoteFormaId.value) });
    if (sucesso) showEditLoteModal.value = false;
  } catch (err) {
    console.error(err);
    uploadError.value = err?.message || "Falha ao editar pagamentos em lote.";
  } finally {
    editLoteRunning.value = false;
  }
}

// --- Consolidação SOT ---
async function consolidarSot() {
  await carregarResumoPendencias();
  if (!canConsolidar.value) {
    uploadError.value = "Consolidacao bloqueada. Verifique os motivos exibidos no painel.";
    return;
  }

  async function executarConsolidacao(overrideFormato = false) {
    const response = await fetch(`${API_BASE_URL}/api/validacao/consolidar-vendas-sot`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ forcar_divergencia_formato: Boolean(overrideFormato) }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const erroApi = parseApiErrorPayload(payload, response.status);
      lastBloqueioResumo.value = resumirBloqueios(erroApi.message, erroApi.bloqueios);
      if (erroApi.bloqueios.length && !overrideFormato) {
        abrirBloqueioModal({
          origem: "consolidar",
          mensagem: erroApi.message,
          codigo: erroApi.codigo,
          bloqueios: erroApi.bloqueios,
          permiteOverride: erroApi.permiteOverride,
          onConfirm: erroApi.permiteOverride ? async () => { await executarConsolidacao(true); } : null,
        });
        return false;
      }
      throw new Error(erroApi.message);
    }
    lastBloqueioResumo.value = "";
    consolidacaoResult.value = payload?.resultado || null;
    notify("Consolidacao STG -> SOT concluida.");
    return true;
  }

  consolidating.value = true;
  try {
    await executarConsolidacao(false);
  } catch (err) {
    console.error(err);
    uploadError.value = err?.message || "Falha ao consolidar vendas no SOT.";
  } finally {
    consolidating.value = false;
  }
}

// --- Nova importação ---
function abrirConfirmacaoNovaImportacao() {
  showNovaImportacaoModal.value = true;
}

async function confirmarNovaImportacao() {
  resettingFluxo.value = true;
  uploadError.value = "";
  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/limpar-fluxo`, { method: "POST" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `Erro ${response.status}`);
    showNovaImportacaoModal.value = false;
    notify("Fluxo anterior removido. Você pode iniciar uma nova importação.");
    // Coordenador chama resetKpis() → este painel desmonta automaticamente
    emit("nova-importacao-confirmada");
  } catch (err) {
    console.error(err);
    uploadError.value = err?.message || "Falha ao reiniciar fluxo de importação.";
  } finally {
    resettingFluxo.value = false;
  }
}

// --- Inicialização ---
onMounted(async () => {
  await Promise.all([reloadDivergencias(true), carregarFormasPagamento(), carregarOpcoesFiltro(), carregarResumoPendencias(), carregarConfigMacro()]);
});
</script>
