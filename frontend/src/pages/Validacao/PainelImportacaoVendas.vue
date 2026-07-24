<template>
  <!-- Hub de sincronização + matriz de datas -->
  <article class="rounded-md border border-gray-200 bg-white p-4 space-y-3">
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

    <!-- Matriz de últimas datas no staging -->
    <div>
      <p class="mb-1.5 text-xs font-medium text-gray-500">Últimas datas com vendas no staging</p>
      <div v-if="loadingDatas" class="text-xs text-gray-400">Carregando...</div>
      <div v-else-if="resumoDatas.length === 0" class="text-xs text-gray-400">Nenhuma venda importada ainda.</div>
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
    </div>
  </article>

  <!-- Ingestão de auditoria (Excel) -->
  <article class="rounded-md border border-gray-200 bg-white p-4 space-y-3">
    <div>
      <h3 class="text-sm font-semibold text-[#373435]">Ingestão de Auditoria (Excel)</h3>
      <p class="mt-1 text-xs text-gray-500">Selecione uma pasta ou vários arquivos .xlsx/.xlsm da aba HostVenda para importar e validar.</p>
    </div>

    <div class="flex flex-wrap gap-2">
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

    <!-- Botão de importação (abaixo da seleção) -->
    <button
      type="button"
      class="inline-flex w-full items-center justify-center gap-2 rounded-md bg-[#2f6f4f] px-3 py-2 text-xs font-semibold text-white hover:bg-[#275d43] disabled:cursor-not-allowed disabled:opacity-70"
      :disabled="uploading || selectedFiles.length === 0"
      @click="importAuditoria"
    >
      <Loader2 v-if="uploading" class="h-4 w-4 animate-spin" />
      <Upload v-else class="h-4 w-4" />
      {{ uploading ? "Importando..." : `Importar e Validar${selectedFiles.length ? ` (${selectedFiles.length})` : ""}` }}
    </button>

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
</template>

<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { FileSpreadsheet, Folder, Loader2, RefreshCw, Upload } from "lucide-vue-next";
import BaseInput from "@/components/ui/BaseInput.vue";
import BaseModal from "@/components/ui/BaseModal.vue";
import { executarSincronizacaoFirebird, formatarErroSincronizacao, getApiBaseUrl } from "@/services/firebirdSync";
import { applyKpis } from "./composables/useSharedKpis";
import { notify } from "./composables/useToast";
import { importSummary } from "./composables/useImportSummary";

const API_BASE_URL = getApiBaseUrl();

// --- Estado da matriz de datas ---
const resumoDatas = ref([]);
const loadingDatas = ref(false);

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

// --- Estado do modal de sincronização ---
const showModal = ref(false);
const submitting = ref(false);
const error = ref("");
const form = reactive({ data_inicial: "", data_final: "" });

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
  showModal.value = true;
}

async function submit() {
  error.value = "";
  if (!form.data_inicial || !form.data_final) {
    error.value = "Preencha data inicial e data final.";
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

        // Busca kpis atualizados para ativar a transição para o PainelGerenciamentoStg.
        // O painel de gerenciamento irá carregar seus próprios dados via onMounted.
        try {
          const kpisResponse = await fetch(`${API_BASE_URL}/api/validacao/reconciliacao/divergencias`);
          const kpisPayload = await kpisResponse.json().catch(() => ({}));
          if (kpisResponse.ok) {
            applyKpis((kpisPayload.results || {}).kpis || {});
          }
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

// --- Reset público (chamado pelo coordenador após nova importação) ---
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
