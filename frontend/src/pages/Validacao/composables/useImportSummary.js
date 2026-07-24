import { reactive } from "vue";

// Singleton: importSummary é preenchido pelo PainelImportacaoVendas após polling
// e exibido pelo PainelGerenciamentoStg quando o painel é montado.
export const importSummary = reactive({
  arquivos_recebidos: 0,
  linhas_importadas: 0,
  erros_importacao: [],
});

export function resetImportSummary() {
  importSummary.arquivos_recebidos = 0;
  importSummary.linhas_importadas = 0;
  importSummary.erros_importacao = [];
}

export function useImportSummary() {
  return { importSummary, resetImportSummary };
}
