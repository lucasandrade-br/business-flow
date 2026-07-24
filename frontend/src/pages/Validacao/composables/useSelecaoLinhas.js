import { computed, reactive } from "vue";

// Composable de instância: cada painel tem seu próprio mapa de seleção.
export function useSelecaoLinhas(rowsRef) {
  const selectedMap = reactive({});

  const selectedRows = computed(() =>
    (rowsRef.value || []).filter((row) => selectedMap[row.row_key])
  );

  const allPaginaSelecionada = computed(
    () =>
      (rowsRef.value || []).length > 0 &&
      selectedRows.value.length === (rowsRef.value || []).length
  );

  function clearSelection() {
    Object.keys(selectedMap).forEach((key) => { delete selectedMap[key]; });
  }

  function toggleRow(row, checked) {
    selectedMap[row.row_key] = Boolean(checked);
  }

  function toggleLinha(row) {
    selectedMap[row.row_key] = !Boolean(selectedMap[row.row_key]);
  }

  function toggleSelecionarTodos(checked) {
    (rowsRef.value || []).forEach((row) => {
      selectedMap[row.row_key] = Boolean(checked);
    });
  }

  return {
    selectedMap,
    selectedRows,
    allPaginaSelecionada,
    clearSelection,
    toggleRow,
    toggleLinha,
    toggleSelecionarTodos,
  };
}
