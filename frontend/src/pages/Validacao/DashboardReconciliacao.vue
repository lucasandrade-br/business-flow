<template>
  <section class="space-y-4">
    <article v-if="!hasValidationResult" class="rounded-md border border-gray-200 bg-white p-4">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 class="text-sm font-semibold text-[#373435]">Hub de Reconciliação Financeira</h2>
          <p class="mt-1 text-xs text-gray-500">Integração isolada para ingestão legado de vendas NFCe e DAV no staging.</p>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-md bg-[#a82631] px-3 py-2 text-xs font-semibold text-white hover:bg-[#901f29] disabled:cursor-not-allowed disabled:opacity-70"
          :disabled="submitting"
          @click="openModal"
        >
          <RefreshCw class="h-4 w-4" />
          Sincronizar Vendas (Legado)
        </button>
      </div>
    </article>

    <article v-if="!hasValidationResult" class="rounded-md border border-gray-200 bg-white p-4 space-y-3">
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 class="text-sm font-semibold text-[#373435]">Ingestão de Auditoria (Excel)</h3>
          <p class="mt-1 text-xs text-gray-500">Selecione uma pasta ou vários arquivos .xlsx/.xlsm da aba HostVenda para importar e validar.</p>
        </div>

        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-md bg-[#2f6f4f] px-3 py-2 text-xs font-semibold text-white hover:bg-[#275d43] disabled:cursor-not-allowed disabled:opacity-70"
          :disabled="uploading || selectedFiles.length === 0"
          @click="importAuditoria"
        >
          <Loader2 v-if="uploading" class="h-4 w-4 animate-spin" />
          <Upload v-else class="h-4 w-4" />
          {{ uploading ? "Importando..." : "Importar e Validar" }}
        </button>
      </div>

      <div class="flex flex-col gap-2 sm:flex-row">
        <label class="inline-flex cursor-pointer items-center justify-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50">
          <Folder class="h-4 w-4" />
          Selecionar Pasta
          <input ref="folderInputRef" type="file" class="hidden" webkitdirectory directory multiple @change="onFolderSelected" />
        </label>

        <label class="inline-flex cursor-pointer items-center justify-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50">
          <FileSpreadsheet class="h-4 w-4" />
          Selecionar Arquivos
          <input ref="filesInputRef" type="file" class="hidden" multiple accept=".xlsx,.xlsm" @change="onFilesSelected" />
        </label>

        <button
          type="button"
          class="rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-60"
          :disabled="uploading || selectedFiles.length === 0"
          @click="clearSelectedFiles"
        >
          Limpar Seleção
        </button>
      </div>

      <div class="rounded-md border border-gray-100 bg-gray-50 p-3 text-xs text-gray-600">
        <p><strong>Arquivos prontos para importação:</strong> {{ selectedFiles.length }}</p>
      </div>

      <div v-if="importJob" class="rounded-md border border-blue-100 bg-blue-50 p-3 text-xs text-blue-900">
        <p><strong>Status:</strong> {{ importJob.status }} - {{ importJob.stage }}</p>
        <p class="mt-1">{{ importJob.detail }}</p>
      </div>

      <p v-if="uploadError" class="text-xs text-red-600">{{ uploadError }}</p>

      <div
        v-if="lastBloqueioResumo"
        class="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900"
      >
        {{ lastBloqueioResumo }}
      </div>
    </article>

    <article v-if="hasValidationResult" class="rounded-md border border-gray-200 bg-white p-4 space-y-3">
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h3 class="text-xs font-semibold uppercase tracking-wide text-gray-500">Resumo da Importação e Validação</h3>
        <button type="button" class="rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50" @click="abrirConfirmacaoNovaImportacao">
          Nova importação
        </button>
      </div>

      <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Negligenciadas</p>
          <p class="text-sm font-semibold text-[#373435]">{{ kpis.vendas_negligenciadas || 0 }}</p>
        </div>
        
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Vendas divergentes</p>
          <p class="text-lg font-semibold text-[#a82631]">{{ kpis.vendas_divergentes || 0 }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-3 lg:col-span-2">
          <p class="text-[11px] text-gray-500">Vendas Validadas (Finalizadas)</p>
          <div class="mt-1 flex items-baseline justify-between gap-2">
            <p class="text-sm font-semibold text-[#2f6f4f]">{{ asMoney(kpis.soma_valor_vendas_validadas) }}</p>
            <p class="text-[10px] text-gray-500">Qtd: {{ kpis.qtd_vendas_validadas || 0 }}</p>
          </div>
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
          <p class="text-[11px] text-gray-500">Diferenca Validadas x Auditoria</p>
          <p class="text-sm font-semibold" :class="Number(kpis.diferenca_total || 0) === 0 ? 'text-[#2f6f4f]' : 'text-[#a82631]'">{{ asMoney(kpis.diferenca_total) }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Periodo</p>
          <p class="text-sm font-semibold text-[#373435]">{{ periodoKpiTexto }}</p>
        </div>
      </div>

      <div class="flex flex-col gap-2 rounded-md border border-gray-200 bg-white p-3 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center gap-2">
          <label class="text-xs text-gray-700">Filtro:</label>
          <select v-model="activeFiltro" class="rounded-md border border-gray-200 px-2 py-1 text-xs" @change="reloadDivergencias(true)">
            <option value="todos">Todas divergências</option>
            <option value="divergencia_totais">Divergência de totais</option>
            <option value="divergencia_formato">Divergência de formato</option>
            <option value="duplicado_sot">Duplicado no SOT</option>
            <option value="status_f">Somente finalizados</option>
            <option value="status_c">Somente cancelados</option>
          </select>
          <label class="inline-flex items-center gap-1 text-xs text-gray-700">
            <input v-model="somentePendentes" type="checkbox" @change="reloadDivergencias(true)" />
            Somente pendentes
          </label>
        </div>

        <div class="flex gap-2">
          <button
            type="button"
            class="rounded-md border border-[#03ad12] px-3 py-1.5 text-xs text-[#03ad12] hover:bg-[#d7fce1] disabled:opacity-60"
            :disabled="!selectedRows.length || applyingBatch"
            @click="abrirConfirmacao('validar', 'lote')"
          >
            Validar Selecionados
          </button>
          <button
            type="button"
            class="rounded-md border border-[#a82631] px-3 py-1.5 text-xs text-[#a82631] hover:bg-[#fff5f6] disabled:opacity-60"
            :disabled="!selectedRows.length || applyingBatch"
            @click="abrirConfirmacao('negligenciar', 'lote')"
          >
            Negligenciar Selecionados
          </button>
          <button
            type="button"
            class="rounded-md border border-[#1f4f8a] px-3 py-1.5 text-xs text-[#1f4f8a] hover:bg-[#eef4fb] disabled:opacity-60"
            :disabled="!selectedRows.length || applyingBatch"
            @click="abrirModalEdicaoLote"
          >
            Editar Selecionados
          </button>
        </div>
      </div>

      <BaseTable
        :columns="tableColumns"
        :rows="rows"
        row-key="row_key"
        :row-class="rowHighlightClass"
        :selected-row-keys="selectedRows.map((row) => row.row_key)"
        :count="count"
        :next="next"
        :previous="previous"
        :loading="loading"
        :error="tableError"
        empty-text="Nenhuma divergencia encontrada."
        @next="goNext"
        @previous="goPrevious"
      >
        <template #header-extra>
          <label class="inline-flex items-center gap-1 text-xs text-gray-700">
            <input :checked="allPaginaSelecionada" type="checkbox" @change="toggleSelecionarTodos($event.target.checked)" />
            Selecionar todos da página
          </label>
        </template>

        <template #cell-select="{ row }">
          <div class="flex cursor-pointer items-center" @click="toggleLinha(row)">
            <input
              :checked="selectedMap[row.row_key] || false"
              type="checkbox"
              @click.stop
              @change="toggleRow(row, $event.target.checked)"
            />
          </div>
        </template>

        <template #cell-venda="{ row }">
          <button type="button" class="font-semibold text-[#373435] hover:underline" @click="toggleLinha(row)">
            {{ row.venda }}
          </button>
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
          <button type="button" class="rounded-md border border-gray-200 px-3 py-1.5 text-xs text-[#373435] hover:bg-gray-50" @click="openEditModal(row)">
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

    <BaseModal
      v-model="showModal"
      title="Sincronizar Vendas Legado"
      description="Informe o intervalo de datas para extracao em 3 blocos (cabecalho, itens e pagamentos)."
    >
      <div class="grid gap-3 sm:grid-cols-2">
        <BaseInput v-model="form.data_inicial" type="date" label="Data inicial" required />
        <BaseInput v-model="form.data_final" type="date" label="Data final" required />
      </div>

      <p v-if="error" class="mt-3 text-xs text-red-600">{{ error }}</p>

      <template #footer>
        <button
          type="button"
          class="rounded-md border border-gray-200 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-60"
          :disabled="submitting"
          @click="showModal = false"
        >
          Cancelar
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-md bg-[#a82631] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#901f29] disabled:cursor-not-allowed disabled:opacity-70"
          :disabled="submitting"
          @click="submit"
        >
          <Loader2 v-if="submitting" class="h-3.5 w-3.5 animate-spin" />
          <RefreshCw v-else class="h-3.5 w-3.5" />
          {{ submitting ? "Sincronizando..." : "Executar sincronizacao" }}
        </button>
      </template>
    </BaseModal>

    <ModalAjusteVendaStg
      v-model="showEditModal"
      :row="activeRow"
      :saving="savingEdit"
      :formas-pagamento="formasPagamento"
      @save="saveEdit"
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
      title="Confirmar acao"
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
          class="rounded-md bg-[#a82631] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#901f29] disabled:opacity-60"
          :disabled="confirmRunning"
          @click="confirmarAcao"
        >
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

        <div
          v-if="bloqueioResumoPorCodigo.length"
          class="flex flex-wrap gap-2"
        >
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

    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="translate-y-2 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="translate-y-2 opacity-0"
    >
      <div v-if="toast" class="fixed bottom-5 right-5 z-50 rounded-md border border-gray-200 bg-white px-4 py-3 text-xs text-[#373435]">
        {{ toast }}
      </div>
    </transition>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { FileSpreadsheet, Folder, Loader2, RefreshCw, Upload } from "lucide-vue-next";
import BaseInput from "@/components/ui/BaseInput.vue";
import BaseModal from "@/components/ui/BaseModal.vue";
import BaseTable from "@/components/ui/BaseTable.vue";
import ModalAjusteVendaStg from "@/pages/Validacao/ModalAjusteVendaStg.vue";
import { executarSincronizacaoFirebird, formatarErroSincronizacao, getApiBaseUrl } from "@/services/firebirdSync";

const API_BASE_URL = getApiBaseUrl();
const STATUS_TRATAMENTO_VALIDADO = "VALIDADO";
const STATUS_TRATAMENTO_NEGLIGENCIADO = "NEGLIGENCIADO";
const MOTIVO_DUPLICADO_SOT = "duplicado_sot";

const LABELS_CODIGO_BLOQUEIO = {
  divergencia_formato_pagamento: "Divergencia de formato de pagamento",
  venda_sem_itens_ou_pagamentos: "Venda sem itens ou pagamentos",
  pagamento_sem_id_forma_origem: "Pagamento sem forma de origem",
  forma_origem_nao_cadastrada: "Forma de origem nao cadastrada",
  mapeamento_forma_ausente: "Mapeamento de forma ausente",
  cliente_nao_encontrado: "Cliente nao encontrado",
  cliente_nome_divergente: "Nome de cliente divergente",
  cliente_legado_zero_sem_cliente_padrao_configurado: "Cliente padrao nao configurado",
  usuario_legado_ausente: "Usuario legado ausente",
  usuario_legado_nao_encontrado: "Usuario legado nao encontrado",
  usuario_nome_divergente: "Nome de usuario divergente",
  item_sem_id_produto: "Item sem produto",
  produto_nao_encontrado: "Produto nao encontrado",
  produto_nome_divergente: "Nome de produto divergente",
  unidade_legado_sem_mapeamento: "Unidade sem mapeamento",
  consolidacao_bloqueada_divergencia_reconciliacao: "Divergencia estrutural na reconciliacao",
  consolidacao_bloqueada_precheck: "Inconsistencias estruturais de pre-check",
  validacao_bloqueada_precheck: "Inconsistencias estruturais de validacao",
};

const MENSAGENS_AMIGAVEIS_BLOQUEIO = {
  validacao_bloqueada_precheck: "Validacao bloqueada por inconsistencias estruturais.",
  consolidacao_bloqueada_divergencia_reconciliacao: "Consolidacao bloqueada por divergencias estruturais na reconciliacao.",
  consolidacao_bloqueada_precheck: "Consolidacao bloqueada por inconsistencias estruturais de pre-check.",
};

const showModal = ref(false);
const submitting = ref(false);
const error = ref("");
const toast = ref("");
const selectedFiles = ref([]);
const uploadError = ref("");
const uploading = ref(false);
const importJob = ref(null);
const importJobId = ref("");
const pollingId = ref(null);
const folderInputRef = ref(null);
const filesInputRef = ref(null);
const consolidating = ref(false);
const consolidacaoResult = ref(null);

const showEditModal = ref(false);
const savingEdit = ref(false);
const activeRow = ref(null);

const importSummary = reactive({
  arquivos_recebidos: 0,
  linhas_importadas: 0,
  erros_importacao: [],
});

const pendenciasResumo = reactive({
  produtos: 0,
  clientes: 0,
  fornecedores: 0,
});
const resumoPendenciasDisponivel = ref(true);

const kpis = reactive({
  total_vendas_stg: 0,
  vendas_aprovadas: 0,
  vendas_divergentes: 0,
  vendas_duplicadas_sot: 0,
  vendas_negligenciadas: 0,
  soma_valor_stg: "0",
  soma_valor_stg_canceladas: "0",
  soma_valor_vendas_validadas: "0",
  qtd_vendas_validadas: 0,
  soma_valor_auditoria: "0",
  qtd_vendas_auditoria: 0,
  diferenca_total: "0",
  motivos_divergencia: {},
  periodo_data_inicial: null,
  periodo_data_final: null,
});

const rows = ref([]);
const loading = ref(false);
const tableError = ref("");
const count = ref(0);
const next = ref("");
const previous = ref("");
const activeFiltro = ref("todos");
const somentePendentes = ref(true);
const applyingBatch = ref(false);
const showConfirmModal = ref(false);
const confirmRunning = ref(false);
const confirmAction = ref("");
const confirmScope = ref("");
const confirmRow = ref(null);
const showNovaImportacaoModal = ref(false);
const resettingFluxo = ref(false);
const formasPagamento = ref([]);
const showEditLoteModal = ref(false);
const editLoteFormaId = ref("");
const editLoteRunning = ref(false);
const showBloqueioModal = ref(false);
const bloqueioModalRunning = ref(false);
const bloqueioModalItems = ref([]);
const bloqueioModalMensagem = ref("");
const bloqueioModalCodigo = ref("");
const bloqueioModalPodeProsseguir = ref(false);
const bloqueioModalOrigem = ref("");
const lastBloqueioResumo = ref("");
const bloqueioModalConfirmAction = ref(null);

const selectedMap = reactive({});

const form = reactive({
  data_inicial: "",
  data_final: "",
});

const tableColumns = [
  { key: "select", label: "Sel" },
  { key: "venda", label: "Venda" },
  { key: "status_venda", label: "Status" },
  { key: "total_documento", label: "Total Doc." },
  { key: "total_itens", label: "Total Ite." },
  { key: "total_pagamentos", label: "Total Pag." },
  { key: "total_auditoria", label: "Total Aud." },
  { key: "formato_venda", label: "Form. Venda" },
  { key: "formato_auditoria", label: "Form. Aud." },
  { key: "cliente", label: "Cliente" },
];

const hasValidationResult = computed(() => Number(kpis.total_vendas_stg || 0) > 0);
const hasPendenciasCadastro = computed(() => (
  Number(pendenciasResumo.produtos || 0) > 0
  || Number(pendenciasResumo.clientes || 0) > 0
  || Number(pendenciasResumo.fornecedores || 0) > 0
));
const consolidacaoBloqueios = computed(() => {
  const motivos = [];
  if (Number(kpis.vendas_aprovadas || 0) <= 0) {
    motivos.push("Nao ha vendas aprovadas para consolidar.");
  }
  if (!resumoPendenciasDisponivel.value) {
    motivos.push("Nao foi possivel validar pendencias de cadastro no momento.");
  }
  if (hasPendenciasCadastro.value) {
    motivos.push(
      `Existem pendencias de cadastro (produtos: ${pendenciasResumo.produtos}, clientes: ${pendenciasResumo.clientes}, fornecedores: ${pendenciasResumo.fornecedores}).`,
    );
  }
  return motivos;
});
const canConsolidar = computed(() => (
  Number(kpis.vendas_aprovadas || 0) > 0
  && resumoPendenciasDisponivel.value
  && !hasPendenciasCadastro.value
));
const selectedRows = computed(() => rows.value.filter((row) => selectedMap[row.row_key]));
const allPaginaSelecionada = computed(() => rows.value.length > 0 && selectedRows.value.length === rows.value.length);
const confirmDescription = computed(() => {
  if (confirmScope.value === "linha" && confirmRow.value) {
    const verbo = confirmAction.value === "validar" ? "validar" : "negligenciar";
    return `Deseja realmente ${verbo} a venda ${confirmRow.value.venda}?`;
  }
  const verbo = confirmAction.value === "validar" ? "validar" : "negligenciar";
  return `Deseja realmente ${verbo} ${selectedRows.value.length} venda(s) selecionada(s)?`;
});
const bloqueioModalDescricao = computed(() => {
  if (bloqueioModalOrigem.value === "validar_lote") {
    return "As vendas abaixo foram bloqueadas durante a validacao em lote.";
  }
  if (bloqueioModalOrigem.value === "validar_linha") {
    return "A venda selecionada foi bloqueada para validacao.";
  }
  if (bloqueioModalOrigem.value === "consolidar") {
    return "A consolidacao encontrou vendas bloqueadas.";
  }
  return "Foram identificados bloqueios durante a operacao.";
});
const bloqueioResumoPorCodigo = computed(() => {
  const acumulado = new Map();
  for (const item of bloqueioModalItems.value || []) {
    const codigosUnicos = new Set((item?.codigos || []).map((codigo) => String(codigo || "").trim()).filter(Boolean));
    for (const codigo of codigosUnicos) {
      acumulado.set(codigo, Number(acumulado.get(codigo) || 0) + 1);
    }
  }

  return Array.from(acumulado.entries())
    .map(([codigo, total]) => ({
      codigo,
      total,
      label: formatarCodigoBloqueio(codigo),
    }))
    .sort((a, b) => b.total - a.total || a.label.localeCompare(b.label));
});

function asMoney(value) {
  const numeric = Number(value || 0);
  return numeric.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function formatDateBr(value) {
  const raw = String(value || "").trim();
  if (!raw) return "-";

  const iso = raw.slice(0, 10);
  const parts = iso.split("-");
  if (parts.length === 3 && parts[0].length === 4) {
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }

  return raw;
}

const periodoKpiTexto = computed(() => {
  const inicial = formatDateBr(kpis.periodo_data_inicial);
  const final = formatDateBr(kpis.periodo_data_final);

  if (inicial === "-" && final === "-") return "-";
  if (inicial === "-") return final;
  if (final === "-") return inicial;
  return `${inicial} até ${final}`;
});

function toNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function hasDifferentFinancialValue(row, vendaKey) {
  const totais = row?.totais || {};
  const vendaValor = toNumber(totais[vendaKey]);
  const auditoriaValor = toNumber(totais.total_auditoria);
  return Math.abs(vendaValor - auditoriaValor) > 0.0001;
}

function normalizePaymentList(values) {
  return (values || [])
    .map((item) => String(item || "").trim().toUpperCase())
    .filter(Boolean)
    .sort()
    .join("|");
}

function hasDifferentPaymentFormat(row) {
  const formatoVenda = normalizePaymentList(row?.stg?.pagamentos || []);
  const formatoAuditoria = normalizePaymentList(row?.auditoria?.pagamentos || []);
  return formatoVenda !== formatoAuditoria;
}

function divergenceBadgeClass(active) {
  if (!active) return "";
  return "inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-900";
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
  return (row?.motivos || []).map((motivo) => String(motivo || "").trim().toLowerCase()).filter(Boolean);
}

function rowHighlightClass(row) {
  const tratamento = String(row?.tratamento || "").trim().toUpperCase();
  if (tratamento === STATUS_TRATAMENTO_VALIDADO) {
    return "bg-[#d7fce1]";
  }
  if (tratamento === STATUS_TRATAMENTO_NEGLIGENCIADO) {
    return "bg-[#fff5f6]";
  }
  if (motivosDaLinha(row).includes(MOTIVO_DUPLICADO_SOT)) {
    return "bg-[#fff9db]";
  }
  return "";
}

function notify(message) {
  toast.value = message;
  setTimeout(() => {
    toast.value = "";
  }, 3000);
}

function parseApiErrorPayload(payload, statusCode) {
  const codigo = String(payload?.codigo || "").trim();
  const bloqueios = Array.isArray(payload?.bloqueios) ? payload.bloqueios : [];
  const mensagemOriginal = String(payload?.detail || `Erro ${statusCode}`).trim();
  const mensagemBase = MENSAGENS_AMIGAVEIS_BLOQUEIO[codigo] || mensagemOriginal;
  const codigosEncontrados = new Set(
    bloqueios.flatMap((item) => (item?.codigos || []).map((codigoItem) => String(codigoItem || "").trim()).filter(Boolean)),
  );
  const somenteFormato = codigosEncontrados.size === 1 && codigosEncontrados.has("divergencia_formato_pagamento");
  const permiteOverride = Boolean(payload?.permite_override);

  let mensagem = mensagemBase;
  if (somenteFormato && permiteOverride) {
    mensagem = `${mensagemBase} Foram encontradas divergencias somente de tipo de pagamento. Voce pode prosseguir agora ou cancelar para ajustar antes.`;
  } else if (somenteFormato) {
    mensagem = `${mensagemBase} Foram encontradas divergencias de tipo de pagamento que exigem ajuste previo.`;
  }

  return {
    message: mensagem,
    codigo,
    bloqueios,
    permiteOverride,
  };
}

function resumirBloqueios(mensagem, bloqueios) {
  const total = Array.isArray(bloqueios) ? bloqueios.length : 0;
  if (!total) {
    return mensagem || "Operacao bloqueada por inconsistencias.";
  }
  return `${mensagem || "Operacao bloqueada."} (${total} venda(s) com restricao)`;
}

function formatarCodigoBloqueio(codigo) {
  const norm = String(codigo || "").trim();
  return LABELS_CODIGO_BLOQUEIO[norm] || norm || "-";
}

function formatarCodigosBloqueio(codigos) {
  const lista = (codigos || []).map((codigo) => formatarCodigoBloqueio(codigo));
  return lista.length ? lista.join(", ") : "-";
}

function limparEstadoBloqueioModal() {
  bloqueioModalItems.value = [];
  bloqueioModalMensagem.value = "";
  bloqueioModalCodigo.value = "";
  bloqueioModalPodeProsseguir.value = false;
  bloqueioModalOrigem.value = "";
  bloqueioModalConfirmAction.value = null;
  bloqueioModalRunning.value = false;
}

function abrirBloqueioModal({ origem, mensagem, codigo, bloqueios, permiteOverride, onConfirm }) {
  bloqueioModalOrigem.value = origem || "";
  bloqueioModalMensagem.value = mensagem || "Operacao bloqueada por inconsistencias estruturais.";
  bloqueioModalCodigo.value = codigo || "";
  bloqueioModalItems.value = Array.isArray(bloqueios) ? bloqueios : [];

  const podeProsseguir = Boolean(permiteOverride && typeof onConfirm === "function");
  bloqueioModalPodeProsseguir.value = podeProsseguir;
  bloqueioModalConfirmAction.value = podeProsseguir ? onConfirm : null;
  showBloqueioModal.value = true;
}

function cancelarBloqueioModal() {
  showBloqueioModal.value = false;
  limparEstadoBloqueioModal();
}

async function prosseguirBloqueioModal() {
  if (!bloqueioModalConfirmAction.value) {
    return;
  }

  bloqueioModalRunning.value = true;
  try {
    const executar = bloqueioModalConfirmAction.value;
    showBloqueioModal.value = false;
    await executar();
  } catch (err) {
    console.error(err);
    uploadError.value = err?.message || "Falha ao prosseguir com override de bloqueio.";
  } finally {
    limparEstadoBloqueioModal();
  }
}

function applyKpis(data) {
  kpis.total_vendas_stg = Number(data.total_vendas_stg || 0);
  kpis.vendas_aprovadas = Number(data.vendas_aprovadas || 0);
  kpis.vendas_divergentes = Number(data.vendas_divergentes || 0);
  kpis.vendas_duplicadas_sot = Number(data.vendas_duplicadas_sot || 0);
  kpis.vendas_negligenciadas = Number(data.vendas_negligenciadas || 0);
  kpis.soma_valor_stg = data.soma_valor_stg || "0";
  kpis.soma_valor_stg_canceladas = data.soma_valor_stg_canceladas || "0";
  kpis.soma_valor_vendas_validadas = data.soma_valor_vendas_validadas || "0";
  kpis.qtd_vendas_validadas = Number(data.qtd_vendas_validadas || 0);
  kpis.soma_valor_auditoria = data.soma_valor_auditoria || "0";
  kpis.qtd_vendas_auditoria = Number(data.qtd_vendas_auditoria || 0);
  kpis.diferenca_total = data.diferenca_total || String(Number(kpis.soma_valor_vendas_validadas || 0) - Number(kpis.soma_valor_auditoria || 0));
  kpis.motivos_divergencia = data.motivos_divergencia || {};
  kpis.periodo_data_inicial = data.periodo_data_inicial || null;
  kpis.periodo_data_final = data.periodo_data_final || null;
}

function statusBadgeClass(status) {
  const norm = String(status || "").toUpperCase();
  if (norm === "F") return "bg-green-100 text-green-800";
  if (norm === "C") return "bg-amber-100 text-amber-800";
  return "bg-gray-100 text-gray-700";
}

function clearSelection() {
  Object.keys(selectedMap).forEach((key) => {
    delete selectedMap[key];
  });
}

function toggleRow(row, checked) {
  selectedMap[row.row_key] = Boolean(checked);
}

function toggleLinha(row) {
  const atual = Boolean(selectedMap[row.row_key]);
  selectedMap[row.row_key] = !atual;
}

function toggleSelecionarTodos(checked) {
  rows.value.forEach((row) => {
    selectedMap[row.row_key] = Boolean(checked);
  });
}

function openModal() {
  error.value = "";
  showModal.value = true;
}

function filterExcelFiles(fileList) {
  return Array.from(fileList || []).filter((file) => {
    const name = (file.name || "").toLowerCase();
    return name.endsWith(".xlsx") || name.endsWith(".xlsm");
  });
}

function onFolderSelected(event) {
  uploadError.value = "";
  selectedFiles.value = filterExcelFiles(event.target.files);
}

function onFilesSelected(event) {
  uploadError.value = "";
  selectedFiles.value = filterExcelFiles(event.target.files);
}

function clearSelectedFiles() {
  selectedFiles.value = [];
  if (folderInputRef.value) {
    folderInputRef.value.value = "";
  }
  if (filesInputRef.value) {
    filesInputRef.value.value = "";
  }
}

function stopPolling() {
  if (pollingId.value) {
    clearInterval(pollingId.value);
    pollingId.value = null;
  }
}

function resetFluxoLocal() {
  stopPolling();
  clearSelectedFiles();
  clearSelection();
  uploadError.value = "";
  importJob.value = null;
  importJobId.value = "";
  importSummary.arquivos_recebidos = 0;
  importSummary.linhas_importadas = 0;
  importSummary.erros_importacao = [];
  rows.value = [];
  count.value = 0;
  next.value = "";
  previous.value = "";
  activeFiltro.value = "todos";
  somentePendentes.value = true;
  Object.keys(kpis).forEach((key) => {
    if (key === "motivos_divergencia") {
      kpis[key] = {};
    } else if (typeof kpis[key] === "number") {
      kpis[key] = 0;
    } else {
      kpis[key] = "0";
    }
  });
  pendenciasResumo.produtos = 0;
  pendenciasResumo.clientes = 0;
  pendenciasResumo.fornecedores = 0;
  resumoPendenciasDisponivel.value = true;
  lastBloqueioResumo.value = "";
  cancelarBloqueioModal();
}

function abrirConfirmacaoNovaImportacao() {
  showNovaImportacaoModal.value = true;
}

async function confirmarNovaImportacao() {
  resettingFluxo.value = true;
  uploadError.value = "";
  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/limpar-fluxo`, {
      method: "POST",
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `Erro ${response.status}`);
    }

    resetFluxoLocal();
    showNovaImportacaoModal.value = false;
    notify("Fluxo anterior removido. Você pode iniciar uma nova importação.");
  } catch (err) {
    console.error(err);
    uploadError.value = err?.message || "Falha ao reiniciar fluxo de importação.";
  } finally {
    resettingFluxo.value = false;
  }
}

async function carregarResumoPendencias() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/resumo`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `Erro ${response.status}`);
    }

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

function buildUrl(url = "") {
  const target = new URL(url || `${API_BASE_URL}/api/validacao/reconciliacao/divergencias`);
  const filtro = String(activeFiltro.value || "");
  if (filtro.startsWith("status_")) {
    target.searchParams.delete("motivo");
    target.searchParams.set("status_venda", filtro === "status_f" ? "F" : "C");
  } else if (filtro && filtro !== "todos") {
    target.searchParams.set("motivo", filtro);
    target.searchParams.delete("status_venda");
  } else {
    target.searchParams.delete("motivo");
    target.searchParams.delete("status_venda");
  }

  if (somentePendentes.value) {
    target.searchParams.set("tratamento", "PENDENTE");
  } else {
    target.searchParams.delete("tratamento");
  }

  return target.toString();
}

async function loadDivergencias(url = "") {
  loading.value = true;
  tableError.value = "";

  try {
    const response = await fetch(buildUrl(url));
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `Erro ${response.status}`);
    }

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
  if (resetPage) {
    return loadDivergencias("");
  }
  return loadDivergencias();
}

function goNext() {
  if (next.value) {
    loadDivergencias(next.value);
  }
}

function goPrevious() {
  if (previous.value) {
    loadDivergencias(previous.value);
  }
}

async function validarLinha(row, options = {}) {
  const forcarDivergenciaFormato = Boolean(options.forcarDivergenciaFormato);
  const response = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/divergencias/tratar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tipo_documento: row.tipo_documento,
      id_legado: row.id_legado,
      acao: "validar",
      payload: {
        forcar_divergencia_formato: forcarDivergenciaFormato,
      },
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
          ? async () => {
              await validarLinha(row, { forcarDivergenciaFormato: true });
            }
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
    body: JSON.stringify({
      tipo_documento: row.tipo_documento,
      id_legado: row.id_legado,
      acao: "negligenciar",
      payload: {},
    }),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Erro ${response.status}`);
  }

  applyKpis(payload.kpis || {});
  await reloadDivergencias(false);
  notify("Venda negligenciada com sucesso.");
  return true;
}

function abrirConfirmacao(acao, escopo, row = null) {
  if (escopo === "lote" && selectedRows.value.length === 0) {
    return;
  }

  confirmAction.value = acao;
  confirmScope.value = escopo;
  confirmRow.value = row;
  showConfirmModal.value = true;
}

async function confirmarAcao() {
  confirmRunning.value = true;
  try {
    showConfirmModal.value = false;
    let sucesso = false;
    if (confirmScope.value === "linha" && confirmRow.value) {
      if (confirmAction.value === "validar") {
        sucesso = await validarLinha(confirmRow.value);
      } else {
        sucesso = await negligenciarLinha(confirmRow.value);
      }
    } else if (confirmScope.value === "lote") {
      if (confirmAction.value === "validar") {
        sucesso = await validarSelecionados();
      } else {
        sucesso = await negligenciarSelecionados();
      }
    }

    if (!sucesso && !showBloqueioModal.value) {
      showConfirmModal.value = true;
    }
  } catch (err) {
    console.error(err);
    uploadError.value = err?.message || "Falha ao aplicar acao em lote.";
  } finally {
    confirmRunning.value = false;
  }
}

function openEditModal(row) {
  activeRow.value = row;
  showEditModal.value = true;
}

async function saveEdit(payload) {
  if (!activeRow.value) {
    return;
  }

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
    if (!response.ok) {
      throw new Error(result.detail || `Erro ${response.status}`);
    }

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

async function aplicarLote(acao, payload = {}, options = {}) {
  const vendasSelecionadas = Array.isArray(options.vendasOverride) && options.vendasOverride.length
    ? options.vendasOverride
    : selectedRows.value.map((row) => ({
      tipo_documento: row.tipo_documento,
      id_legado: row.id_legado,
    }));

  if (!vendasSelecionadas.length) {
    return false;
  }

  applyingBatch.value = true;
  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/divergencias/tratar-lote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        acao,
        payload,
        vendas: vendasSelecionadas,
      }),
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
        .map((item) => ({
          tipo_documento: item.tipo_documento,
          id_legado: item.id_legado,
        }));

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
              await aplicarLote(
                "validar",
                {
                  ...payload,
                  forcar_divergencia_formato: true,
                },
                {
                  vendasOverride: vendasBloqueadas,
                },
              );
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

function validarSelecionados() {
  return aplicarLote("validar");
}

function negligenciarSelecionados() {
  return aplicarLote("negligenciar");
}

async function carregarFormasPagamento() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/formas-pagamento`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `Erro ${response.status}`);
    }
    formasPagamento.value = payload.rows || [];
  } catch (err) {
    console.error(err);
    formasPagamento.value = [];
  }
}

function abrirModalEdicaoLote() {
  if (!selectedRows.value.length) {
    return;
  }
  editLoteFormaId.value = "";
  showEditLoteModal.value = true;
}

async function confirmarEdicaoLote() {
  if (!editLoteFormaId.value) {
    return;
  }
  editLoteRunning.value = true;
  try {
    const sucesso = await aplicarLote("editar_pagamento", { id_forma: Number(editLoteFormaId.value) });
    if (sucesso) {
      showEditLoteModal.value = false;
    }
  } catch (err) {
    console.error(err);
    uploadError.value = err?.message || "Falha ao editar pagamentos em lote.";
  } finally {
    editLoteRunning.value = false;
  }
}

function startPollingImportJob(jobId) {
  stopPolling();
  uploading.value = true;

  const tick = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/validacao/importar-auditoria-planilhas/status/${jobId}`);
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || `Erro ${response.status}`);
      }

      importJob.value = payload;

      if (payload.status === "completed") {
        const resultado = payload.resultado || {};
        importSummary.arquivos_recebidos = Number(resultado.arquivos_recebidos || 0);
        importSummary.linhas_importadas = Number(resultado.linhas_importadas || 0);
        importSummary.erros_importacao = resultado.erros_importacao || [];

        uploading.value = false;
        stopPolling();
        await reloadDivergencias(true);
        notify("Importacao e validacao concluidas.");
      }

      if (payload.status === "failed") {
        uploadError.value = payload.detail || payload.erro || "Falha no processamento assincrono.";
        uploading.value = false;
        stopPolling();
      }
    } catch (err) {
      console.error(err);
      uploadError.value = err?.message || "Erro ao consultar status da importacao.";
      uploading.value = false;
      stopPolling();
    }
  };

  tick();
  pollingId.value = setInterval(tick, 1500);
}

async function importAuditoria() {
  uploadError.value = "";
  importJob.value = null;
  importJobId.value = "";

  if (!selectedFiles.value.length) {
    uploadError.value = "Selecione ao menos um arquivo .xlsx ou .xlsm.";
    return;
  }

  uploading.value = true;
  try {
    const formData = new FormData();
    selectedFiles.value.forEach((file) => {
      formData.append("files", file);
    });

    const response = await fetch(`${API_BASE_URL}/api/validacao/importar-auditoria-planilhas`, {
      method: "POST",
      body: formData,
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `Erro ${response.status}`);
    }

    importJobId.value = payload?.job_id || "";
    if (!importJobId.value) {
      throw new Error("Nao foi possivel iniciar o processamento assincrono.");
    }

    startPollingImportJob(importJobId.value);
    notify("Importacao iniciada. Acompanhe o progresso em tempo real.");
  } catch (err) {
    console.error(err);
    uploadError.value = err?.message || "Falha ao importar planilhas de auditoria.";
    uploading.value = false;
  }
}

async function consolidarSot() {
  await carregarResumoPendencias();
  if (!canConsolidar.value) {
    uploadError.value = "Consolidacao bloqueada. Verifique os motivos exibidos no painel.";
    return;
  }

  const forcarDivergenciaFormato = false;

  async function executarConsolidacao(overrideFormato = false) {
    const response = await fetch(`${API_BASE_URL}/api/validacao/consolidar-vendas-sot`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        forcar_divergencia_formato: Boolean(overrideFormato),
      }),
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
          onConfirm: erroApi.permiteOverride
            ? async () => {
                await executarConsolidacao(true);
              }
            : null,
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
    await executarConsolidacao(forcarDivergenciaFormato);
  } catch (err) {
    console.error(err);
    uploadError.value = err?.message || "Falha ao consolidar vendas no SOT.";
  } finally {
    consolidating.value = false;
  }
}

async function submit() {
  error.value = "";

  if (!form.data_inicial || !form.data_final) {
    error.value = "Preencha data inicial e data final.";
    return;
  }

  submitting.value = true;
  try {
    await executarSincronizacaoFirebird(`${API_BASE_URL}/api/validacao/sincronizar-vendas-firebird`, {
      data_inicial: form.data_inicial,
      data_final: form.data_final,
    }, {
      allowBrowserUploadFallback: false,
    });

    showModal.value = false;
    notify("Sincronizacao de vendas concluida com sucesso.");
  } catch (err) {
    console.error(err);
    error.value = formatarErroSincronizacao(err, "Falha ao sincronizar vendas do legado.");
  } finally {
    submitting.value = false;
  }
}

onMounted(async () => {
  await Promise.all([reloadDivergencias(true), carregarFormasPagamento(), carregarResumoPendencias()]);
});

onBeforeUnmount(() => {
  stopPolling();
});
</script>
