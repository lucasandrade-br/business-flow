export const fmtR = (valor) =>
  valor === null || valor === undefined ? '—'
    : Number(valor).toLocaleString('pt-BR', { maximumFractionDigits: 0 })

export const fmtRVar = (valor) => {
  if (valor === null || valor === undefined) return '—'
  const numero = Number(valor)
  return (numero > 0 ? '+' : '') + numero.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
}

export const fmtP = (valor, casas = 1) =>
  valor === null || valor === undefined ? '—' : `${Number(valor).toFixed(casas)}%`

export const fmtX = (valor) =>
  valor === null || valor === undefined ? '—' : `${Number(valor).toFixed(2)}x`

export const sgn = (valor) => Number(valor) >= 0 ? '+' : ''

export const fmtData = (valor) => {
  if (!valor) return '—'
  const [ano, mes, dia] = valor.slice(0, 10).split('-')
  return `${dia}/${mes}/${ano}`
}

export const fmtMomento = (valor) => valor
  ? new Date(valor).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
  : '—'

export function corVar(tipo, valor) {
  if (valor === null || valor === undefined) return 'text-gray-300'
  const alta = Number(valor) >= 0
  if (tipo === 'custo') return alta ? 'text-[#a82631]' : 'text-[#2f6f4f]'
  return alta ? 'text-[#2f6f4f]' : 'text-[#a82631]'
}
