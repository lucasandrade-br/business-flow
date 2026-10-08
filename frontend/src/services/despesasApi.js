import { filialAtiva } from '@/stores/filial.js'

export async function despesasApi(caminho, options = {}) {
  const resposta = await fetch(`${filialAtiva.value.apiUrl}/api/despesas/${caminho}`, options)
  if (resposta.status === 204) return null
  const corpo = await resposta.json().catch(() => ({}))
  if (!resposta.ok) {
    const detalhe = corpo.detail || Object.entries(corpo).map(([chave, valor]) => `${chave}: ${Array.isArray(valor) ? valor.join(', ') : valor}`).join(' · ')
    throw new Error(String(detalhe || 'Não foi possível concluir a operação.'))
  }
  return corpo
}

export function enviarJson(caminho, metodo, dados) {
  return despesasApi(caminho, { method: metodo, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dados) })
}

export function dinheiro(valor) {
  return valor == null ? '—' : Number(valor).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}
