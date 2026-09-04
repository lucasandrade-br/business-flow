export const MESES = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']

export function numeroFinanceiro(valor) {
  if (valor === null || valor === undefined || valor === '') return null
  const numero = Number(valor)
  return Number.isFinite(numero) && numero !== 0 ? numero : null
}

export function formatarValor(valor, casasDecimais = 0) {
  const numero = numeroFinanceiro(valor)
  if (numero === null) return '-'
  return numero.toLocaleString('pt-BR', {
    minimumFractionDigits: casasDecimais,
    maximumFractionDigits: casasDecimais,
  })
}

// Ranking independente por linha. Zeros não participam da distribuição e
// valores empatados recebem sempre a mesma classificação.
export function mapaQuartis(valores, indicesIgnorados = []) {
  const ignorados = new Set(indicesIgnorados)
  const validos = valores
    .map(numeroFinanceiro)
    .filter((valor, indice) => valor !== null && !ignorados.has(indice))
  if (validos.length < 4) return null

  const unicos = [...new Set(validos)].sort((a, b) => a - b)
  if (unicos.length < 2) return null

  return new Map(unicos.map((valor, indice) => [valor, indice / (unicos.length - 1)]))
}

export function estiloCelulaFinanceira(ranking, valor, inverterCores = false, ignorar = false) {
  if (ignorar) return {}
  const numero = numeroFinanceiro(valor)
  if (numero === null || !ranking) return {}

  const posicao = ranking.get(numero)
  if (posicao === undefined) return {}
  const baixoForte = inverterCores ? 'rgba(47, 111, 79, 0.30)' : 'rgba(168, 38, 49, 0.30)'
  const baixoSuave = inverterCores ? 'rgba(47, 111, 79, 0.12)' : 'rgba(168, 38, 49, 0.12)'
  const altoForte = inverterCores ? 'rgba(168, 38, 49, 0.30)' : 'rgba(47, 111, 79, 0.30)'
  const altoSuave = inverterCores ? 'rgba(168, 38, 49, 0.12)' : 'rgba(47, 111, 79, 0.12)'

  if (posicao === 0) return { backgroundColor: baixoForte }
  if (posicao <= 0.25) return { backgroundColor: baixoSuave }
  if (posicao === 1) return { backgroundColor: altoForte }
  if (posicao >= 0.75) return { backgroundColor: altoSuave }
  return {}
}

export function indiceMesAberto(dados) {
  const mes = Number(dados?.mes_aberto)
  return Number.isInteger(mes) && mes >= 1 && mes <= 12 ? mes - 1 : -1
}

export function indicesIgnoradosMesAberto(dados) {
  const indice = indiceMesAberto(dados)
  return indice >= 0 ? [indice] : []
}

export function mesEstaAberto(dados, indice) {
  return indiceMesAberto(dados) === indice
}

export function tooltipMesAberto(dados, indice) {
  if (!mesEstaAberto(dados, indice)) return undefined
  const partes = String(dados?.ultima_data_disponivel || '').split('-')
  const data = partes.length === 3 ? `${partes[2]}/${partes[1]}` : ''
  return data ? `Mês em aberto — dados parciais até ${data}` : 'Mês em aberto'
}

export function formatarQuantidade(valor) {
  const numero = Number(valor || 0)
  if (!Number.isFinite(numero) || numero === 0) return '-'
  return numero.toLocaleString('pt-BR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  })
}
