/**
 * Estado global da filial ativa — sem Pinia.
 *
 * A filial selecionada fica salva em localStorage (chave BF_FILIAL_ATIVA).
 * Ao mudar a filial, BF_API_BASE_URL também é atualizada para que
 * getApiBaseUrl() em firebirdSync.js aponte automaticamente para o backend
 * correto na próxima requisição.
 */
import { ref, watch } from 'vue'
import { FILIAIS } from '@/config/filiais.js'

const STORAGE_KEY = 'BF_FILIAL_ATIVA'

function loadFromStorage() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const found = FILIAIS.find(f => f.id === saved)
      if (found) return found
    }
  } catch {}
  return FILIAIS[0]
}

export const filialAtiva = ref(loadFromStorage())

// Mantém BF_API_BASE_URL em sincronia com a filial ativa.
// immediate:true garante que a URL correta é gravada logo na inicialização.
watch(filialAtiva, (nova) => {
  try {
    localStorage.setItem(STORAGE_KEY, nova.id)
    localStorage.setItem('BF_API_BASE_URL', nova.apiUrl)
  } catch {}
}, { immediate: true })

export function setFilial(filial) {
  filialAtiva.value = filial
}
