<template>
  <section class="space-y-4">
    <article v-if="!hasValidationResult" class="rounded-md border border-gray-200 bg-white p-4">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 class="text-sm font-semibold text-[#373435]">Hub de Reconciliacao Financeira</h2>
          <p class="mt-1 text-xs text-gray-500">Integracao isolada para ingestao legado de vendas NFCe e DAV no staging.</p>
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
          <h3 class="text-sm font-semibold text-[#373435]">Ingestao de Auditoria (Excel)</h3>
          <p class="mt-1 text-xs text-gray-500">Selecione uma pasta ou varios arquivos .xlsx/.xlsm da aba HostVenda para importar e validar.</p>
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
          Limpar Selecao
        </button>
      </div>

      <div class="rounded-md border border-gray-100 bg-gray-50 p-3 text-xs text-gray-600">
        <p><strong>Arquivos prontos para importacao:</strong> {{ selectedFiles.length }}</p>
      </div>

      <div v-if="importJob" class="rounded-md border border-blue-100 bg-blue-50 p-3 text-xs text-blue-900">
        <p><strong>Status:</strong> {{ importJob.status }} - {{ importJob.stage }}</p>
        <p class="mt-1">{{ importJob.detail }}</p>
      </div>

      <p v-if="uploadError" class="text-xs text-red-600">{{ uploadError }}</p>
    </article>

    <article v-if="hasValidationResult" class="rounded-md border border-gray-200 bg-white p-4 space-y-3">
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h3 class="text-xs font-semibold uppercase tracking-wide text-gray-500">Resumo da Importacao e Validacao</h3>
        <button type="button" class="rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50" @click="resetFluxo">
          Nova importacao
        </button>
      </div>

      <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Data inicial</p>
          <p class="text-lg font-semibold text-[#373435]">{{ kpis.periodo_data_inicial || '-' }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Data final</p>
          <p class="text-lg font-semibold text-[#373435]">{{ kpis.periodo_data_final || '-' }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Vendas aprovadas</p>
          <p class="text-lg font-semibold text-[#2f6f4f]">{{ kpis.vendas_aprovadas || 0 }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Vendas divergentes</p>
          <p class="text-lg font-semibold text-[#a82631]">{{ kpis.vendas_divergentes || 0 }}</p>
        </div>
      </div>

      <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Vendas Finalizadas</p>
          <div class="mt-1 flex items-baseline justify-between gap-2">
            <p class="text-sm font-semibold text-[#373435]">{{ asMoney(kpis.soma_valor_stg) }}</p>
            <p class="text-[10px] text-gray-400">Canceladas: {{ asMoney(kpis.soma_valor_stg_canceladas) }}</p>
          </div>
        </div>
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Total Auditoria</p>
          <p class="text-sm font-semibold text-[#373435]">{{ asMoney(kpis.soma_valor_auditoria) }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Diferenca Total</p>
          <p class="text-sm font-semibold" :class="Number(kpis.diferenca_total || 0) === 0 ? 'text-[#2f6f4f]' : 'text-[#a82631]'">{{ asMoney(kpis.diferenca_total) }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Negligenciadas</p>
          <p class="text-sm font-semibold text-[#373435]">{{ kpis.vendas_negligenciadas || 0 }}</p>
        </div>
      </div>

      <div class="flex flex-col gap-2 rounded-md border border-gray-200 bg-white p-3 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center gap-2">
          <label class="text-xs text-gray-700">Filtro:</label>
          <select v-model="activeFiltro" class="rounded-md border border-gray-200 px-2 py-1 text-xs" @change="reloadDivergencias(true)">
            <option value="todos">Todas divergencias</option>
            <option value="divergencia_totais">Divergencia de totais</option>
            <option value="divergencia_formato">Divergencia de formato</option>
            <option value="duplicado_sot">Duplicado no SOT</option>
            <option value="status_f">Somente finalizados</option>
            <option value="status_c">Somente cancelados</option>
          </select>
          <label class="inline-flex items-center gap-1 text-xs text-gray-700">
            <input v-model="somentePendentes" type="checkbox" @change="reloadDivergencias(true)" />
            Somente pendentes
          </label>
          <label class="inline-flex items-center gap-1 text-xs text-gray-700">
            <input :checked="allPaginaSelecionada" type="checkbox" @change="toggleSelecionarTodos($event.target.checked)" />
            Selecionar todos da pagina
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
        title="Divergencias Consolidadas"
        subtitle="Comparacao entre STG e Auditoria"
        :columns="tableColumns"
        :rows="rows"
        row-key="row_key"
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
          <span :class="financialDivergenciaClass(row, 'total_itens')">
            {{ asMoney(row.totais?.total_itens) }}
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
        <p v-else class="text-xs text-red-600">Existem divergencias pendentes. Resolva-as ou negligencie-as antes da aprovacao.</p>
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

const API_BASE_URL = "http://127.0.0.1:8000";

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

const kpis = reactive({
  total_vendas_stg: 0,
  vendas_aprovadas: 0,
  vendas_divergentes: 0,
  vendas_duplicadas_sot: 0,
  vendas_negligenciadas: 0,
  soma_valor_stg: "0",
  soma_valor_stg_canceladas: "0",
  soma_valor_auditoria: "0",
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
const formasPagamento = ref([]);
const showEditLoteModal = ref(false);
const editLoteFormaId = ref("");
const editLoteRunning = ref(false);

const selectedMap = reactive({});

const form = reactive({
  data_inicial: "",
  data_final: "",
});

const tableColumns = [
  { key: "select", label: "Sel" },
  { key: "venda", label: "Venda" },
  { key: "status_venda", label: "Status" },
  { key: "total_documento", label: "Documento" },
  { key: "total_itens", label: "Total Itens" },
  { key: "total_pagamentos", label: "Total Pag." },
  { key: "total_auditoria", label: "Total Aud." },
  { key: "formato_venda", label: "Form. Venda" },
  { key: "formato_auditoria", label: "Form. Aud." },
  { key: "cliente", label: "Cliente" },
];

const hasValidationResult = computed(() => Number(kpis.total_vendas_stg || 0) > 0);
const canConsolidar = computed(() => Number(kpis.vendas_divergentes || 0) === 0 && Number(kpis.vendas_aprovadas || 0) > 0);
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

function asMoney(value) {
  const numeric = Number(value || 0);
  return numeric.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

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

function notify(message) {
  toast.value = message;
  setTimeout(() => {
    toast.value = "";
  }, 3000);
}

function applyKpis(data) {
  kpis.total_vendas_stg = Number(data.total_vendas_stg || 0);
  kpis.vendas_aprovadas = Number(data.vendas_aprovadas || 0);
  kpis.vendas_divergentes = Number(data.vendas_divergentes || 0);
  kpis.vendas_duplicadas_sot = Number(data.vendas_duplicadas_sot || 0);
  kpis.vendas_negligenciadas = Number(data.vendas_negligenciadas || 0);
  kpis.soma_valor_stg = data.soma_valor_stg || "0";
  kpis.soma_valor_stg_canceladas = data.soma_valor_stg_canceladas || "0";
  kpis.soma_valor_auditoria = data.soma_valor_auditoria || "0";
  kpis.diferenca_total = data.diferenca_total || "0";
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

function resetFluxo() {
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

async function validarLinha(row) {
  const response = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/divergencias/tratar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tipo_documento: row.tipo_documento,
      id_legado: row.id_legado,
      acao: "validar",
      payload: {},
    }),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Erro ${response.status}`);
  }

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

    if (sucesso) {
      showConfirmModal.value = false;
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

async function aplicarLote(acao, payload = {}) {
  if (!selectedRows.value.length) {
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
        vendas: selectedRows.value.map((row) => ({
          tipo_documento: row.tipo_documento,
          id_legado: row.id_legado,
        })),
      }),
    });

    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(result.detail || `Erro ${response.status}`);
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
  if (!canConsolidar.value) {
    uploadError.value = "Ainda existem divergencias pendentes; consolidacao bloqueada.";
    return;
  }

  consolidating.value = true;
  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/consolidar-vendas-sot`, {
      method: "POST",
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `Erro ${response.status}`);
    }

    consolidacaoResult.value = payload?.resultado || null;
    notify("Consolidacao STG -> SOT concluida.");
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
    const response = await fetch(`${API_BASE_URL}/api/validacao/sincronizar-vendas-firebird`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        data_inicial: form.data_inicial,
        data_final: form.data_final,
      }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `Erro ${response.status}`);
    }

    showModal.value = false;
    notify("Sincronizacao de vendas concluida com sucesso.");
  } catch (err) {
    console.error(err);
    error.value = err?.message || "Falha ao sincronizar vendas do legado.";
  } finally {
    submitting.value = false;
  }
}

onMounted(async () => {
  await Promise.all([reloadDivergencias(true), carregarFormasPagamento()]);
});

onBeforeUnmount(() => {
  stopPolling();
});
</script>
