<template>
  <section class="space-y-4">
    <article class="rounded-md border border-gray-200 bg-white p-4">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 class="text-sm font-semibold text-[#373435]">Integracao de Compras</h2>
          <p class="mt-1 text-xs text-gray-500">
            Sincronize compras do legado, trate divergencias e consolide para o SOT seguindo o fluxo operacional do sistema.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <DateRangeField v-model:start="dataInicial" v-model:end="dataFinal" placeholder="Periodo da compra" />
          <button
            type="button"
            class="inline-flex items-center gap-2 rounded-md bg-[#a82631] px-3 py-2 text-xs font-semibold text-white hover:bg-[#901f29] disabled:cursor-not-allowed disabled:opacity-70"
            :disabled="syncing"
            @click="sincronizarCompras"
          >
            <RefreshCw class="h-4 w-4" :class="syncing ? 'animate-spin' : ''" />
            {{ syncing ? "Sincronizando..." : "Sincronizar Compras" }}
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-2 rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-60"
            :disabled="limpandoFluxo"
            @click="abrirConfirmacaoLimpeza"
          >
            <Eraser class="h-4 w-4" />
            {{ limpandoFluxo ? "Limpando..." : "Limpar Fluxo" }}
          </button>
        </div>
      </div>

      <p v-if="globalError" class="mt-3 text-xs text-red-600">{{ globalError }}</p>
    </article>

    <article class="rounded-md border border-gray-200 bg-white p-4">
      <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Periodo inicial</p>
          <p class="text-sm font-semibold text-[#373435]">{{ formatDateBr(kpis.periodo_data_inicial) }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Periodo final</p>
          <p class="text-sm font-semibold text-[#373435]">{{ formatDateBr(kpis.periodo_data_final) }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Compras STG</p>
          <p class="text-lg font-semibold text-[#373435]">{{ kpis.total_compras_stg || 0 }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Valor total STG</p>
          <p class="text-sm font-semibold text-[#373435]">{{ asMoney(kpis.soma_valor_stg) }}</p>
        </div>
      </div>

      <div class="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Aprovadas</p>
          <p class="text-lg font-semibold text-[#2f6f4f]">{{ kpis.compras_aprovadas || 0 }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Divergentes</p>
          <p class="text-lg font-semibold text-[#a82631]">{{ kpis.compras_divergentes || 0 }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Duplicadas SOT</p>
          <p class="text-lg font-semibold text-[#373435]">{{ kpis.compras_duplicadas_sot || 0 }}</p>
        </div>
        <div class="rounded-md border border-gray-200 p-3">
          <p class="text-[11px] text-gray-500">Negligenciadas</p>
          <p class="text-lg font-semibold text-[#373435]">{{ kpis.compras_negligenciadas || 0 }}</p>
        </div>
      </div>

      <div class="mt-3 rounded-md border border-gray-100 bg-gray-50 p-3">
        <p class="text-[11px] font-semibold uppercase tracking-wide text-gray-500">Motivos de divergencia</p>
        <div class="mt-2 flex flex-wrap gap-1.5">
          <span
            v-for="item in motivosKpiOrdenados"
            :key="item.codigo"
            class="inline-flex items-center rounded-full border border-gray-200 bg-white px-2 py-0.5 text-[11px] text-gray-700"
          >
            {{ item.label }}: {{ item.total }}
          </span>
          <span v-if="!motivosKpiOrdenados.length" class="text-xs text-gray-500">Sem divergencias registradas.</span>
        </div>
      </div>
    </article>

    <article class="rounded-md border border-gray-200 bg-white p-3">
      <div class="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div class="flex flex-wrap items-center gap-2">
          <select v-model="filtroMotivo" class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs">
            <option value="">Todos os motivos</option>
            <option v-for="item in motivoOptions" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>

          <select v-model="filtroTratamento" class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs">
            <option value="">Todos os tratamentos</option>
            <option value="PENDENTE">Pendente / Ajustado</option>
            <option value="VALIDADO">Validado</option>
            <option value="NEGLIGENCIADO">Negligenciado</option>
          </select>

          <input
            v-model="filtroIdCompra"
            type="text"
            placeholder="Filtrar por ID da compra"
            class="rounded-md border border-gray-200 px-2 py-1.5 text-xs"
          />

          <button
            type="button"
            class="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-black px-3 py-1.5 text-xs text-white hover:bg-gray-500"
            @click="reloadDivergencias(true)"
          >
            <Filter class="h-3.5 w-3.5" />
            Filtrar
          </button>
          <button
            type="button"
            class="rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
            @click="limparFiltros"
          >
            Limpar filtros
          </button>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <button
            type="button"
            class="rounded-md border border-[#03ad12] px-3 py-1.5 text-xs text-[#03ad12] hover:bg-[#d7fce1] disabled:opacity-60"
            :disabled="!selectedRows.length || applyingBatch"
            @click="abrirConfirmacaoLote('validar')"
          >
            {{ applyingBatch ? "Processando..." : "Validar Selecionadas" }}
          </button>
          <button
            type="button"
            class="rounded-md border border-[#a82631] px-3 py-1.5 text-xs text-[#a82631] hover:bg-[#fff5f6] disabled:opacity-60"
            :disabled="!selectedRows.length || applyingBatch"
            @click="abrirConfirmacaoLote('negligenciar')"
          >
            {{ applyingBatch ? "Processando..." : "Negligenciar Selecionadas" }}
          </button>
        </div>
      </div>
    </article>

    <BaseTable
      title="Divergencias de Compras"
      subtitle="Tratamento da reconciliacao STG x SOT"
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
      empty-text="Nenhuma divergencia encontrada para os filtros selecionados."
      @next="goNext"
      @previous="goPrevious"
    >
      <template #header-extra>
        <div class="flex items-center gap-2">
          <span class="rounded-md border border-gray-200 px-2 py-1 text-xs text-gray-600">
            {{ rows.length }} na pagina
          </span>
          <label class="inline-flex items-center gap-1 text-xs text-gray-700">
            <input :checked="allPaginaSelecionada" type="checkbox" @change="toggleSelecionarTodos($event.target.checked)" />
            Selecionar todos da pagina
          </label>
        </div>
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

      <template #cell-compra="{ row }">
        <button type="button" class="font-semibold text-[#373435] hover:underline" @click="abrirAjuste(row)">
          {{ row.compra }}
        </button>
      </template>

      <template #cell-fornecedor="{ row }">
        <div class="space-y-0.5">
          <p class="font-medium text-[#373435]">{{ row.fornecedor_resolvido?.nome_fornecedor || '-' }}</p>
          <p class="text-[11px] text-gray-500">Legado: {{ row.fornecedor_legado?.nome_fornecedor_legado || '-' }}</p>
        </div>
      </template>

      <template #cell-total_compra="{ row }">
        {{ asMoney(row.totais?.total_compra) }}
      </template>

      <template #cell-total_itens="{ row }">
        {{ asMoney(row.totais?.total_itens) }}
      </template>

      <template #cell-diferenca_total="{ row }">
        <span :class="Number(row.totais?.diferenca_total || 0) === 0 ? 'text-[#2f6f4f]' : 'text-[#a82631]'">
          {{ asMoney(row.totais?.diferenca_total) }}
        </span>
      </template>

      <template #cell-motivos="{ row }">
        <div class="flex max-w-[280px] flex-wrap gap-1">
          <span
            v-for="motivo in (row.motivos || []).slice(0, 2)"
            :key="`${row.row_key}-${motivo}`"
            class="inline-flex rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-[11px] text-gray-700"
          >
            {{ formatarMotivo(motivo) }}
          </span>
          <span
            v-if="(row.motivos || []).length > 2"
            class="inline-flex rounded-full border border-gray-200 bg-white px-2 py-0.5 text-[11px] text-gray-500"
          >
            +{{ (row.motivos || []).length - 2 }}
          </span>
        </div>
      </template>

      <template #actions="{ row }">
        <div class="inline-flex items-center gap-2">
          <button
            type="button"
            class="inline-flex items-center gap-1 rounded-md border border-gray-200 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
            @click="abrirAjuste(row)"
          >
            <Pencil class="h-3.5 w-3.5" />
            Ajustar
          </button>
        </div>
      </template>
    </BaseTable>

    <article class="rounded-md border border-gray-200 bg-white p-3 space-y-2">
      <p class="text-xs font-semibold text-gray-700">Consolidacao para tabelas oficiais (SOT)</p>
      <p v-if="canConsolidar" class="text-xs text-gray-600">Tudo consistente. A consolidacao pode ser aprovada.</p>
      <ul v-else class="list-disc pl-4 text-xs text-red-600 space-y-0.5">
        <li v-for="motivo in consolidacaoBloqueios" :key="motivo">{{ motivo }}</li>
      </ul>
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-md bg-[#1f4f8a] px-3 py-2 text-xs font-semibold text-white hover:bg-[#193f6e] disabled:cursor-not-allowed disabled:opacity-70"
        :disabled="consolidando || !canConsolidar"
        @click="abrirConfirmacaoConsolidacao"
      >
        {{ consolidando ? "Consolidando..." : "Aprovar e Inserir no SOT" }}
      </button>

      <div v-if="consolidacaoResult" class="rounded-md border border-green-100 bg-green-50 p-2 text-xs text-green-800">
        <p>Compras inseridas: {{ consolidacaoResult.compras_inseridas || 0 }}</p>
        <p>Ignoradas (duplicadas): {{ consolidacaoResult.compras_ignoradas_duplicadas || 0 }}</p>
        <p>Ignoradas (incompletas): {{ consolidacaoResult.compras_ignoradas_incompletas || 0 }}</p>
      </div>
    </article>

    <ModalAjusteCompraStg
      v-model="showEditModal"
      :row="activeRow"
      :saving="savingEdit"
      @save="salvarAjuste"
    />

    <BaseModal
      v-model="showConfirmModal"
      :title="confirmTitle"
      :description="confirmDescription"
    >
      <template #footer>
        <button
          type="button"
          class="rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50"
          :disabled="confirmRunning"
          @click="showConfirmModal = false"
        >
          Cancelar
        </button>
        <button
          type="button"
          class="rounded-md bg-[#1f4f8a] px-3 py-2 text-xs font-medium text-white hover:bg-[#193f6e] disabled:opacity-60"
          :disabled="confirmRunning"
          @click="executarConfirmacao"
        >
          {{ confirmRunning ? "Processando..." : "Confirmar" }}
        </button>
      </template>
    </BaseModal>

    <BaseModal
      v-model="showBloqueioModal"
      title="Bloqueios identificados"
      :description="bloqueioMensagem"
    >
      <div class="space-y-2">
        <p v-if="bloqueioCodigo" class="text-xs text-gray-600">Codigo: {{ bloqueioCodigo }}</p>
        <ul class="max-h-64 space-y-2 overflow-auto pr-1">
          <li v-for="item in bloqueioItems" :key="`${item.compra}-${item.id_compra_legado}`" class="rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900">
            <p class="font-semibold">{{ item.compra || `COMPRA #${item.id_compra_legado}` }}</p>
            <p>Motivos: {{ formatarCodigos(item.codigos || []) }}</p>
            <p v-if="(item.erros || []).length">Detalhe: {{ (item.erros || []).join(' | ') }}</p>
          </li>
        </ul>
      </div>
      <template #footer>
        <button
          type="button"
          class="rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50"
          @click="showBloqueioModal = false"
        >
          Fechar
        </button>
      </template>
    </BaseModal>

    <div v-if="confirmRunning" class="fixed inset-0 z-[70] bg-black/35">
      <div class="absolute inset-0 flex items-center justify-center p-4">
        <article class="w-full max-w-md rounded-md border border-gray-200 bg-white p-4 shadow-lg">
          <div class="flex items-start gap-3">
            <RefreshCw class="mt-0.5 h-5 w-5 animate-spin text-[#1f4f8a]" />
            <div class="space-y-1">
              <p class="text-sm font-semibold text-[#373435]">Processando solicitacao</p>
              <p class="text-xs text-gray-600">{{ confirmProcessingDescription }}</p>
            </div>
          </div>
        </article>
      </div>
    </div>

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
import {
  Eraser,
  Filter,
  Pencil,
  RefreshCw,
} from "lucide-vue-next";
import BaseModal from "@/components/ui/BaseModal.vue";
import BaseTable from "@/components/ui/BaseTable.vue";
import DateRangeField from "@/components/ui/DateRangeField.vue";
import ModalAjusteCompraStg from "@/pages/Compras/ModalAjusteCompraStg.vue";
import { executarSincronizacaoFirebird, formatarErroSincronizacao, getApiBaseUrl } from "@/services/firebirdSync";

const API_BASE_URL = getApiBaseUrl();

const MOTIVO_LABELS = {
  duplicado_sot: "Duplicado no SOT",
  compra_sem_itens: "Compra sem itens",
  fornecedor_sem_correspondencia: "Fornecedor sem correspondencia",
  produto_sem_correspondencia: "Produto sem correspondencia",
  unidade_sem_mapeamento: "Unidade sem mapeamento",
  divergencia_total_itens: "Divergencia total itens",
  valor_negativo_bloqueado: "Valor negativo bloqueado",
};

const motivoOptions = Object.entries(MOTIVO_LABELS).map(([value, label]) => ({ value, label }));

const kpis = reactive({
  total_compras_stg: 0,
  compras_aprovadas: 0,
  compras_divergentes: 0,
  compras_duplicadas_sot: 0,
  compras_negligenciadas: 0,
  soma_valor_stg: "0",
  motivos_divergencia: {},
  periodo_data_inicial: null,
  periodo_data_final: null,
});

const dataInicial = ref("");
const dataFinal = ref("");
const syncing = ref(false);
const limpandoFluxo = ref(false);
const consolidando = ref(false);
const applyingBatch = ref(false);
const savingEdit = ref(false);

const rows = ref([]);
const loading = ref(false);
const tableError = ref("");
const globalError = ref("");

const count = ref(0);
const next = ref("");
const previous = ref("");
const consolidacaoResult = ref(null);

const filtroMotivo = ref("");
const filtroTratamento = ref("PENDENTE");
const filtroIdCompra = ref("");

const selectedMap = reactive({});

const showEditModal = ref(false);
const activeRow = ref(null);

const showConfirmModal = ref(false);
const confirmTitle = ref("");
const confirmDescription = ref("");
const confirmProcessingDescription = ref("Executando operacao. Aguarde a conclusao...");
const confirmRunning = ref(false);
let confirmAction = null;

const showBloqueioModal = ref(false);
const bloqueioMensagem = ref("");
const bloqueioCodigo = ref("");
const bloqueioItems = ref([]);

const toast = ref("");
let toastTimer = null;

const tableColumns = [
  { key: "select", label: "Sel" },
  { key: "compra", label: "Compra" },
  { key: "fornecedor", label: "Fornecedor" },
  { key: "total_compra", label: "Total Doc." },
  { key: "total_itens", label: "Total Itens" },
  { key: "diferenca_total", label: "Diferenca" },
  { key: "motivos", label: "Motivos" },
];

const selectedRows = computed(() => rows.value.filter((row) => selectedMap[row.row_key]));
const allPaginaSelecionada = computed(() => rows.value.length > 0 && selectedRows.value.length === rows.value.length);
const motivosKpiOrdenados = computed(() => {
  const motivos = kpis.motivos_divergencia || {};
  return Object.keys(motivos)
    .map((codigo) => ({
      codigo,
      label: formatarMotivo(codigo),
      total: Number(motivos[codigo] || 0),
    }))
    .filter((item) => item.total > 0)
    .sort((a, b) => b.total - a.total || a.label.localeCompare(b.label));
});

const canConsolidar = computed(() => {
  return Number(kpis.compras_aprovadas || 0) > 0 && Number(kpis.compras_divergentes || 0) === 0;
});

const consolidacaoBloqueios = computed(() => {
  const bloqueios = [];
  if (Number(kpis.compras_aprovadas || 0) <= 0) {
    bloqueios.push("Nao ha compras aprovadas para consolidar.");
  }
  if (Number(kpis.compras_divergentes || 0) > 0) {
    bloqueios.push("Ainda existem compras divergentes pendentes de tratamento.");
  }
  return bloqueios;
});

function asMoney(value) {
  return Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatDateBr(value) {
  if (!value) {
    return "-";
  }

  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) {
    return String(value);
  }

  return `${match[3]}/${match[2]}/${match[1]}`;
}

function notify(message) {
  toast.value = String(message || "");
  if (toastTimer) {
    clearTimeout(toastTimer);
  }
  toastTimer = setTimeout(() => {
    toast.value = "";
    toastTimer = null;
  }, 3000);
}

function formatarMotivo(codigo) {
  return MOTIVO_LABELS[String(codigo || "").trim()] || String(codigo || "-");
}

function formatarCodigos(codigos) {
  const list = (codigos || []).map((codigo) => formatarMotivo(codigo));
  return list.length ? list.join(", ") : "-";
}

function rowHighlightClass(row) {
  const norm = String(row?.tratamento || "").toUpperCase();
  if (norm === "VALIDADO") return "bg-[#f3fbf6]";
  if (norm === "NEGLIGENCIADO") return "bg-[#fff7f8]";
  return "";
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
  selectedMap[row.row_key] = !Boolean(selectedMap[row.row_key]);
}

function toggleSelecionarTodos(checked) {
  rows.value.forEach((row) => {
    selectedMap[row.row_key] = Boolean(checked);
  });
}

function applyKpis(data) {
  kpis.total_compras_stg = Number(data.total_compras_stg || 0);
  kpis.compras_aprovadas = Number(data.compras_aprovadas || 0);
  kpis.compras_divergentes = Number(data.compras_divergentes || 0);
  kpis.compras_duplicadas_sot = Number(data.compras_duplicadas_sot || 0);
  kpis.compras_negligenciadas = Number(data.compras_negligenciadas || 0);
  kpis.soma_valor_stg = data.soma_valor_stg || "0";
  kpis.motivos_divergencia = data.motivos_divergencia || {};
  kpis.periodo_data_inicial = data.periodo_data_inicial || null;
  kpis.periodo_data_final = data.periodo_data_final || null;
}

function resetKpis() {
  applyKpis({});
}

function parseApiError(payload, statusCode) {
  return {
    message: String(payload?.detail || `Erro ${statusCode}`).trim(),
    codigo: String(payload?.codigo || "").trim(),
    bloqueios: Array.isArray(payload?.bloqueios) ? payload.bloqueios : [],
  };
}

async function requestJson(url, options = {}, timeoutMs = 90000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    const payload = await response.json().catch(() => ({}));
    return { response, payload };
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error("Tempo limite excedido ao aguardar resposta do servidor.");
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function abrirBloqueioModal({ mensagem, codigo, bloqueios }) {
  bloqueioMensagem.value = mensagem || "Operacao bloqueada por inconsistencias estruturais.";
  bloqueioCodigo.value = codigo || "";
  bloqueioItems.value = Array.isArray(bloqueios) ? bloqueios : [];
  showBloqueioModal.value = true;
}

function buildUrl(url = "") {
  const target = new URL(url || `${API_BASE_URL}/api/compras/reconciliacao/divergencias`);

  if (filtroMotivo.value) {
    target.searchParams.set("motivo", filtroMotivo.value);
  } else {
    target.searchParams.delete("motivo");
  }

  if (filtroTratamento.value) {
    target.searchParams.set("tratamento", filtroTratamento.value);
  } else {
    target.searchParams.delete("tratamento");
  }

  if (String(filtroIdCompra.value || "").trim()) {
    target.searchParams.set("id_compra_legado", String(filtroIdCompra.value).trim());
  } else {
    target.searchParams.delete("id_compra_legado");
  }

  return target.toString();
}

async function loadDivergencias(url = "") {
  loading.value = true;
  tableError.value = "";

  try {
    const { response, payload } = await requestJson(buildUrl(url));
    if (!response.ok) {
      throw new Error(payload.detail || `Erro ${response.status}`);
    }

    const result = payload.results || {};
    rows.value = (result.rows || []).map((row) => ({
      ...row,
      row_key: String(row.id_compra_legado),
    }));

    count.value = Number(payload.count || 0);
    next.value = payload.next || "";
    previous.value = payload.previous || "";
    applyKpis(result.kpis || {});
    clearSelection();
  } catch (err) {
    console.error(err);
    tableError.value = err?.message || "Falha ao carregar divergencias de compras.";
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

function limparFiltros() {
  filtroMotivo.value = "";
  filtroTratamento.value = "PENDENTE";
  filtroIdCompra.value = "";
  reloadDivergencias(true);
}

function openConfirm({ title, description, onConfirm, processingDescription }) {
  confirmTitle.value = title;
  confirmDescription.value = description;
  confirmProcessingDescription.value =
    String(processingDescription || "").trim() || "Executando operacao. Aguarde a conclusao...";
  confirmAction = onConfirm;
  showConfirmModal.value = true;
}

async function executarConfirmacao() {
  if (typeof confirmAction !== "function") {
    showConfirmModal.value = false;
    return;
  }

  confirmRunning.value = true;
  try {
    showConfirmModal.value = false;
    await confirmAction();
  } finally {
    confirmRunning.value = false;
    confirmAction = null;
  }
}

async function sincronizarCompras() {
  globalError.value = "";
  if (!dataInicial.value || !dataFinal.value) {
    globalError.value = "Informe data inicial e data final para sincronizar compras.";
    return;
  }

  syncing.value = true;
  try {
    const { payload } = await executarSincronizacaoFirebird(`${API_BASE_URL}/api/compras/sincronizar-firebird`, {
      data_inicial: dataInicial.value,
      data_final: dataFinal.value,
    }, {
      allowBrowserUploadFallback: false,
    });

    applyKpis(payload.kpis || {});
    consolidacaoResult.value = null;
    await reloadDivergencias(true);
    notify("Sincronizacao de compras concluida com sucesso.");
  } catch (err) {
    console.error(err);
    globalError.value = formatarErroSincronizacao(err, "Falha ao sincronizar compras do legado.");
  } finally {
    syncing.value = false;
  }
}

async function tratarCompra(row, acao, payload = {}) {
  const response = await fetch(`${API_BASE_URL}/api/compras/reconciliacao/divergencias/tratar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      id_compra_legado: row.id_compra_legado,
      acao,
      payload,
    }),
  });

  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const erro = parseApiError(result, response.status);
    if (erro.bloqueios.length) {
      abrirBloqueioModal({ mensagem: erro.message, codigo: erro.codigo, bloqueios: erro.bloqueios });
    }
    throw new Error(erro.message);
  }

  applyKpis(result.kpis || {});
  await reloadDivergencias(false);
  notify("Ajuste da compra aplicado com sucesso.");
}

function abrirAjuste(row) {
  activeRow.value = row;
  showEditModal.value = true;
}

async function salvarAjuste(payload) {
  if (!activeRow.value) {
    return;
  }

  savingEdit.value = true;
  globalError.value = "";
  try {
    await tratarCompra(activeRow.value, "ajustar", payload);
    showEditModal.value = false;
  } catch (err) {
    console.error(err);
    globalError.value = err?.message || "Falha ao salvar ajuste da compra.";
  } finally {
    savingEdit.value = false;
  }
}

async function aplicarLote(acao) {
  if (!selectedRows.value.length) {
    return;
  }

  applyingBatch.value = true;
  globalError.value = "";
  try {
    const response = await fetch(`${API_BASE_URL}/api/compras/reconciliacao/divergencias/tratar-lote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        acao,
        compras: selectedRows.value.map((row) => ({ id_compra_legado: row.id_compra_legado })),
      }),
    });

    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      const erro = parseApiError(result, response.status);
      if (erro.bloqueios.length) {
        abrirBloqueioModal({ mensagem: erro.message, codigo: erro.codigo, bloqueios: erro.bloqueios });
      }
      throw new Error(erro.message);
    }

    if (Number(result.bloqueadas || 0) > 0 && Array.isArray(result.bloqueios) && result.bloqueios.length) {
      abrirBloqueioModal({
        mensagem: `Tratamento em lote bloqueou ${result.bloqueadas} compra(s).`,
        codigo: "tratamento_lote_bloqueado",
        bloqueios: result.bloqueios,
      });
    }

    applyKpis(result.kpis || {});
    await reloadDivergencias(false);
    notify(result.detail || "Tratamento em lote concluido.");
  } catch (err) {
    console.error(err);
    globalError.value = err?.message || "Falha no tratamento em lote.";
  } finally {
    applyingBatch.value = false;
  }
}

function abrirConfirmacaoLote(acao) {
  const total = selectedRows.value.length;
  if (!total) {
    return;
  }

  const verbo = acao === "validar" ? "validar" : "negligenciar";
  openConfirm({
    title: "Confirmar lote",
    description: `Deseja realmente ${verbo} ${total} compra(s) selecionada(s)?`,
    processingDescription: "Aplicando tratamento em lote nas compras selecionadas. Aguarde...",
    onConfirm: () => aplicarLote(acao),
  });
}

async function consolidarCompras() {
  consolidando.value = true;
  globalError.value = "";

  try {
    const response = await fetch(`${API_BASE_URL}/api/compras/consolidar-sot`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });

    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      const erro = parseApiError(result, response.status);
      if (erro.bloqueios.length) {
        abrirBloqueioModal({ mensagem: erro.message, codigo: erro.codigo, bloqueios: erro.bloqueios });
      }
      throw new Error(erro.message);
    }

    consolidacaoResult.value = result.resultado || null;
    notify(result.detail || "Consolidacao de compras concluida.");
    await reloadDivergencias(true);
  } catch (err) {
    console.error(err);
    globalError.value = err?.message || "Falha ao consolidar compras para o SOT.";
  } finally {
    consolidando.value = false;
  }
}

function abrirConfirmacaoConsolidacao() {
  if (Number(kpis.compras_aprovadas || 0) <= 0) {
    return;
  }

  openConfirm({
    title: "Confirmar consolidacao",
    description: "Deseja consolidar as compras aprovadas da STG para o SOT?",
    processingDescription: "Consolidando compras aprovadas para o SOT. Aguarde...",
    onConfirm: consolidarCompras,
  });
}

async function limparFluxo() {
  limpandoFluxo.value = true;
  globalError.value = "";

  try {
    const response = await fetch(`${API_BASE_URL}/api/compras/reconciliacao/limpar-fluxo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `Erro ${response.status}`);
    }

    rows.value = [];
    count.value = 0;
    next.value = "";
    previous.value = "";
    clearSelection();
    resetKpis();
    consolidacaoResult.value = null;
    notify("Fluxo de reconciliacao de compras limpo com sucesso.");
  } catch (err) {
    console.error(err);
    globalError.value = err?.message || "Falha ao limpar fluxo de compras.";
  } finally {
    limpandoFluxo.value = false;
  }
}

function abrirConfirmacaoLimpeza() {
  openConfirm({
    title: "Limpar fluxo de compras",
    description: "Deseja realmente remover os dados temporarios de compras (STG)?",
    processingDescription: "Limpando dados temporarios do fluxo de compras. Aguarde...",
    onConfirm: limparFluxo,
  });
}

function setDefaultDates() {
  if (dataInicial.value && dataFinal.value) {
    return;
  }

  const today = new Date();
  const end = formatDateInput(today);

  const startDate = new Date(today);
  startDate.setDate(today.getDate() - 30);
  const start = formatDateInput(startDate);

  dataInicial.value = dataInicial.value || start;
  dataFinal.value = dataFinal.value || end;
}

function formatDateInput(date) {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

onMounted(async () => {
  setDefaultDates();
  await reloadDivergencias(true);
});

onBeforeUnmount(() => {
  if (toastTimer) {
    clearTimeout(toastTimer);
  }
});
</script>
