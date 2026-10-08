<script setup>
import { computed } from 'vue'
import { BarChart2 } from 'lucide-vue-next'
import { useDre } from './useDre'
import { fmtData, fmtMomento, fmtP, fmtX } from './dreFormatters'
import {
  estiloCelulaFinanceira, formatarValor, indicesIgnoradosMesAberto,
  mapaQuartis, mesEstaAberto, numeroFinanceiro, tooltipMesAberto,
} from './analiseMensalUtils'

const { anosDisponiveis, anoSelecionado, periodoEquivalente, dados, loading, semDados, erro, periodosPendentes } = useDre('mensal')
const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

const linhas = computed(() => {
  if (!dados.value?.visao_mensal) return []
  const rec = dados.value.visao_mensal.receita
  const cst = dados.value.visao_mensal.compras
  const desp = dados.value.visao_mensal.despesas
  const resultadoMeses = rec.map((valor, indice) => valor !== null && desp[indice] !== null ? valor - desp[indice] : null)
  const resultadoPercentualMeses = rec.map((valor, indice) => {
    const resultado = resultadoMeses[indice]
    return resultado !== null && valor !== 0 ? resultado / valor * 100 : null
  })
  const fatMeses = rec.map((valor, indice) => {
    const despesa = desp[indice]
    return valor !== null && despesa !== null && despesa !== 0 ? valor / despesa : null
  })
  const tRec = rec.reduce((soma, valor) => soma + (valor ?? 0), 0)
  const tCst = cst.reduce((soma, valor) => soma + (valor ?? 0), 0)
  const tDesp = dados.value.despesas_incompletas ? null : desp.reduce((soma, valor) => soma + (valor ?? 0), 0)
  const tResultado = dados.value.total_resultado_disponivel ? tRec - tDesp : null
  const tResultadoPercentual = tResultado !== null && tRec !== 0 ? tResultado / tRec * 100 : null
  const tFat = tDesp !== null && tDesp !== 0 && tResultado !== null ? tRec / tDesp : null
  const ignorados = dados.value.periodo_equivalente ? [] : indicesIgnoradosMesAberto(dados.value)
  return [
    { label: 'Receita Total', tipo: 'normal', bold: false, destaque: false, meses: rec, total: tRec, fmt: formatarValor, fmtT: formatarValor, ranking: mapaQuartis(rec, ignorados) },
    { label: 'Despesas totais', tipo: 'custo', bold: false, destaque: false, meses: desp, total: tDesp, fmt: formatarValor, fmtT: formatarValor, ranking: mapaQuartis(desp, ignorados) },
    { label: 'Compras', tipo: 'informativo', bold: false, destaque: false, meses: cst, total: tCst, fmt: formatarValor, fmtT: formatarValor, ranking: [] },
    { label: 'Resultado operacional', tipo: 'normal', bold: true, destaque: true, meses: resultadoMeses, total: tResultado, fmt: formatarValor, fmtT: formatarValor, ranking: mapaQuartis(resultadoMeses, ignorados) },
    { label: 'Resultado %', tipo: 'normal', bold: false, destaque: false, meses: resultadoPercentualMeses, total: tResultadoPercentual, fmt: (valor) => fmtP(valor, 1), fmtT: (valor) => fmtP(valor, 1), ranking: mapaQuartis(resultadoPercentualMeses, ignorados) },
    { label: 'Fator de Retorno', tipo: 'normal', bold: false, destaque: false, meses: fatMeses, total: tFat, fmt: fmtX, fmtT: fmtX, ranking: mapaQuartis(fatMeses, ignorados) },
  ]
})

