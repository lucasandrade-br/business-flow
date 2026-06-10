<template>
  <BaseModal
    v-model="open"
    :title="`Cliente ${cliente?.id_cliente ?? ''}`"
    description="Confirme os dados e complete os campos de cadastro oficial."
  >
    <div v-if="!cliente" class="text-sm text-gray-500">Nenhum cliente selecionado.</div>

    <div v-else class="space-y-4">
      <section class="grid gap-3 rounded-md border border-gray-200 p-3 lg:grid-cols-2">
        <div class="space-y-1">
          <BaseInput
            v-model="form.nome_cliente"
            label="Cliente"
            readonly
            :input-class="isCampoDivergente('nome_cliente', form.nome_cliente, normalizeString) ? 'bg-yellow-50 border-yellow-300 text-yellow-900' : ''"
          />
          <p v-if="isCampoDivergente('nome_cliente', form.nome_cliente, normalizeString)" class="text-[11px] text-yellow-800">
            Atualmente: {{ valorSotTexto('nome_cliente') }}
          </p>
        </div>
        <div>
          <p class="text-xs font-medium uppercase tracking-wide text-gray-500">ID</p>
          <p class="mt-1 text-sm text-[#373435]">{{ cliente.id_cliente }}</p>
        </div>
        <div class="space-y-1 lg:col-span-2">
          <BaseInput
            v-model="form.raz_social"
            label="Razao Social"
            readonly
            :input-class="isCampoDivergente('raz_social', form.raz_social, normalizeString) ? 'bg-yellow-50 border-yellow-300 text-yellow-900' : ''"
          />
          <p v-if="isCampoDivergente('raz_social', form.raz_social, normalizeString)" class="text-[11px] text-yellow-800">
            Atualmente: {{ valorSotTexto('raz_social') }}
          </p>
        </div>
      </section>

      <section class="grid gap-3 lg:grid-cols-3">
        <div class="space-y-1">
          <label class="space-y-1 text-xs">
            <span class="inline-flex items-center gap-1 font-medium text-gray-600">
              Prazo Cobranca
              <span class="text-red-500">*</span>
              <span class="group relative inline-flex items-center">
                <HelpCircle class="h-4 w-4 text-gray-400" />
                <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-56 -translate-x-1/2 rounded-md bg-[#1f1f1f] px-2 py-1 text-[11px] font-normal text-white group-hover:block">
                  Prazo em dias para cobranca do cliente
                </span>
              </span>
            </span>
            <input
              v-model="form.prazo_cob"
              type="number"
              :class="[
                'w-full rounded-md border px-3 py-2 text-sm',
                isCampoDivergente('prazo_cob', form.prazo_cob, normalizeNumber) ? 'border-yellow-300 bg-yellow-50 text-yellow-900' : 'border-gray-200',
              ]"
            />
          </label>
          <p v-if="isCampoDivergente('prazo_cob', form.prazo_cob, normalizeNumber)" class="text-[11px] text-yellow-800">
            Atualmente: {{ valorSotTexto('prazo_cob') }}
          </p>
        </div>

        <div class="space-y-1">
          <label class="space-y-1 text-xs">
            <span class="inline-flex items-center gap-1 font-medium text-gray-600">
              Grupo
              <span class="group relative inline-flex items-center">
                <HelpCircle class="h-4 w-4 text-gray-400" />
                <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-56 -translate-x-1/2 rounded-md bg-[#1f1f1f] px-2 py-1 text-[11px] font-normal text-white group-hover:block">
                  Classificacao comercial do cliente
                </span>
              </span>
            </span>
            <select
              v-model="form.id_grupo"
              :class="[
                'w-full appearance-none rounded-md border bg-white px-3 py-2 text-sm',
                isCampoDivergente('id_grupo', form.id_grupo, normalizeNumber) ? 'border-yellow-300 bg-yellow-50 text-yellow-900' : 'border-gray-200',
              ]"
            >
              <option value="">Selecione</option>
              <option v-for="option in gruposOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
          <p v-if="isCampoDivergente('id_grupo', form.id_grupo, normalizeNumber)" class="text-[11px] text-yellow-800">
            Atualmente: {{ valorSotTexto('id_grupo') }}
          </p>
        </div>

        <div class="space-y-1">
          <label class="space-y-1 text-xs">
            <span class="inline-flex items-center gap-1 font-medium text-gray-600">
              Tipo de Venda
              <span class="group relative inline-flex items-center">
                <HelpCircle class="h-4 w-4 text-gray-400" />
                <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-56 -translate-x-1/2 rounded-md bg-[#1f1f1f] px-2 py-1 text-[11px] font-normal text-white group-hover:block">
                  Define a modalidade de venda para o cliente
                </span>
              </span>
            </span>
            <select
              v-model="form.id_tipo_venda"
              :class="[
                'w-full appearance-none rounded-md border bg-white px-3 py-2 text-sm',
                isCampoDivergente('id_tipo_venda', form.id_tipo_venda, normalizeNumber) ? 'border-yellow-300 bg-yellow-50 text-yellow-900' : 'border-gray-200',
              ]"
            >
              <option value="">Selecione</option>
              <option v-for="option in tiposVendaOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
          <p v-if="isCampoDivergente('id_tipo_venda', form.id_tipo_venda, normalizeNumber)" class="text-[11px] text-yellow-800">
            Atualmente: {{ valorSotTexto('id_tipo_venda') }}
          </p>
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

