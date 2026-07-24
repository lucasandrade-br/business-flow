import { computed, ref } from "vue";
import { LABELS_CODIGO_BLOQUEIO } from "@/constants/reconciliacaoVendas";

// Composable de instância: cada chamada cria estado próprio.
// Usado exclusivamente pelo PainelGerenciamentoStg.
export function useBloqueioModal() {
  const showBloqueioModal = ref(false);
  const bloqueioModalRunning = ref(false);
  const bloqueioModalItems = ref([]);
  const bloqueioModalMensagem = ref("");
  const bloqueioModalCodigo = ref("");
  const bloqueioModalPodeProsseguir = ref(false);
  const bloqueioModalOrigem = ref("");
  const bloqueioModalConfirmAction = ref(null);

  const bloqueioModalDescricao = computed(() => {
    if (bloqueioModalOrigem.value === "validar_lote") return "As vendas abaixo foram bloqueadas durante a validacao em lote.";
    if (bloqueioModalOrigem.value === "validar_linha") return "A venda selecionada foi bloqueada para validacao.";
    if (bloqueioModalOrigem.value === "consolidar") return "A consolidacao encontrou vendas bloqueadas.";
    return "Foram identificados bloqueios durante a operacao.";
  });

  const bloqueioResumoPorCodigo = computed(() => {
    const acumulado = new Map();
    for (const item of bloqueioModalItems.value || []) {
      const codigosUnicos = new Set(
        (item?.codigos || []).map((c) => String(c || "").trim()).filter(Boolean)
      );
      for (const codigo of codigosUnicos) {
        acumulado.set(codigo, Number(acumulado.get(codigo) || 0) + 1);
      }
    }
    return Array.from(acumulado.entries())
      .map(([codigo, total]) => ({ codigo, total, label: formatarCodigoBloqueio(codigo) }))
      .sort((a, b) => b.total - a.total || a.label.localeCompare(b.label));
  });

  function formatarCodigoBloqueio(codigo) {
    const norm = String(codigo || "").trim();
    return LABELS_CODIGO_BLOQUEIO[norm] || norm || "-";
  }

  function formatarCodigosBloqueio(codigos) {
    return (codigos || []).map((c) => formatarCodigoBloqueio(c)).join(", ") || "-";
  }

  function limparEstadoBloqueioModal() {
    bloqueioModalItems.value = [];
    bloqueioModalMensagem.value = "";
    bloqueioModalCodigo.value = "";
    bloqueioModalPodeProsseguir.value = false;
    bloqueioModalOrigem.value = "";
    bloqueioModalConfirmAction.value = null;
    bloqueioModalRunning.value = false;
  }

  function abrirBloqueioModal({ origem, mensagem, codigo, bloqueios, permiteOverride, onConfirm }) {
    bloqueioModalOrigem.value = origem || "";
    bloqueioModalMensagem.value = mensagem || "Operacao bloqueada por inconsistencias estruturais.";
    bloqueioModalCodigo.value = codigo || "";
    bloqueioModalItems.value = Array.isArray(bloqueios) ? bloqueios : [];
    const podeProsseguir = Boolean(permiteOverride && typeof onConfirm === "function");
    bloqueioModalPodeProsseguir.value = podeProsseguir;
    bloqueioModalConfirmAction.value = podeProsseguir ? onConfirm : null;
    showBloqueioModal.value = true;
  }

  function cancelarBloqueioModal() {
    showBloqueioModal.value = false;
    limparEstadoBloqueioModal();
  }

  async function prosseguirBloqueioModal(onError) {
    if (!bloqueioModalConfirmAction.value) return;
    bloqueioModalRunning.value = true;
    try {
      const executar = bloqueioModalConfirmAction.value;
      showBloqueioModal.value = false;
      await executar();
    } catch (err) {
      console.error(err);
      if (typeof onError === "function") {
        onError(err?.message || "Falha ao prosseguir com override de bloqueio.");
      }
    } finally {
      limparEstadoBloqueioModal();
    }
  }

  return {
    showBloqueioModal,
    bloqueioModalRunning,
    bloqueioModalItems,
    bloqueioModalMensagem,
    bloqueioModalCodigo,
    bloqueioModalPodeProsseguir,
    bloqueioModalOrigem,
    bloqueioModalDescricao,
    bloqueioResumoPorCodigo,
    formatarCodigoBloqueio,
    formatarCodigosBloqueio,
    limparEstadoBloqueioModal,
    abrirBloqueioModal,
    cancelarBloqueioModal,
    prosseguirBloqueioModal,
  };
}
