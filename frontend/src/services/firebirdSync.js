const FALLBACK_LOCAL_BACKEND = "http://127.0.0.1:8000";

function getEnvApiBaseUrl() {
  try {
    return String(import.meta?.env?.VITE_API_BASE_URL || "").trim();
  } catch {
    return "";
  }
}

function getRuntimeApiBaseUrl() {
  if (typeof window === "undefined") {
    return "";
  }
  return String(window.localStorage?.getItem("BF_API_BASE_URL") || "").trim();
}

function getSameOriginBaseUrl() {
  if (typeof window === "undefined") {
    return "";
  }
  const origin = String(window.location?.origin || "").trim();
  if (!origin || origin === "null") {
    return "";
  }
  return origin;
}

export function getApiBaseUrl() {
  return getRuntimeApiBaseUrl() || getEnvApiBaseUrl() || FALLBACK_LOCAL_BACKEND;
}

function getApiBaseCandidates() {
  const list = [
    getRuntimeApiBaseUrl(),
    getEnvApiBaseUrl(),
    FALLBACK_LOCAL_BACKEND,
    getSameOriginBaseUrl(),
  ].filter(Boolean);

  return [...new Set(list)];
}

function joinUrl(baseUrl, path) {
  const base = String(baseUrl || "").trim().replace(/\/+$/, "");
  const suffix = String(path || "").trim();
  if (!base) {
    return suffix;
  }
  if (!suffix) {
    return base;
  }
  if (suffix.startsWith("http://") || suffix.startsWith("https://")) {
    return suffix;
  }
  return `${base}${suffix.startsWith("/") ? "" : "/"}${suffix}`;
}

function extractPathAndSearch(url) {
  try {
    const target = new URL(url);
    return `${target.pathname}${target.search}`;
  } catch {
    return String(url || "");
  }
}

const MODO_FIXO = "FIXED";
const MODO_DINAMICO = "DYNAMIC";

function shouldFallbackToBrowserUpload(statusCode, detailMessage) {
  const detail = String(detailMessage || "").toLowerCase();
  return (
    statusCode === 404
    || statusCode === 405
    || statusCode === 501
    || detail.includes("nao foi possivel abrir o explorer")
  );
}

function createFileInputPicker() {
  return new Promise((resolve) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".fdb,.gdb,.fbk";

    input.addEventListener("change", () => {
      const file = input.files && input.files[0] ? input.files[0] : null;
      resolve(file);
    });

    input.click();
  });
}

function buildBackendUnavailableMessage() {
  const suggested = getApiBaseCandidates()[0] || FALLBACK_LOCAL_BACKEND;
  return (
    `Nao foi possivel conectar ao backend em ${suggested}. `
    + "Verifique se o servidor Django esta em execucao e tente novamente."
  );
}

function normalizeNetworkError(error) {
  const message = String(error?.message || "");
  const name = String(error?.name || "");
  const lower = message.toLowerCase();
  const isFetchNetworkError = name === "TypeError" && lower.includes("fetch");

  if (isFetchNetworkError || lower.includes("networkerror") || lower.includes("failed to fetch")) {
    return new Error(buildBackendUnavailableMessage());
  }

  return error instanceof Error ? error : new Error(String(error || "Erro desconhecido."));
}

async function pickFirebirdFile() {
  if (window.showOpenFilePicker) {
    try {
      const handles = await window.showOpenFilePicker({
        multiple: false,
        types: [
          {
            description: "Firebird database",
            accept: {
              "application/octet-stream": [".fdb", ".gdb", ".fbk"],
            },
          },
        ],
      });

      if (!handles || !handles.length) {
        return null;
      }

      return await handles[0].getFile();
    } catch (error) {
      if (error && error.name === "AbortError") {
        return null;
      }
      throw error;
    }
  }

  return createFileInputPicker();
}

async function fetchWithFallback(pathOrUrl, options = {}) {
  const path = extractPathAndSearch(pathOrUrl);
  const candidates = [];

  if (String(pathOrUrl || "").startsWith("http://") || String(pathOrUrl || "").startsWith("https://")) {
    candidates.push(String(pathOrUrl));
  }

  getApiBaseCandidates().forEach((base) => {
    candidates.push(joinUrl(base, path));
  });

  const deduped = [...new Set(candidates.filter(Boolean))];
  let lastError = null;

  for (const target of deduped) {
    try {
      return await fetch(target, options);
    } catch (error) {
      lastError = error;
    }
  }

  throw normalizeNetworkError(lastError);
}

async function pickFirebirdPathFromBackend() {
  const response = await fetchWithFallback("/api/integracao/firebird-picker", {
    method: "POST",
  });

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = String(payload?.detail || `Erro ${response.status}`).trim();
    if (detail.toLowerCase().includes("cancelada")) {
      throw new Error(detail);
    }
    if (shouldFallbackToBrowserUpload(response.status, detail)) {
      return "";
    }
    throw new Error(detail);
  }

  return String(payload?.firebird_path || "").trim();
}

export async function obterConfiguracaoFirebird() {
  const response = await fetchWithFallback("/api/integracao/firebird-config");

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.detail || `Erro ${response.status}`);
  }

  return payload;
}

export async function executarSincronizacaoFirebird(url, extraData = {}, options = {}) {
  const requestConfig = await montarRequestSincronizacaoFirebird(extraData, options);

  const response = await fetchWithFallback(url, {
    method: "POST",
    headers: requestConfig.headers,
    body: requestConfig.body,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Erro ${response.status}`);
  }

  return { response, payload, mode: requestConfig.mode };
}

export function formatarErroSincronizacao(error, fallbackMessage) {
  const normalized = normalizeNetworkError(error);
  const message = String(normalized?.message || "").trim();
  return message || fallbackMessage;
}

function buildDynamicPickerRequiredMessage() {
  return (
    "Nao foi possivel selecionar o caminho Firebird no servidor. "
    + "No modo dinamico, execute o backend com acesso ao explorer do sistema "
    + "ou configure um caminho fixo no Painel do Sistema."
  );
}

export async function montarRequestSincronizacaoFirebird(extraData = {}, options = {}) {
  const config = await obterConfiguracaoFirebird();
  const modo = String(config?.modo_localizacao || MODO_FIXO).toUpperCase();
  const allowBrowserUploadFallback = Boolean(options?.allowBrowserUploadFallback);

  if (modo === MODO_DINAMICO) {
    try {
      const firebirdPath = await pickFirebirdPathFromBackend();
      if (firebirdPath) {
        return {
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...(extraData || {}),
            firebird_path: firebirdPath,
          }),
          mode: MODO_DINAMICO,
        };
      }
    } catch (error) {
      const message = String(error?.message || "").toLowerCase();
      if (!message.includes("cancelada")) {
        throw error;
      }
      throw error;
    }

    if (!allowBrowserUploadFallback) {
      throw new Error(buildDynamicPickerRequiredMessage());
    }

    const arquivoFirebird = await pickFirebirdFile();
    if (!arquivoFirebird) {
      throw new Error("Selecao de arquivo Firebird cancelada.");
    }

    const formData = new FormData();
    Object.entries(extraData).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        formData.append(key, String(value));
      }
    });
    formData.append("firebird_file", arquivoFirebird, arquivoFirebird.name || "database.fdb");

    return {
      headers: {},
      body: formData,
      mode: MODO_DINAMICO,
    };
  }

  return {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(extraData || {}),
    mode: MODO_FIXO,
  };
}
