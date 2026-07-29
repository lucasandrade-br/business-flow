<template>
  <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:items-start">

    <!-- Coluna esquerda: Hubs de ação -->
    <div class="space-y-3">

      <!-- Hub Firebird -->
      <article class="rounded-md border border-gray-200 bg-white p-4 space-y-3">
        <div>
          <h2 class="text-sm font-semibold text-[#373435]">Hub de Sincronização (Firebird)</h2>
          <p class="mt-1 text-xs text-gray-500">Ingestão legado de vendas NFCe e DAV diretamente do banco Firebird para o staging.</p>
        </div>
        <button
          type="button"
          class="inline-flex w-full items-center justify-center gap-2 rounded-md bg-[#373435] px-3 py-2 text-xs font-semibold text-white hover:bg-[#1a1618] disabled:cursor-not-allowed disabled:opacity-70"
          :disabled="submitting"
          @click="openModal"
        >
          <RefreshCw class="h-4 w-4" />
          Sincronizar Vendas (Legado)
        </button>

        <!-- Datas capturadas na última sincronização -->
        <div v-if="datasFirebirdCapturadas.length" class="max-h-40 overflow-y-auto rounded-md border border-gray-100 bg-gray-50 py-1.5">
          <div
            v-for="row in datasFirebirdCapturadas"
            :key="row.data"
            class="flex items-center justify-between gap-1.5 px-3 py-0.5"
          >
            <div class="flex items-center gap-1.5">
              <CalendarCheck class="h-3.5 w-3.5 shrink-0 text-green-600" />
              <span class="font-mono text-xs text-gray-700">{{ formatarData(row.data) }}</span>
            </div>
            <span class="tabular-nums text-xs text-gray-500">{{ row.qtd }} venda(s)</span>
          </div>
        </div>
        <div v-else-if="sincronizadoPeriodo" class="rounded-md border border-dashed border-gray-200 bg-gray-50 px-3 py-2.5 text-xs text-gray-400">
          Nenhuma venda encontrada no período sincronizado.
        </div>
      </article>

      <!-- Hub Excel Auditoria -->
      <article class="rounded-md border border-gray-200 bg-white p-4 space-y-3">
        <div>
          <h3 class="text-sm font-semibold text-[#373435]">Hub de Auditoria (Excel)</h3>
          <p class="mt-1 text-xs text-gray-500">Selecione uma pasta ou vários arquivos .xlsx/.xlsm da aba HostVenda para importar e validar.</p>
        </div>

        <div class="flex flex-wrap gap-2">
          <label class="inline-flex cursor-pointer items-center justify-center gap-2 rounded-md bg-[#373435] px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-[#1a1618] hover:text-white">
            <Folder class="h-4 w-4" />
            Selecionar Pasta
            <input ref="folderInputRef" type="file" class="hidden" webkitdirectory directory multiple @change="onFolderSelected" />
          </label>

          <label class="inline-flex cursor-pointer items-center justify-center gap-2 rounded-md bg-[#373435] px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-[#1a1618] hover:text-white">
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
            Limpar
          </button>
        </div>

        <!-- Lista de arquivos selecionados -->
        <div v-if="selectedFiles.length" class="max-h-36 overflow-y-auto rounded-md border border-gray-100 bg-gray-50 py-1.5">
          <div
            v-for="file in selectedFiles"
            :key="file.name"
            class="flex items-center gap-1.5 px-3 py-0.5"
          >
            <FileSpreadsheet class="h-3.5 w-3.5 shrink-0 text-green-600" />
            <span class="truncate text-xs text-gray-700">{{ file.name }}</span>
          </div>
        </div>
        <div v-else class="rounded-md border border-dashed border-gray-200 bg-gray-50 px-3 py-2.5 text-xs text-gray-400">
          Nenhum arquivo selecionado.
        </div>

      </article>

      <!-- Ação de processamento (isolada) -->
      <button
        type="button"
        class="inline-flex w-full items-center justify-center gap-2 rounded-md bg-[#2f6f4f] px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-[#275d43] disabled:cursor-not-allowed disabled:opacity-70"
        :disabled="uploading || selectedFiles.length === 0"
        @click="importAuditoria"
      >
        <Loader2 v-if="uploading" class="h-4 w-4 animate-spin" />
        <Upload v-else class="h-4 w-4" />
        {{ uploading ? "Importando..." : `Processar e Validar${selectedFiles.length ? ` (${selectedFiles.length})` : ""}` }}
      </button>

      <div v-if="importJob" class="rounded-md border border-blue-100 bg-blue-50 p-3 text-xs text-blue-900">
        <p><strong>Status:</strong> {{ importJob.status }} — {{ importJob.stage }}</p>
        <p class="mt-1">{{ importJob.detail }}</p>
      </div>

      <p v-if="uploadError" class="text-xs text-red-600">{{ uploadError }}</p>

      <div
        v-if="lastBloqueioResumo"
        class="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900"
      >
        {{ lastBloqueioResumo }}
      </div>

    </div>

    <!-- Coluna direita: Matriz de datas -->
    <article class="rounded-md border border-gray-200 bg-white p-4 space-y-3">
      <div>
        <h3 class="text-sm font-semibold text-[#373435]">Últimas datas com vendas</h3>
        <p class="mt-1 text-xs text-gray-500">Vendas já sincronizadas do Firebird.</p>
      </div>

      <div v-if="loadingDatas" class="py-6 text-center text-xs text-gray-400">Carregando...</div>
      <div v-else-if="resumoDatas.length === 0" class="py-6 text-center text-xs text-gray-400">Nenhuma venda importada ainda.</div>
      <div v-else class="overflow-x-auto rounded-md border border-gray-100">
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-gray-100 bg-gray-50 text-left text-gray-500">
              <th class="px-3 py-2 font-medium">Data</th>
              <th class="px-3 py-2 text-right font-medium">Vendas</th>
              <th class="px-3 py-2 text-right font-medium">Total (R$)</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, idx) in resumoDatas"
              :key="row.data"
              :class="idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/60'"
              class="border-b border-gray-100 last:border-0"
            >
              <td class="px-3 py-1.5 font-mono text-gray-700">{{ formatarData(row.data) }}</td>
              <td class="px-3 py-1.5 text-right tabular-nums text-gray-700">{{ row.qtd }}</td>
              <td class="px-3 py-1.5 text-right tabular-nums font-medium text-gray-900">{{ formatarValor(row.total) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <button
        type="button"
        class="text-[11px] text-gray-400 hover:text-gray-600 underline"
        @click="carregarResumoDatas"
      >
        Atualizar
      </button>
    </article>

  </div>

  <!-- Modal com calendário de seleção de período -->
  <BaseModal
    v-model="showModal"
    title="Sincronizar Vendas Legado"
    description="Selecione o período desejado para extração do banco Firebird."
  >
    <div class="space-y-3">
      <!-- Navegação de mês -->
      <div class="flex items-center justify-between">
        <button type="button" class="rounded p-1 hover:bg-gray-100" @click="prevMonth">
          <ChevronLeft class="h-4 w-4 text-gray-600" />
        </button>
        <span class="text-xs font-semibold text-[#373435]">{{ calendarMonthLabel }}</span>
        <button type="button" class="rounded p-1 hover:bg-gray-100" @click="nextMonth">
          <ChevronRight class="h-4 w-4 text-gray-600" />
        </button>
      </div>

      <!-- Calendário -->
      <div class="select-none">
        <!-- Cabeçalho dos dias da semana -->
        <div class="mb-1 grid grid-cols-7">
          <div
            v-for="d in ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']"
            :key="d"
            class="py-1 text-center text-[10px] font-semibold uppercase tracking-wide text-gray-400"
          >
            {{ d }}
          </div>
        </div>
        <!-- Grade de dias -->
        <div class="grid grid-cols-7">
          <button
            v-for="(day, idx) in calendarDays"
            :key="idx"
            type="button"
            class="flex h-7 items-center justify-center text-[11px] transition-colors"
            :class="calendarCellClasses(day)"
            @click="selectDate(day)"
            @mouseenter="hoverDate = day.currentMonth ? toISO(day.date) : null"
            @mouseleave="hoverDate = null"
          >
            {{ day.date.getDate() }}
          </button>
        </div>
      </div>

      <!-- Resumo do período selecionado -->
      <div class="flex items-center justify-between border-t border-gray-100 pt-2">
        <span class="text-[11px] text-gray-500">
          <template v-if="form.data_inicial && form.data_final">
            <strong>{{ formatarData(form.data_inicial) }}</strong>
            &nbsp;→&nbsp;
            <strong>{{ formatarData(form.data_final) }}</strong>
            &nbsp;·&nbsp;{{ diasPeriodo }} dia(s)
          </template>
          <template v-else-if="form.data_inicial">
            <strong>{{ formatarData(form.data_inicial) }}</strong> — selecione a data final
          </template>
          <template v-else>
            Clique para selecionar a data inicial
          </template>
        </span>
        <button
          v-if="form.data_inicial"
          type="button"
          class="text-[11px] text-gray-400 hover:text-gray-600"
          @click="clearCalendar"
        >
          Limpar
        </button>
      </div>
    </div>

    <p v-if="error" class="mt-2 text-xs text-red-600">{{ error }}</p>

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
        class="inline-flex items-center gap-2 rounded-md bg-[#373435] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#1a1618] disabled:cursor-not-allowed disabled:opacity-70"
        :disabled="submitting"
        @click="submit"
      >
        <Loader2 v-if="submitting" class="h-3.5 w-3.5 animate-spin" />
        <RefreshCw v-else class="h-3.5 w-3.5" />
        {{ submitting ? "Sincronizando..." : "Executar sincronização" }}
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { CalendarCheck, ChevronLeft, ChevronRight, FileSpreadsheet, Folder, Loader2, RefreshCw, Upload } from "lucide-vue-next";
import BaseModal from "@/components/ui/BaseModal.vue";
import { executarSincronizacaoFirebird, formatarErroSincronizacao, getApiBaseUrl } from "@/services/firebirdSync";
import { applyKpis } from "./composables/useSharedKpis";
import { notify } from "./composables/useToast";
import { importSummary } from "./composables/useImportSummary";

const API_BASE_URL = getApiBaseUrl();

// --- Estado da matriz de datas (SOT — tabela oficial, coluna direita) ---
const resumoDatas = ref([]);
const loadingDatas = ref(false);

// --- Estado das datas do staging (STG — hub Firebird, coluna esquerda) ---
const resumoDatasStg = ref([]);

function formatarData(isoDate) {
  if (!isoDate) return "";
  const [y, m, d] = isoDate.split("-");
  return `${d}/${m}/${y}`;
}

function formatarValor(val) {
  return Number(val || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

async function carregarResumoDatas() {
  loadingDatas.value = true;
  try {
    const res = await fetch(`${API_BASE_URL}/api/validacao/importacao/resumo-datas`);
    const data = await res.json().catch(() => []);
    resumoDatas.value = Array.isArray(data) ? data : [];
  } catch (e) {
    console.error(e);
  } finally {
    loadingDatas.value = false;
  }
}

async function carregarResumoDatasStg() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/validacao/importacao/resumo-datas-stg`);
    const data = await res.json().catch(() => []);
    resumoDatasStg.value = Array.isArray(data) ? data : [];
  } catch (e) {
    console.error(e);
  }
}

// --- Estado do modal de sincronização ---
const showModal = ref(false);
const submitting = ref(false);
const error = ref("");
const form = reactive({ data_inicial: "", data_final: "" });
const sincronizadoPeriodo = ref(null);

// --- Estado do calendário de seleção de período ---
const MONTH_NAMES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
const calendarDate = ref(new Date());
const hoverDate = ref(null);
const selecting = ref(false);

const calendarYear = computed(() => calendarDate.value.getFullYear());
const calendarMonth = computed(() => calendarDate.value.getMonth());
const calendarMonthLabel = computed(() => `${MONTH_NAMES[calendarMonth.value]} ${calendarYear.value}`);

const calendarDays = computed(() => {
  const year = calendarYear.value;
  const month = calendarMonth.value;
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  let startDow = firstDay.getDay();
  if (startDow === 0) startDow = 7;
  startDow -= 1;
  const days = [];
  for (let i = startDow; i > 0; i--) {
    days.push({ date: new Date(year, month, 1 - i), currentMonth: false });
  }
  for (let d = 1; d <= lastDay.getDate(); d++) {
    days.push({ date: new Date(year, month, d), currentMonth: true });
  }
  let nextDay = 1;
  while (days.length < 42) {
    days.push({ date: new Date(year, month + 1, nextDay++), currentMonth: false });
  }
  return days;
});

function toISO(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function prevMonth() {
  calendarDate.value = new Date(calendarYear.value, calendarMonth.value - 1, 1);
}

function nextMonth() {
  calendarDate.value = new Date(calendarYear.value, calendarMonth.value + 1, 1);
}

function selectDate(day) {
  if (!day.currentMonth) return;
  const iso = toISO(day.date);
  if (!form.data_inicial || (form.data_inicial && form.data_final)) {
    form.data_inicial = iso;
    form.data_final = '';
    selecting.value = true;
  } else if (iso >= form.data_inicial) {
    form.data_final = iso;
    selecting.value = false;
    hoverDate.value = null;
  } else {
    form.data_inicial = iso;
    form.data_final = '';
  }
}

function clearCalendar() {
  form.data_inicial = '';
  form.data_final = '';
  selecting.value = false;
  hoverDate.value = null;
}

function calendarCellClasses(day) {
  if (!day.currentMonth) return 'text-gray-300 cursor-default';
  const iso = toISO(day.date);
  const isStart = iso === form.data_inicial;
  const isEnd = iso === form.data_final;
  const inRange = form.data_inicial && form.data_final && iso > form.data_inicial && iso < form.data_final;
  const isHoverRange = selecting.value && hoverDate.value && iso > form.data_inicial && iso <= hoverDate.value;
  if (isStart || isEnd) return 'bg-[#373435] text-white rounded-md font-semibold cursor-pointer';
  if (inRange) return 'bg-gray-100 text-gray-700 cursor-pointer';
  if (isHoverRange) return 'bg-gray-50 text-gray-600 cursor-pointer';
  return 'text-gray-700 hover:bg-gray-100 cursor-pointer rounded-md';
}

const datasFirebirdCapturadas = computed(() => {
  if (!sincronizadoPeriodo.value) return [];
  const { ini, fin } = sincronizadoPeriodo.value;
  return resumoDatasStg.value.filter((row) => row.data >= ini && row.data <= fin);
});

const diasPeriodo = computed(() => {
  if (!form.data_inicial || !form.data_final) return null;
  const ini = new Date(form.data_inicial);
  const fin = new Date(form.data_final);
  if (isNaN(ini) || isNaN(fin) || fin < ini) return null;
  return Math.round((fin - ini) / (1000 * 60 * 60 * 24)) + 1;
});

// --- Estado de seleção de arquivos ---
const selectedFiles = ref([]);
const folderInputRef = ref(null);
const filesInputRef = ref(null);
const uploadError = ref("");

// --- Estado do job de importação ---
const uploading = ref(false);
const importJob = ref(null);
const importJobId = ref("");
const pollingId = ref(null);
const lastBloqueioResumo = ref("");

// --- Handlers do modal de sincronização ---
function openModal() {
  error.value = "";
  form.data_inicial = "";
  form.data_final = "";
  selecting.value = false;
  hoverDate.value = null;
  calendarDate.value = new Date();
  showModal.value = true;
}

async function submit() {
  error.value = "";
  if (!form.data_inicial || !form.data_final) {
    error.value = "Selecione as datas de início e fim do período.";
    return;
  }
  if (form.data_final < form.data_inicial) {
    error.value = "A data final deve ser igual ou posterior à data inicial.";
    return;
  }
  submitting.value = true;
  try {
    await executarSincronizacaoFirebird(
      `${API_BASE_URL}/api/validacao/sincronizar-vendas-firebird`,
      { data_inicial: form.data_inicial, data_final: form.data_final },
      { allowBrowserUploadFallback: false },
    );
    showModal.value = false;
    notify("Sincronizacao de vendas concluida com sucesso.");
    sincronizadoPeriodo.value = { ini: form.data_inicial, fin: form.data_final };
    await Promise.all([carregarResumoDatas(), carregarResumoDatasStg()]);
  } catch (err) {
    console.error(err);
    error.value = formatarErroSincronizacao(err, "Falha ao sincronizar vendas do legado.");
  } finally {
    submitting.value = false;
  }
}

// --- Handlers de seleção de arquivos ---
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
  if (folderInputRef.value) folderInputRef.value.value = "";
  if (filesInputRef.value) filesInputRef.value.value = "";
}

// --- Polling e importação ---
function stopPolling() {
  if (pollingId.value) {
    clearInterval(pollingId.value);
    pollingId.value = null;
  }
}

function startPollingImportJob(jobId) {
  stopPolling();
  uploading.value = true;

  const tick = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/validacao/importar-auditoria-planilhas/status/${jobId}`);
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || `Erro ${response.status}`);

      importJob.value = payload;

      if (payload.status === "completed") {
        const resultado = payload.resultado || {};
        importSummary.arquivos_recebidos = Number(resultado.arquivos_recebidos || 0);
        importSummary.linhas_importadas = Number(resultado.linhas_importadas || 0);
        importSummary.erros_importacao = resultado.erros_importacao || [];

        uploading.value = false;
        stopPolling();

        try {
          const kpisResponse = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/divergencias`);
          const kpisPayload = await kpisResponse.json().catch(() => ({}));
          if (kpisResponse.ok) applyKpis((kpisPayload.results || {}).kpis || {});
        } catch (e) {
          console.error(e);
        }

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
    selectedFiles.value.forEach((file) => { formData.append("files", file); });

    const response = await fetch(`${API_BASE_URL}/api/validacao/importar-auditoria-planilhas`, {
      method: "POST",
      body: formData,
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `Erro ${response.status}`);

    importJobId.value = payload?.job_id || "";
    if (!importJobId.value) throw new Error("Nao foi possivel iniciar o processamento assincrono.");

    startPollingImportJob(importJobId.value);
    notify("Importacao iniciada. Acompanhe o progresso em tempo real.");
  } catch (err) {
    console.error(err);
    uploadError.value = err?.message || "Falha ao importar planilhas de auditoria.";
    uploading.value = false;
  }
}

// --- Reset público ---
function reset() {
  stopPolling();
  clearSelectedFiles();
  uploadError.value = "";
  importJob.value = null;
  importJobId.value = "";
  lastBloqueioResumo.value = "";
}

defineExpose({ reset });

onMounted(() => {
  carregarResumoDatas();
});

onBeforeUnmount(() => {
  stopPolling();
});
</script>