function estiloMensal(row, valor, indice) {
  if (row.tipo === 'informativo') return {}
  return estiloCelulaFinanceira(
    row.ranking, valor, row.tipo === 'custo',
    !dados.value?.periodo_equivalente && mesEstaAberto(dados.value, indice),
  )
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-xl font-bold text-gray-900">DRE Gerencial</h1>
      <p class="mt-0.5 text-sm text-gray-400">Receita de vendas, pagamentos de despesas e resultado gerencial por mês.</p>
    </div>

    <div v-if="semDados && !loading" class="rounded-xl border border-dashed border-gray-200 bg-white px-6 py-8 text-center">
      <div class="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-gray-100"><BarChart2 class="h-5 w-5 text-gray-400" /></div>
      <p class="text-sm font-medium text-gray-600">Nenhum dado disponível</p>
      <p class="mt-1 text-xs text-gray-400">Execute o sistema para consolidar os dados do DRE.</p>
    </div>

    <div v-else class="rounded-xl border border-gray-200 bg-white shadow-sm">
      <div class="flex flex-wrap items-center justify-between gap-3 rounded-t-xl border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white px-4 py-2.5">
        <div class="flex items-center gap-2">
          <div class="flex h-5 w-5 items-center justify-center rounded-full bg-[#373435] shadow-sm"><BarChart2 class="h-3 w-3 text-white" /></div>
          <span class="text-xs font-bold uppercase tracking-wider text-[#373435]">DRE Gerencial · Mensal</span>
        </div>
        <div class="flex items-center gap-3">
          <select v-model="anoSelecionado" class="rounded-md border border-gray-200 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300" aria-label="Ano do DRE mensal">
            <option v-for="ano in anosDisponiveis" :key="ano" :value="ano">{{ ano }}</option>
          </select>
          <label v-if="dados?.ano_consultado === anoSelecionado && dados?.mes_aberto" class="flex cursor-pointer items-center gap-2 rounded-md border border-gray-200 bg-white px-2.5 py-1 text-[10px] font-semibold text-gray-600">
            <input v-model="periodoEquivalente" type="checkbox" class="h-3.5 w-3.5 rounded border-gray-300 accent-[#373435]" />
            Períodos equivalentes
          </label>
        </div>
      </div>

      <div v-if="!erro && dados?.ano_consultado === anoSelecionado" class="border-b border-gray-100 px-4 py-2 text-[10px] text-gray-500">
        Último documento: {{ fmtData(dados.ultima_data_disponivel) }} · Agregados atualizados: {{ fmtMomento(dados.atualizado_em) }}
      </div>
      <div v-if="!erro && dados?.ano_consultado === anoSelecionado && dados?.periodo_equivalente" class="border-b border-gray-100 bg-gray-50/60 px-4 py-2 text-right text-[10px] text-gray-500">
        Meses comparados do dia 1 ao dia {{ dados.dia_corte }}; meses mais curtos usam seu último dia. O total soma os valores exibidos.
      </div>
      <div v-if="!erro && dados?.ano_consultado === anoSelecionado && dados?.desatualizado" class="border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800">
        Há períodos do DRE aguardando atualização. Último snapshot válido exibido.
      </div>
      <div v-if="!erro && dados?.ano_consultado === anoSelecionado && dados?.despesas_incompletas" class="border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800" role="status">
        Pagamentos indisponíveis em {{ dados.periodos_despesas_pendentes.slice(0, 5).map(p => `${p.mes}/${p.ano} (${p.status})`).join(', ') }}{{ dados.periodos_despesas_pendentes.length > 5 ? '…' : '' }}. Resultados e totais dependentes desses meses aparecem como —.
      </div>
      <div v-if="erro" class="border-b border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700" role="alert">
        {{ erro }}<span v-if="periodosPendentes.length"> Períodos pendentes: {{ periodosPendentes.slice(0, 5).map(p => `${p.mes}/${p.ano} (${p.status})`).join(', ') }}.</span>
      </div>
      <div v-if="loading" class="animate-pulse space-y-2 p-4"><div v-for="i in 5" :key="i" class="h-9 rounded bg-gray-100" /></div>
      <div v-else-if="dados && !erro && dados.ano_consultado === anoSelecionado" class="app-scrollbar overflow-x-auto">
        <table class="w-full text-sm">
          <thead><tr class="border-b border-gray-100">
            <th class="sticky left-0 z-10 w-36 bg-white px-11 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-400 shadow-[1px_0_0_#f3f4f6]">Métrica</th>
            <th v-for="(mes, indice) in MESES" :key="mes" class="min-w-[72px] px-2 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-400" :title="tooltipMesAberto(dados, indice)" :aria-label="tooltipMesAberto(dados, indice) || mes">{{ mes }}</th>
            <th class="min-w-[96px] px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-gray-500">{{ dados.periodo_equivalente ? 'Total comparável' : 'Total' }}</th>
          </tr></thead>
          <tbody>
            <tr v-for="(row, indice) in linhas" :key="row.label" class="border-b border-gray-50 last:border-0" :class="row.destaque ? 'bg-blue-50/40' : row.tipo === 'informativo' ? 'bg-gray-50/30' : indice % 2 ? 'bg-gray-50/60' : 'bg-white'">
              <td class="sticky left-0 z-10 px-4 py-2 text-xs text-gray-700 shadow-[1px_0_0_#f3f4f6]" :class="[row.destaque ? 'bg-blue-50/40' : row.tipo === 'informativo' ? 'bg-gray-50/30 pl-7 text-gray-500' : indice % 2 ? 'bg-gray-50/60' : 'bg-white', row.bold ? 'font-bold' : 'font-medium']">{{ row.label }}</td>
              <td v-for="(valor, mes) in row.meses" :key="mes" class="px-2 py-2 text-right font-mono text-xs tabular-nums" :class="row.tipo === 'informativo' ? 'text-gray-400' : numeroFinanceiro(valor) !== null ? 'text-gray-700' : 'text-gray-300'" :style="estiloMensal(row, valor, mes)">{{ row.fmt(valor) }}</td>
              <td class="px-4 py-2 text-right font-mono text-xs tabular-nums" :class="row.bold ? 'font-bold text-gray-800' : row.tipo === 'informativo' ? 'text-gray-400' : 'font-semibold text-gray-700'">{{ row.fmtT(row.total) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="dados && !erro" class="border-t border-gray-100 px-4 py-2 text-[10px] text-gray-500">Vendas pela data da venda; pagamentos pela data efetiva; compras pela emissão, apenas para consulta. A última data paga não comprova a cobertura da planilha de origem.</p>
    </div>
  </div>
</template>
