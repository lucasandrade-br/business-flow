<template>
  <BaseModal
    v-model="open"
    :title="`Produto ${produto?.id_produto ?? ''}`"
    description="Preencha os campos obrigatorios e, se desejar, vincule categorias por raiz."
  >
    <div v-if="!produto" class="text-sm text-gray-500">Nenhum produto selecionado.</div>

    <div v-else class="space-y-4">
      <section class="grid gap-3 rounded-md border border-gray-200 p-3 lg:grid-cols-2">
        <div class="space-y-1">
          <BaseInput
            v-model="form.nome"
            label="Produto"
            readonly
            :input-class="isCampoDivergente('nome', form.nome, normalizeString) ? 'bg-yellow-50 border-yellow-300 text-yellow-900' : ''"
          />
          <p
            v-if="isCampoDivergente('nome', form.nome, normalizeString)"
            class="text-[11px] text-yellow-800"
          >
            Atualmente: {{ valorSotTexto('nome') }}
          </p>
        </div>
        <div>
          <p class="inline-flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-gray-500">
            ID
            <span class="text-red-500">*</span>
          </p>
          <p class="mt-1 text-sm text-[#373435]">{{ produto.id_produto }}</p>
        </div>
        <div class="space-y-1">
          <BaseInput
            v-model="form.gtin"
            label="GTIN"
            readonly
            :input-class="isCampoDivergente('gtin', form.gtin, normalizeString) ? 'bg-yellow-50 border-yellow-300 text-yellow-900' : ''"
          />
          <p
            v-if="isCampoDivergente('gtin', form.gtin, normalizeString)"
            class="text-[11px] text-yellow-800"
          >
            Atualmente: {{ valorSotTexto('gtin') }}
          </p>
        </div>
        <div class="space-y-1">
          <BaseInput
            v-model="form.barras"
            label="Codigo de Barras"
            readonly
            :input-class="isCampoDivergente('barras', form.barras, normalizeString) ? 'bg-yellow-50 border-yellow-300 text-yellow-900' : ''"
          />
          <p
            v-if="isCampoDivergente('barras', form.barras, normalizeString)"
            class="text-[11px] text-yellow-800"
          >
            Atualmente: {{ valorSotTexto('barras') }}
          </p>
        </div>
      </section>

      <section class="grid gap-3 lg:grid-cols-3">
        <label class="space-y-1 text-xs">
          <span class="inline-flex items-center gap-1 font-medium text-gray-600">
            Status
            <span class="text-red-500">*</span>
            <span class="group relative inline-flex items-center">
              <HelpCircle class="h-4 w-4 text-gray-400" />
              <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-56 -translate-x-1/2 rounded-md bg-[#1f1f1f] px-2 py-1 text-[11px] font-normal text-white group-hover:block">
                Status obrigatorio para aprovar o produto
              </span>
            </span>
          </span>
          <button
            type="button"
            :class="[
              'inline-flex w-full items-center justify-between rounded-md border px-3 py-2',
              isCampoDivergente('status', statusComoTexto(form.status), normalizeStatusLabel)
                ? 'bg-yellow-50 border-yellow-300 text-yellow-900'
                : 'border-gray-200',
            ]"
            @click="form.status = !form.status"
          >
            <span class="text-sm font-medium" :class="form.status ? 'text-green-700' : 'text-gray-500'">
              {{ form.status ? "ATIVO" : "INATIVO" }}
            </span>
            <span class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors" :class="form.status ? 'bg-green-500' : 'bg-gray-300'">
              <span class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform" :class="form.status ? 'translate-x-6' : 'translate-x-1'" />
            </span>
          </button>
          <p
            v-if="isCampoDivergente('status', statusComoTexto(form.status), normalizeStatusLabel)"
            class="text-[11px] text-yellow-800"
          >
            Atualmente: {{ valorSotTexto('status', normalizeStatusLabel) }}
          </p>
        </label>
        <div class="space-y-1">
          <label class="space-y-1 text-xs">
            <span class="inline-flex items-center gap-1 font-medium text-gray-600">
              Und. Medida
              <span class="text-red-500">*</span>
              <span class="group relative inline-flex items-center">
                <HelpCircle class="h-4 w-4 text-gray-400" />
                <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-56 -translate-x-1/2 rounded-md bg-[#1f1f1f] px-2 py-1 text-[11px] font-normal text-white group-hover:block">
                  Unidade de medida obrigatoria para aprovacao
                </span>
              </span>
            </span>
            <select
              v-model="form.id_und_medida"
              required
              :class="[
                'w-full rounded-md border bg-white px-3 py-2 text-sm',
                isCampoDivergente('id_und_medida', form.id_und_medida, normalizeNumber) ? 'border-yellow-300 bg-yellow-50 text-yellow-900' : 'border-gray-200',
              ]"
            >
              <option value="">Selecione</option>
              <option v-for="option in unidadesOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
          <p
            v-if="isCampoDivergente('id_und_medida', form.id_und_medida, normalizeNumber)"
            class="text-[11px] text-yellow-800"
          >
            Atualmente: {{ valorSotTexto('id_und_medida') }}
          </p>
        </div>
        <div class="space-y-1">
          <CurrencyInput
            v-model="form.custo"
            label="Custo"
            required
            help-text="Valor de custo obrigatorio para aprovacao"
            :input-class="isCampoDivergente('custo', form.custo, normalizeNumber) ? 'bg-yellow-50 border-yellow-300 text-yellow-900' : ''"
          />
          <p
            v-if="isCampoDivergente('custo', form.custo, normalizeNumber)"
            class="text-[11px] text-yellow-800"
          >
            Atualmente: {{ valorSotMonetario('custo') }}
          </p>
        </div>
        <div class="space-y-1">
          <CurrencyInput
            v-model="form.valor_venda"
            label="Venda"
            required
            help-text="Valor de venda obrigatorio para aprovacao"
            :input-class="isCampoDivergente('valor_venda', form.valor_venda, normalizeNumber) ? 'bg-yellow-50 border-yellow-300 text-yellow-900' : ''"
          />
          <p
            v-if="isCampoDivergente('valor_venda', form.valor_venda, normalizeNumber)"
            class="text-[11px] text-yellow-800"
          >
            Atualmente: {{ valorSotMonetario('valor_venda') }}
          </p>
        </div>
        <label class="space-y-1 text-xs">
          <span class="font-medium text-gray-600">Markup</span>
          <PercentInput v-model="form.markup" />
        </label>
        <label class="space-y-1 text-xs">
          <span class="font-medium text-gray-600">Markup Inv</span>
          <PercentInput v-model="form.markup_inv" />
        </label>
        <label class="space-y-1 text-xs">
          <span class="font-medium text-gray-600">Perda</span>
          <PercentInput v-model="form.perda" />
        </label>
        <label class="space-y-1 text-xs">
          <span class="font-medium text-gray-600">Fisico</span>
          <input
            v-model="form.fisico"
            type="text"
            inputmode="decimal"
            class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm"
            @input="form.fisico = normalizeDecimalInput(form.fisico, 4)"
          />
        </label>
        <label class="space-y-1 text-xs">
          <span class="font-medium text-gray-600">AliqEFC</span>
          <select v-model="form.aliqefc" class="w-full appearance-none rounded-md border border-gray-200 bg-white px-3 py-2 text-sm">
            <option value="">Selecione</option>
            <option v-for="option in aliquotasOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <label class="space-y-1 text-xs">
          <span class="font-medium text-gray-600">Cod G3N</span>
          <input v-model="form.cod_g3n" type="number" class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm" />
        </label>
        <label class="space-y-1 text-xs">
          <span class="font-medium text-gray-600">Cod Rel</span>
          <input v-model="form.cod_rel" type="number" class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm" />
        </label>
        <label class="space-y-1 text-xs lg:col-span-2">
          <span class="font-medium text-gray-600">Usuario</span>
          <input v-model="form.usuario" type="text" class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm" />
        </label>
      </section>

      <section class="rounded-md border border-gray-200 p-3">
        <h4 class="text-xs font-semibold uppercase tracking-wide text-gray-500">Categorias por raiz (opcional)</h4>
        <p v-if="treeLoading" class="mt-2 text-xs text-gray-500">Carregando arvore...</p>
        <p v-else-if="treeError" class="mt-2 text-xs text-red-600">{{ treeError }}</p>
        <div v-else class="mt-3 grid gap-3 lg:grid-cols-2">
          <div v-for="root in roots" :key="root.id_conta" class="space-y-1">
            <label class="text-xs font-medium text-gray-600">{{ root.nome_conta }}</label>
            <select
              v-model="selectedByRoot[root.id_conta]"
              class="w-full appearance-none rounded-md border border-gray-200 bg-white px-3 py-2 text-sm"
            >
              <option value="">Selecione uma subcategoria</option>
              <option v-for="child in flattenCategorias(root)" :key="child.id_conta" :value="String(child.id_conta)">
                {{ child.label }}
              </option>
            </select>
          </div>
        </div>
      </section>

      <p v-if="error" class="text-xs text-red-600">{{ error }}</p>
    </div>

    <template #footer>
      <button
        type="button"
        class="rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50"
        @click="open = false"
      >
        Cancelar
      </button>
      <button
        type="button"
        class="rounded-md bg-[#a82631] px-3 py-2 text-xs font-medium text-white hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="saving"
        @click="save"
      >
        {{ saving ? "Salvando..." : "Aprovar" }}
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { HelpCircle } from "lucide-vue-next";
import BaseInput from "@/components/ui/BaseInput.vue";
import BaseModal from "@/components/ui/BaseModal.vue";
import CurrencyInput from "@/components/ui/CurrencyInput.vue";
import PercentInput from "@/components/ui/PercentInput.vue";

