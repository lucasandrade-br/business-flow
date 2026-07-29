export const MOTIVO_LABELS = {
  divergencia_formato: "Divergência de formato",
  divergencia_totais: "Divergência de totais",
  duplicado_sot: "Duplicado no SOT",
};

export const motivoOptions = Object.entries(MOTIVO_LABELS).map(([value, label]) => ({ value, label }));

export const LABELS_CODIGO_BLOQUEIO = {
  divergencia_formato_pagamento: "Divergencia de formato de pagamento",
  venda_sem_itens_ou_pagamentos: "Venda sem itens ou pagamentos",
  pagamento_sem_id_forma_origem: "Pagamento sem forma de origem",
  forma_origem_nao_cadastrada: "Forma de origem nao cadastrada",
  mapeamento_forma_ausente: "Mapeamento de forma ausente",
  cliente_nao_encontrado: "Cliente nao encontrado",
  cliente_nome_divergente: "Nome de cliente divergente",
  cliente_legado_zero_sem_cliente_padrao_configurado: "Cliente padrao nao configurado",
  usuario_legado_ausente: "Usuario legado ausente",
  usuario_legado_nao_encontrado: "Usuario legado nao encontrado",
  usuario_nome_divergente: "Nome de usuario divergente",
  item_sem_id_produto: "Item sem produto",
  produto_nao_encontrado: "Produto nao encontrado",
  produto_nome_divergente: "Nome de produto divergente",
  unidade_legado_sem_mapeamento: "Unidade sem mapeamento",
  consolidacao_bloqueada_divergencia_reconciliacao: "Divergencia estrutural na reconciliacao",
  consolidacao_bloqueada_precheck: "Inconsistencias estruturais de pre-check",
  validacao_bloqueada_precheck: "Inconsistencias estruturais de validacao",
};

export const MENSAGENS_AMIGAVEIS_BLOQUEIO = {
  validacao_bloqueada_precheck: "Validacao bloqueada por inconsistencias estruturais.",
  consolidacao_bloqueada_divergencia_reconciliacao: "Consolidacao bloqueada por divergencias estruturais na reconciliacao.",
  consolidacao_bloqueada_precheck: "Consolidacao bloqueada por inconsistencias estruturais de pre-check.",
};

export const STATUS_TRATAMENTO_MANUAL = "MANUAL";
export const STATUS_TRATAMENTO_AUTOMATICO = "AUTOMATICO";
export const STATUS_VALIDACAO_NEGADO = "NEGADO";
export const MOTIVO_DUPLICADO_SOT = "duplicado_sot";

export const TABLE_COLUMNS = [
  { key: "select", label: "Sel" },
  { key: "venda", label: "Venda" },
  { key: "status_venda", label: "Status" },
  { key: "total_documento", label: "Total Doc." },
  { key: "total_itens", label: "Total Ite." },
  { key: "total_pagamentos", label: "Total Pag." },
  { key: "total_auditoria", label: "Total Aud.", headerClass: "bg-[#f0f7ff]", cellClass: "bg-[#f8fbff]" },
  { key: "formato_venda", label: "Form. Venda" },
  { key: "formato_auditoria", label: "Form. Aud.", headerClass: "bg-[#f0f7ff]", cellClass: "bg-[#f8fbff]" },
  { key: "cliente", label: "Cliente" },
];