const API_BASE_URL = "http://127.0.0.1:8000";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  cliente: { type: Object, default: null },
});

const emit = defineEmits(["update:modelValue", "approved"]);

const saving = ref(false);
const error = ref("");
const gruposOptions = ref([]);
const tiposVendaOptions = ref([]);

const form = reactive({
  nome_cliente: "",
  raz_social: "",
  prazo_cob: 0,
  id_grupo: "",
  id_tipo_venda: "",
});

const open = computed({
  get: () => props.modelValue,
  set: (value) => emit("update:modelValue", value),
});

watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      hydrateForm();
      error.value = "";
      Promise.all([fetchGrupos(), fetchTiposVenda()]).catch((err) => console.error(err));
    }
  },
);

function normalizeString(value) {
  return String(value || "").trim();
}

function normalizeNumber(value) {
  if (value === "" || value === null || value === undefined) {
    return "";
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? String(parsed) : "";
}

function isAtualizacao() {
  return props.cliente?.tipo_pendencia === "ATUALIZACAO" && !!props.cliente?.dados_sot;
}

function isCampoDivergente(campo, valorAtual, normalizer = (value) => value) {
  if (!isAtualizacao()) {
    return false;
  }
  const dados = props.cliente?.dados_sot || {};
  const valorSot = campo === "nome_cliente" ? (dados.nome_cliente ?? dados.cliente) : dados[campo];
  return normalizer(valorAtual) !== normalizer(valorSot);
}

function valorSotTexto(campo) {
  const dados = props.cliente?.dados_sot || {};
  const valor = campo === "nome_cliente" ? (dados.nome_cliente ?? dados.cliente) : dados[campo];
  if (valor === null || valor === undefined || String(valor).trim() === "") {
    return "-";
  }
  return String(valor);
}

function hydrateForm() {
  form.nome_cliente = String(props.cliente?.nome_cliente || "");
  form.raz_social = String(props.cliente?.raz_social || "");

  if (isAtualizacao()) {
    const dados = props.cliente?.dados_sot || {};
    form.prazo_cob = Number(dados.prazo_cob ?? 0);
    form.id_grupo = dados.id_grupo ?? "";
    form.id_tipo_venda = dados.id_tipo_venda ?? "";
    return;
  }

  form.prazo_cob = 0;
  form.id_grupo = "";
  form.id_tipo_venda = "";
}

async function fetchGrupos() {
  const response = await fetch(`${API_BASE_URL}/api/cadastros/grupos-cliente`);
  if (!response.ok) throw new Error(`Erro ${response.status}`);
  const data = await response.json();
  gruposOptions.value = (data.results || []).map((item) => ({
    value: item.id_grupo,
    label: item.descricao,
  }));
}

async function fetchTiposVenda() {
  const response = await fetch(`${API_BASE_URL}/api/cadastros/tipos-venda`);
  if (!response.ok) throw new Error(`Erro ${response.status}`);
  const data = await response.json();
  tiposVendaOptions.value = (data.results || []).map((item) => ({
    value: item.id_tipo_venda,
    label: item.descricao,
  }));
}

function toNumberOrNull(value) {
  if (value === "" || value === null || value === undefined) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

async function save() {
  if (!props.cliente) return;

  saving.value = true;
  error.value = "";

  const payload = {
    id_cliente: props.cliente.id_cliente,
    nome_cliente: String(form.nome_cliente || ""),
    raz_social: String(form.raz_social || ""),
    prazo_cob: Number(form.prazo_cob || 0),
    id_grupo: toNumberOrNull(form.id_grupo),
    id_tipo_venda: toNumberOrNull(form.id_tipo_venda),
  };

  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/clientes/aprovar`, {
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
    error.value = "Falha ao aprovar cliente.";
  } finally {
    saving.value = false;
  }
}
</script>