const API_BASE_URL = "http://127.0.0.1:8000";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  produto: { type: Object, default: null },
});

const emit = defineEmits(["update:modelValue", "approved"]);

const treeLoading = ref(false);
const treeError = ref("");
const saving = ref(false);
const error = ref("");
const roots = ref([]);
const unidadesOptions = ref([]);
const aliquotasOptions = ref([]);

const form = reactive({
  nome: "",
  gtin: "",
  barras: "",
  status: true,
  id_und_medida: "",
  custo: 0,
  valor_venda: 0,
  markup: 0,
  markup_inv: 0,
  perda: 0,
  fisico: "0,0000",
  aliqefc: "",
  cod_g3n: "",
  cod_rel: "",
  usuario: "",
});

const selectedByRoot = reactive({});

const open = computed({
  get: () => props.modelValue,
  set: (value) => emit("update:modelValue", value),
});

watch(
  () => props.modelValue,
  async (value) => {
    if (value) {
      await Promise.all([fetchTree(), fetchUnidades(), fetchAliquotas()]);
      hydrateFormFromProduto();
    }
  },
);

function numberOrZero(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function normalizeDecimalInput(value, maxDecimals = 4) {
  const clean = String(value || "").replace(/[^\d,]/g, "");
  const parts = clean.split(",");
  if (parts.length === 1) return parts[0];
  return `${parts[0]},${parts.slice(1).join("").slice(0, maxDecimals)}`;
}

function parseLocaleDecimal(value) {
  const parsed = Number(String(value || "").replace(/\./g, "").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

function flattenCategorias(root) {
  const result = [];

  function visit(nodes, depth) {
    for (const node of nodes || []) {
      const prefix = depth > 0 ? `${"\u00A0\u00A0".repeat(depth)}\u2514\u2500 ` : "";
      result.push({
        id_conta: node.id_conta,
        label: `${prefix}${node.codigo_hierarquico} ${node.nome_conta}`,
      });
      visit(node.filhas, depth + 1);
    }
  }

  visit(root.filhas || [], 0);
  return result;
}

function resetForm() {
  form.nome = "";
  form.gtin = "";
  form.barras = "";
  form.status = true;
  form.id_und_medida = "";
  form.custo = 0;
  form.valor_venda = 0;
  form.markup = 0;
  form.markup_inv = 0;
  form.perda = 0;
  form.fisico = "0,0000";
  form.aliqefc = "";
  form.cod_g3n = "";
  form.cod_rel = "";
  form.usuario = "";
  error.value = "";

  for (const key of Object.keys(selectedByRoot)) {
    delete selectedByRoot[key];
  }
}

function normalizeString(value) {
  return String(value || "").trim();
}

function normalizeStatus(value) {
  return normalizeString(value).toUpperCase();
}

function normalizeStatusLabel(value) {
  const status = normalizeStatus(value);
  if (status === "1" || status === "A" || status === "ATIVO") return "ATIVO";
  if (status === "0" || status === "I" || status === "INATIVO") return "INATIVO";
  return status;
}

function normalizeNumber(value) {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) ? parsed.toFixed(6) : "0.000000";
}

function statusComoTexto(statusBoolean) {
  return statusBoolean ? "ATIVO" : "INATIVO";
}

function isAtualizacao() {
  return props.produto?.tipo_pendencia === "ATUALIZACAO" && !!props.produto?.dados_sot;
}

function isCampoDivergente(campo, valorAtual, normalizer = (valor) => valor) {
  if (!isAtualizacao()) {
    return false;
  }
  const dados = props.produto?.dados_sot || {};
  const valorSot = dados[campo];
  return normalizer(valorAtual) !== normalizer(valorSot);
}

function valorSotTexto(campo, normalizer = (valor) => valor) {
  const dados = props.produto?.dados_sot || {};
  const valor = dados[campo];
  if (valor === null || valor === undefined || String(valor).trim() === "") {
    return "-";
  }
  return String(normalizer(valor));
}

function valorSotMonetario(campo) {
  const dados = props.produto?.dados_sot || {};
  return Number(dados[campo] || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function applyCategoriasToRoots(categoriasIds = []) {
  const desired = new Set(
    (categoriasIds || [])
      .map((id) => Number(id))
      .filter((id) => Number.isFinite(id) && id > 0),
  );

  for (const root of roots.value) {
    selectedByRoot[root.id_conta] = "";
    const match = flattenCategorias(root).find((child) => desired.has(Number(child.id_conta)));
    if (match) {
      selectedByRoot[root.id_conta] = String(match.id_conta);
    }
  }
}

function hydrateFormFromProduto() {
  if (!props.produto) {
    resetForm();
    return;
  }

  const sugeridaId = props.produto.unidade_sugerida_id ?? "";
  const stagedCusto = Number(props.produto.custo || 0);
  const stagedVenda = Number(props.produto.valor_venda || 0);

  if (props.produto.tipo_pendencia === "ATUALIZACAO" && props.produto.dados_sot) {
    const dados = props.produto.dados_sot;
    form.nome = props.produto.nome || "";
    form.gtin = props.produto.gtin || "";
    form.barras = props.produto.barras || "";
    form.id_und_medida = dados.id_und_medida || sugeridaId;
    form.status = normalizeStatusLabel(props.produto.status) !== "INATIVO";
    form.custo = stagedCusto;
    form.valor_venda = stagedVenda;
    form.markup = dados.markup ?? 0;
    form.markup_inv = dados.markup_inv ?? 0;
    form.perda = dados.perda ?? 0;
    form.fisico = Number(dados.fisico ?? 0).toLocaleString("pt-BR", { minimumFractionDigits: 4, maximumFractionDigits: 4 });
    form.aliqefc = dados.aliqefc ?? "";
    form.cod_g3n = dados.cod_g3n ?? "";
    form.cod_rel = dados.cod_rel ?? "";
    form.usuario = dados.usuario ?? "";

    applyCategoriasToRoots(dados.categorias_ids || []);
    return;
  }

  resetForm();
  form.nome = props.produto.nome || "";
  form.gtin = props.produto.gtin || "";
  form.barras = props.produto.barras || "";
  form.id_und_medida = sugeridaId;
  form.status = normalizeStatusLabel(props.produto.status) !== "INATIVO";
  form.custo = stagedCusto;
  form.valor_venda = stagedVenda;
}

async function fetchTree() {
  treeLoading.value = true;
  treeError.value = "";

  try {
    const response = await fetch(`${API_BASE_URL}/api/cadastros/plano-contas/arvore`);
    if (!response.ok) {
      throw new Error(`Erro ${response.status}`);
    }

    const data = await response.json();
    roots.value = Array.isArray(data) ? data : [];

    for (const root of roots.value) {
      selectedByRoot[root.id_conta] = "";
    }
  } catch (err) {
    console.error(err);
    treeError.value = "Nao foi possivel carregar a arvore de plano de contas.";
  } finally {
    treeLoading.value = false;
  }
}

async function fetchUnidades() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/cadastros/unidades-medida`);
    if (!response.ok) {
      throw new Error(`Erro ${response.status}`);
    }

    const data = await response.json();
    unidadesOptions.value = (data.results || []).map((item) => ({
      value: item.id_und_medida,
      label: `${item.sigla} - ${item.descricao}`,
    }));
  } catch (err) {
    console.error(err);
    unidadesOptions.value = [];
  }
}

async function fetchAliquotas() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/cadastros/aliquotas`);
    if (!response.ok) {
      throw new Error(`Erro ${response.status}`);
    }

    const data = await response.json();
    aliquotasOptions.value = (data.results || []).map((item) => ({
      value: item.descricao || String(item.valor_percentual || ""),
      label: item.descricao || `${item.valor_percentual}%`,
    }));
  } catch (err) {
    console.error(err);
    aliquotasOptions.value = [];
  }
}

function buildPayload() {
  const categorias_ids = Object.values(selectedByRoot)
    .filter((id) => id !== "")
    .map((id) => Number(id))
    .filter((id) => Number.isFinite(id) && id > 0);

  return {
    id_produto: props.produto.id_produto,
    nome: String(form.nome || "").trim(),
    gtin: String(form.gtin || "").trim(),
    barras: String(form.barras || "").trim(),
    status: form.status ? "ATIVO" : "INATIVO",
    ult_mov: props.produto.dt_ultimo_movimento || null,
    custo: numberOrZero(form.custo),
    valor_venda: numberOrZero(form.valor_venda),
    id_und_medida: numberOrZero(form.id_und_medida),
    markup: numberOrZero(form.markup),
    markup_inv: numberOrZero(form.markup_inv),
    perda: numberOrZero(form.perda),
    categorias_ids,
    fisico: parseLocaleDecimal(form.fisico),
    aliqefc: String(form.aliqefc || ""),
    cod_g3n: numberOrZero(form.cod_g3n),
    cod_rel: numberOrZero(form.cod_rel),
    usuario: String(form.usuario || ""),
  };
}

async function save() {
  if (!props.produto) {
    return;
  }

  error.value = "";
  const payload = buildPayload();

  saving.value = true;

  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/produtos/aprovar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || `Erro ${response.status}`);
    }

    emit("approved");
    open.value = false;
  } catch (err) {
    console.error(err);
    error.value = "Falha ao aprovar produto.";
  } finally {
    saving.value = false;
  }
}
</script>
