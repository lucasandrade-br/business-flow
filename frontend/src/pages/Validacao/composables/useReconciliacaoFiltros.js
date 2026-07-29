import { ref } from "vue";
import { getApiBaseUrl } from "@/services/firebirdSync";

const API_BASE_URL = getApiBaseUrl();

// Composable de instância: cada chamada ao PainelGerenciamentoStg cria
// refs independentes. Ao desmontar o painel os filtros são descartados.
export function useReconciliacaoFiltros() {
  const filtroMotivo = ref("");
  const filtroStatusValidacao = ref("PENDENTE");
  const filtroTratamento = ref("PENDENTE");
  const filtroStatusVenda = ref("");
  const filtroIdLegado = ref("");

  // Filtros secundários
  const filtroTipoDocumento = ref("");
  const filtroImportacaoOrigem = ref("");
  const filtroFormatoPagamentoVenda = ref("");
  const filtroFormatoPagamentoAuditoria = ref("");
  const filtroValorVenda = ref("");
  const filtroDataVenda = ref("");

  function buildUrl(url = "") {
    const target = new URL(url || `${API_BASE_URL}/api/validacao/reconciliacao/divergencias`);

    const idLegadoNorm = String(filtroIdLegado.value || "").trim();
    const valorVendaNorm = String(filtroValorVenda.value || "").trim();

    // Modo lookup: se ID ou valor preenchidos, envia apenas esse parâmetro
    if (idLegadoNorm) {
      target.searchParams.set("id_legado", idLegadoNorm);
      return target.toString();
    }
    if (valorVendaNorm) {
      target.searchParams.set("valor_venda", valorVendaNorm);
      return target.toString();
    }

    // Modo normal: filtros categóricos e de data
    if (filtroMotivo.value) target.searchParams.set("motivo", filtroMotivo.value);
    else target.searchParams.delete("motivo");

    if (filtroStatusValidacao.value) target.searchParams.set("status_validacao", filtroStatusValidacao.value);
    else target.searchParams.delete("status_validacao");

    if (filtroTratamento.value) target.searchParams.set("tratamento", filtroTratamento.value);
    else target.searchParams.delete("tratamento");

    if (filtroStatusVenda.value) target.searchParams.set("status_venda", filtroStatusVenda.value);
    else target.searchParams.delete("status_venda");

    if (filtroTipoDocumento.value) target.searchParams.set("tipo_documento", filtroTipoDocumento.value);
    else target.searchParams.delete("tipo_documento");

    if (filtroImportacaoOrigem.value) target.searchParams.set("importacao_origem", filtroImportacaoOrigem.value);
    else target.searchParams.delete("importacao_origem");

    if (filtroFormatoPagamentoVenda.value) target.searchParams.set("formato_pagamento_venda", filtroFormatoPagamentoVenda.value.trim().toUpperCase());
    else target.searchParams.delete("formato_pagamento_venda");

    if (filtroFormatoPagamentoAuditoria.value) target.searchParams.set("formato_pagamento_auditoria", filtroFormatoPagamentoAuditoria.value.trim().toUpperCase());
    else target.searchParams.delete("formato_pagamento_auditoria");

    if (filtroDataVenda.value) target.searchParams.set("data_venda", filtroDataVenda.value);
    else target.searchParams.delete("data_venda");

    return target.toString();
  }

  function limparFiltros(onLimpar) {
    filtroMotivo.value = "";
    filtroStatusValidacao.value = "PENDENTE";
    filtroTratamento.value = "PENDENTE";
    filtroStatusVenda.value = "";
    filtroIdLegado.value = "";
    filtroTipoDocumento.value = "";
    filtroImportacaoOrigem.value = "";
    filtroFormatoPagamentoVenda.value = "";
    filtroFormatoPagamentoAuditoria.value = "";
    filtroValorVenda.value = "";
    filtroDataVenda.value = "";
    if (typeof onLimpar === "function") onLimpar();
  }

  return {
    filtroMotivo,
    filtroStatusValidacao,
    filtroTratamento,
    filtroStatusVenda,
    filtroIdLegado,
    filtroTipoDocumento,
    filtroImportacaoOrigem,
    filtroFormatoPagamentoVenda,
    filtroFormatoPagamentoAuditoria,
    filtroValorVenda,
    filtroDataVenda,
    buildUrl,
    limparFiltros,
  };
}
