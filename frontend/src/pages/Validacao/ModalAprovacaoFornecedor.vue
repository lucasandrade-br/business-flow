<template>
  <BaseModal
    v-model="open"
    :title="`Fornecedor ${fornecedor?.id_fornecedor ?? ''}`"
    description="Confirme os dados e informe os campos finais para cadastro oficial."
  >
    <div v-if="!fornecedor" class="text-sm text-gray-500">Nenhum fornecedor selecionado.</div>

    <div v-else class="space-y-4">
      <section class="grid gap-3 rounded-md border border-gray-200 p-3 lg:grid-cols-2">
        <div class="space-y-1">
          <BaseInput
            v-model="form.nome_fornecedor"
            label="Fantasia"
            readonly
            :input-class="isCampoDivergente('nome_fornecedor', form.nome_fornecedor, normalizeString) ? 'bg-yellow-50 border-yellow-300 text-yellow-900' : ''"
          />
          <p v-if="isCampoDivergente('nome_fornecedor', form.nome_fornecedor, normalizeString)" class="text-[11px] text-yellow-800">
            Atualmente: {{ valorSotTexto('nome_fornecedor') }}
          </p>
        </div>
        <div>
          <p class="inline-flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-gray-500">
            ID
            <span class="text-red-500">*</span>
          </p>
          <p class="mt-1 text-sm text-[#373435]">{{ fornecedor.id_fornecedor }}</p>
        </div>
        <div class="space-y-1">
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
        <div>
          <p class="text-xs font-medium uppercase tracking-wide text-gray-500">Cadastro</p>
          <p class="mt-1 text-sm text-[#373435]">{{ fornecedor.dt_cadastro || "-" }}</p>
        </div>
      </section>

      <section class="grid gap-3 lg:grid-cols-2">
        <label class="space-y-1 text-xs">
          <span class="inline-flex items-center gap-1 font-medium text-gray-600">
            ID CodSis
            <span class="group relative inline-flex items-center">
              <HelpCircle class="h-4 w-4 text-gray-400" />
              <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-56 -translate-x-1/2 rounded-md bg-[#1f1f1f] px-2 py-1 text-[11px] font-normal text-white group-hover:block">
                Identificador legado para integracao
              </span>
            </span>
          </span>
          <input v-model="form.id_codsis" type="number" class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm" />
        </label>
        <label class="space-y-1 text-xs">
          <span class="inline-flex items-center gap-1 font-medium text-gray-600">
            Codigo (5)
            <span class="group relative inline-flex items-center">
              <HelpCircle class="h-4 w-4 text-gray-400" />
              <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-56 -translate-x-1/2 rounded-md bg-[#1f1f1f] px-2 py-1 text-[11px] font-normal text-white group-hover:block">
                Codigo numerico com 5 digitos
              </span>
            </span>
          </span>
          <input
            v-model="form.codigo"
            maxlength="5"
            class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm"
            @blur="form.codigo = padCodigo(form.codigo)"
          />
        </label>
        <label class="space-y-1 text-xs">
          <span class="inline-flex items-center gap-1 font-medium text-gray-600">
            Operador
            <span class="group relative inline-flex items-center">
              <HelpCircle class="h-4 w-4 text-gray-400" />
              <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-56 -translate-x-1/2 rounded-md bg-[#1f1f1f] px-2 py-1 text-[11px] font-normal text-white group-hover:block">
                Nivel de operacao permitido (0, 1 ou 10)
              </span>
            </span>
          </span>
          <select v-model="form.operador" class="w-full appearance-none rounded-md border border-gray-200 bg-white px-3 py-2 text-sm">
            <option :value="0">0</option>
            <option :value="1">1</option>
            <option :value="10">10</option>
          </select>
        </label>
        <label class="space-y-1 text-xs">
          <span class="font-medium text-gray-600">Usuario</span>
          <input v-model="form.usuario" class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm" />
        </label>
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
  fornecedor: { type: Object, default: null },
});

const emit = defineEmits(["update:modelValue", "approved"]);

const saving = ref(false);
const error = ref("");

const form = reactive({
  nome_fornecedor: "",
  raz_social: "",
  id_codsis: "",
  codigo: "",
  operador: 0,
  usuario: "",
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
    }
  },
);

function normalizeString(value) {
  return String(value || "").trim();
}

function isAtualizacao() {
  return props.fornecedor?.tipo_pendencia === "ATUALIZACAO" && !!props.fornecedor?.dados_sot;
}

function isCampoDivergente(campo, valorAtual, normalizer = (value) => value) {
  if (!isAtualizacao()) {
    return false;
  }
  const dados = props.fornecedor?.dados_sot || {};
  const valorSot = campo === "nome_fornecedor" ? (dados.nome_fornecedor ?? dados.fantasia) : dados[campo];
  return normalizer(valorAtual) !== normalizer(valorSot);
}

function valorSotTexto(campo) {
  const dados = props.fornecedor?.dados_sot || {};
  const valor = campo === "nome_fornecedor" ? (dados.nome_fornecedor ?? dados.fantasia) : dados[campo];
  if (valor === null || valor === undefined || String(valor).trim() === "") {
    return "-";
  }
  return String(valor);
}

function hydrateForm() {
  form.nome_fornecedor = String(props.fornecedor?.nome_fornecedor || "");
  form.raz_social = String(props.fornecedor?.raz_social || "");

  if (isAtualizacao()) {
    const dados = props.fornecedor?.dados_sot || {};
    form.id_codsis = dados.id_codsis ?? "";
    form.codigo = dados.codigo ?? "";
    form.operador = Number(dados.operador ?? 0);
    form.usuario = dados.usuario ?? "";
    return;
  }

  form.id_codsis = "";
  form.codigo = "";
  form.operador = 0;
  form.usuario = "";
}

function toNumberOrNull(value) {
  if (value === "" || value === null || value === undefined) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function padCodigo(value) {
  const clean = String(value || "").replace(/\D/g, "").slice(0, 5);
  return clean ? clean.padStart(5, "0") : "";
}

async function save() {
  if (!props.fornecedor) return;

  saving.value = true;
  error.value = "";

  const payload = {
    id_fornecedor: props.fornecedor.id_fornecedor,
    nome_fornecedor: String(form.nome_fornecedor || ""),
    raz_social: String(form.raz_social || ""),
    dt_cadastro: props.fornecedor.dt_cadastro || null,
    id_codsis: toNumberOrNull(form.id_codsis),
    codigo: padCodigo(form.codigo),
    operador: Number(form.operador || 0),
    usuario: String(form.usuario || ""),
  };

  try {
    const response = await fetch(`${API_BASE_URL}/api/validacao/fornecedores/aprovar`, {
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
    error.value = "Falha ao aprovar fornecedor.";
  } finally {
    saving.value = false;
  }
}
</script>
