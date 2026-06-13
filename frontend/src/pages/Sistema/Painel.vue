<template>
  <section class="space-y-4">
    <article class="rounded-md border border-gray-200 bg-white p-4">
      <h2 class="text-sm font-semibold text-[#373435]">Sistema</h2>
      <p class="mt-1 text-xs text-gray-500">Area reservada para configuracoes operacionais e monitoramento.</p>
    </article>

    <article class="rounded-md border border-gray-200 bg-white p-4 space-y-4">
      <div>
        <h3 class="text-sm font-semibold text-[#373435]">Conexao Firebird</h3>
        <p class="mt-1 text-xs text-gray-500">
          Defina se a origem Firebird sera fixa (caminho salvo) ou dinamica (escolha do arquivo a cada sincronizacao).
        </p>
      </div>

      <div class="rounded-md border border-gray-200 bg-gray-50 p-3 space-y-3">
        <label class="inline-flex items-center gap-2 text-xs font-semibold text-gray-700">
          <input v-model="modoDinamico" type="checkbox" :disabled="loading || saving" />
          Modo dinâmico (pedir arquivo no início de cada sincronização)
        </label>

        <div v-if="!modoDinamico" class="space-y-2">
          <label class="text-xs font-semibold text-gray-700">Caminho fixo do banco Firebird</label>
          <input
            v-model="caminhoFixo"
            type="text"
            placeholder="Ex.: C:/Bases/ERP/HOST_DELICIAS.FDB"
            class="w-full rounded-md border border-gray-200 px-3 py-2 text-xs"
            :disabled="loading || saving"
          />
          <p class="text-[11px] text-gray-500">Esse caminho sera usado em todas as sincronizacoes enquanto o modo fixo estiver ativo.</p>
        </div>

        <div v-else class="rounded-md border border-blue-100 bg-blue-50 p-2 text-xs text-blue-900">
          No modo dinamico, o sistema abrira o explorer para selecionar o arquivo Firebird antes de cada sincronizacao.
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="rounded-md bg-[#1f4f8a] px-3 py-2 text-xs font-semibold text-white hover:bg-[#193f6e] disabled:opacity-60"
          :disabled="loading || saving"
          @click="salvarConfiguracao"
        >
          {{ saving ? "Salvando..." : "Salvar configuracao" }}
        </button>
        <button
          type="button"
          class="rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-60"
          :disabled="loading || saving"
          @click="carregarConfiguracao"
        >
          Recarregar
        </button>
      </div>

      <p v-if="mensagemSucesso" class="text-xs text-green-700">{{ mensagemSucesso }}</p>
      <p v-if="mensagemErro" class="text-xs text-red-600">{{ mensagemErro }}</p>

      <div class="rounded-md border border-gray-200 bg-white p-3 text-xs text-gray-600 space-y-1">
        <p><strong>Modo atual:</strong> {{ modoDinamico ? "Dinamico" : "Fixo" }}</p>
        <p><strong>Caminho efetivo:</strong> {{ caminhoEfetivo || "Nao definido" }}</p>
      </div>
    </article>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { getApiBaseUrl } from "@/services/firebirdSync";

const API_BASE_URL = getApiBaseUrl();

const loading = ref(false);
const saving = ref(false);
const modoDinamico = ref(false);
const caminhoFixo = ref("");
const caminhoEfetivo = ref("");
const mensagemErro = ref("");
const mensagemSucesso = ref("");

function limparMensagens() {
  mensagemErro.value = "";
  mensagemSucesso.value = "";
}

function aplicarPayload(payload) {
  const modo = String(payload?.modo_localizacao || "FIXED").toUpperCase();
  modoDinamico.value = modo === "DYNAMIC";
  caminhoFixo.value = String(payload?.caminho_fixo || "");
  caminhoEfetivo.value = String(payload?.caminho_efetivo || "");
}

async function carregarConfiguracao() {
  loading.value = true;
  limparMensagens();

  try {
    const response = await fetch(`${API_BASE_URL}/api/integracao/firebird-config`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `Erro ${response.status}`);
    }

    aplicarPayload(payload);
  } catch (error) {
    console.error(error);
    mensagemErro.value = error?.message || "Falha ao carregar configuracao do Firebird.";
  } finally {
    loading.value = false;
  }
}

async function salvarConfiguracao() {
  saving.value = true;
  limparMensagens();

  try {
    const response = await fetch(`${API_BASE_URL}/api/integracao/firebird-config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        modo_localizacao: modoDinamico.value ? "DYNAMIC" : "FIXED",
        caminho_fixo: caminhoFixo.value,
      }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `Erro ${response.status}`);
    }

    aplicarPayload(payload);
    mensagemSucesso.value = "Configuracao salva com sucesso.";
  } catch (error) {
    console.error(error);
    mensagemErro.value = error?.message || "Falha ao salvar configuracao do Firebird.";
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  carregarConfiguracao();
});
</script>
