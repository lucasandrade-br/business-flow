import { reactive } from "vue";

// Singleton: compartilhado entre PainelImportacaoVendas e PainelGerenciamentoStg
const kpis = reactive({
  total_vendas_stg: 0,
  vendas_aprovadas: 0,
  vendas_divergentes: 0,
  vendas_duplicadas_sot: 0,
  vendas_negadas: 0,
  soma_valor_stg: "0",
  soma_valor_stg_canceladas: "0",
  soma_valor_vendas_validadas: "0",
  qtd_vendas_validadas: 0,
  soma_valor_auditoria: "0",
  qtd_vendas_auditoria: 0,
  diferenca_total: "0",
  motivos_divergencia: {},
  periodo_data_inicial: null,
  periodo_data_final: null,
  periodo_auditoria_data_inicial: null,
  periodo_auditoria_data_final: null,
});

export function applyKpis(data) {
  kpis.total_vendas_stg = Number(data.total_vendas_stg || 0);
  kpis.vendas_aprovadas = Number(data.vendas_aprovadas || 0);
  kpis.vendas_divergentes = Number(data.vendas_divergentes || 0);
  kpis.vendas_duplicadas_sot = Number(data.vendas_duplicadas_sot || 0);
  // Backend retorna vendas_negligenciadas; manter compatibilidade com campo legacy vendas_negadas
  kpis.vendas_negadas = Number(data.vendas_negligenciadas ?? data.vendas_negadas ?? 0);
  kpis.soma_valor_stg = data.soma_valor_stg || "0";
  kpis.soma_valor_stg_canceladas = data.soma_valor_stg_canceladas || "0";
  kpis.soma_valor_vendas_validadas = data.soma_valor_vendas_validadas || "0";
  kpis.qtd_vendas_validadas = Number(data.qtd_vendas_validadas || 0);
  kpis.soma_valor_auditoria = data.soma_valor_auditoria || "0";
  kpis.qtd_vendas_auditoria = Number(data.qtd_vendas_auditoria || 0);
  kpis.diferenca_total =
    data.diferenca_total ||
    String(Number(kpis.soma_valor_vendas_validadas || 0) - Number(kpis.soma_valor_auditoria || 0));
  kpis.motivos_divergencia = data.motivos_divergencia || {};
  kpis.periodo_data_inicial = data.periodo_data_inicial || null;
  kpis.periodo_data_final = data.periodo_data_final || null;
  kpis.periodo_auditoria_data_inicial = data.periodo_auditoria_data_inicial || null;
  kpis.periodo_auditoria_data_final = data.periodo_auditoria_data_final || null;
}

export function resetKpis() {
  kpis.total_vendas_stg = 0;
  kpis.vendas_aprovadas = 0;
  kpis.vendas_divergentes = 0;
  kpis.vendas_duplicadas_sot = 0;
  kpis.vendas_negadas = 0;
  kpis.soma_valor_stg = "0";
  kpis.soma_valor_stg_canceladas = "0";
  kpis.soma_valor_vendas_validadas = "0";
  kpis.qtd_vendas_validadas = 0;
  kpis.soma_valor_auditoria = "0";
  kpis.qtd_vendas_auditoria = 0;
  kpis.diferenca_total = "0";
  kpis.motivos_divergencia = {};
  kpis.periodo_data_inicial = null;
  kpis.periodo_data_final = null;
}

export function useSharedKpis() {
  return { kpis, applyKpis, resetKpis };
}
