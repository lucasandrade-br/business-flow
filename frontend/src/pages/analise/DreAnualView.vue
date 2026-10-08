<script setup>
import { computed } from 'vue'
import { BarChart2 } from 'lucide-vue-next'
import { useDre } from './useDre'
import { corVar, fmtData, fmtMomento, fmtP, fmtR, fmtRVar, fmtX, sgn } from './dreFormatters'

const { anosDisponiveis, anoSelecionado, periodoEquivalente, dados, loading, semDados, erro, periodosPendentes } = useDre('anual')
const anoAnterior = computed(() => anoSelecionado.value ? Number(anoSelecionado.value) - 1 : '')

function dataCurta(valor) {
  if (!valor) return ''
  const [, mes, dia] = valor.split('-')
  return `${dia}/${mes}`
}

const linhas = computed(() => {
  if (!dados.value?.visao_anual) return []
  const { receita, compras, despesas, resultado, resultado_percentual, fator_retorno } = dados.value.visao_anual
  const mgpA = resultado_percentual.atual, mgpB = resultado_percentual.anterior
  const fatA = fator_retorno.atual, fatB = fator_retorno.anterior
  return [
    {
      label: 'Receita Total', tipo: 'normal', bold: false, destaque: false,
      vAnt: fmtR(receita.anterior), vAtu: fmtR(receita.atual),
      nom: { v: receita.var_nominal, t: fmtRVar(receita.var_nominal) },
      rel: { v: receita.var_relativa, t: receita.var_relativa !== null ? `${sgn(receita.var_relativa)}${Number(receita.var_relativa).toFixed(1)}%` : '—' },
    },
    {
      label: 'Despesas totais', tipo: 'custo', bold: false, destaque: false,
      vAnt: fmtR(despesas.anterior), vAtu: fmtR(despesas.atual),
      nom: { v: despesas.var_nominal, t: fmtRVar(despesas.var_nominal) },
      rel: { v: despesas.var_relativa, t: despesas.var_relativa !== null ? `${sgn(despesas.var_relativa)}${Number(despesas.var_relativa).toFixed(1)}%` : '—' },
    },
    {
      label: 'Compras', tipo: 'informativo', bold: false, destaque: false,
      vAnt: fmtR(compras.anterior), vAtu: fmtR(compras.atual),
      nom: { v: compras.var_nominal, t: fmtRVar(compras.var_nominal) },
      rel: { v: compras.var_relativa, t: compras.var_relativa !== null ? `${sgn(compras.var_relativa)}${Number(compras.var_relativa).toFixed(1)}%` : '—' },
    },
    {
      label: 'Resultado operacional', tipo: 'normal', bold: true, destaque: true,
      vAnt: fmtR(resultado.anterior), vAtu: fmtR(resultado.atual),
      nom: { v: resultado.var_nominal, t: fmtRVar(resultado.var_nominal) },
      rel: { v: resultado.var_relativa, t: resultado.var_relativa !== null ? `${sgn(resultado.var_relativa)}${Number(resultado.var_relativa).toFixed(1)}%` : '—' },
    },
    {
      label: 'Resultado %', tipo: 'normal', bold: false, destaque: false,
      vAnt: fmtP(mgpB), vAtu: fmtP(mgpA), nom: { v: null, t: '—' },
      rel: {
        v: mgpA !== null && mgpB !== null ? mgpA - mgpB : null,
        t: mgpA !== null && mgpB !== null ? `${sgn(mgpA - mgpB)}${(mgpA - mgpB).toFixed(1)}%` : '—',
      },
    },
    {
      label: 'Fator de Retorno', tipo: 'normal', bold: false, destaque: false,
      vAnt: fmtX(fatB), vAtu: fmtX(fatA), nom: { v: null, t: '—' },
      rel: {
        v: fatA !== null && fatB !== null ? fatA - fatB : null,
        t: fatA !== null && fatB !== null ? `${sgn(fatA - fatB)}${(fatA - fatB).toFixed(2)}x` : '—',
      },
    },
  ]
})
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-xl font-bold text-gray-900">DRE Gerencial</h1>
      <p class="mt-0.5 text-sm text-gray-400">Receita de vendas, pagamentos de despesas e resultado gerencial por ano.</p>
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
          <span class="text-xs font-bold uppercase tracking-wider text-[#373435]">DRE Gerencial · Anual</span>
        </div>
        <div class="flex items-center gap-3">
          <select v-model="anoSelecionado" class="rounded-md border border-gray-200 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-300" aria-label="Ano do DRE anual">
            <option v-for="ano in anosDisponiveis" :key="ano" :value="ano">{{ ano }}</option>
          </select>
          <label class="flex cursor-pointer items-center gap-2 rounded-md border border-gray-200 bg-white px-2.5 py-1 text-[10px] font-semibold text-gray-600">
            <input v-model="periodoEquivalente" type="checkbox" class="h-3.5 w-3.5 rounded border-gray-300 accent-[#373435]" />
            Períodos equivalentes
          </label>
        </div>
      </div>

      <div v-if="!erro && dados?.ano_consultado === anoSelecionado" class="border-b border-gray-100 px-4 py-2 text-[10px] text-gray-500">
        Último documento: {{ fmtData(dados.ultima_data_disponivel) }} · Agregados atualizados: {{ fmtMomento(dados.atualizado_em) }}
      </div>
      <div v-if="!erro && dados?.ano_consultado === anoSelecionado && dados?.periodo_equivalente" class="border-b border-gray-100 bg-gray-50/60 px-4 py-2 text-right text-[10px] text-gray-500">
        Comparação de 01/01 a {{ dataCurta(dados.data_corte_atual) }} em ambos os anos
      </div>
      <div v-if="!erro && dados?.ano_consultado === anoSelecionado && dados?.desatualizado" class="border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800">
        Há períodos do DRE aguardando atualização. Último snapshot válido exibido.
      </div>
      <div v-if="!erro && dados?.ano_consultado === anoSelecionado && dados?.despesas_incompletas" class="border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800" role="status">
        Pagamentos indisponíveis em {{ dados.periodos_despesas_pendentes.slice(0, 5).map(p => `${p.mes}/${p.ano} (${p.status})`).join(', ') }}{{ dados.periodos_despesas_pendentes.length > 5 ? '…' : '' }}. Resultados dependentes desses meses aparecem como —.
      </div>
      <div v-if="erro" class="border-b border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700" role="alert">
        {{ erro }}<span v-if="periodosPendentes.length"> Períodos pendentes: {{ periodosPendentes.slice(0, 5).map(p => `${p.mes}/${p.ano} (${p.status})`).join(', ') }}.</span>
      </div>
      <div v-if="loading" class="animate-pulse space-y-2 p-4"><div v-for="i in 5" :key="i" class="h-9 rounded bg-gray-100" /></div>
      <div v-else-if="dados && !erro && dados.ano_consultado === anoSelecionado" class="app-scrollbar overflow-x-auto">
        <table class="w-full text-sm">
          <thead><tr class="border-b border-gray-100">
            <th class="w-40 px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-400">Métrica</th>
            <th class="px-4 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400">{{ anoAnterior }}</th>
            <th class="px-4 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-500">{{ anoSelecionado }}</th>
            <th class="px-4 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400">Var. Nominal</th>
            <th class="px-4 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider text-gray-400">Variação</th>
          </tr></thead>
          <tbody>
            <tr v-for="(row, indice) in linhas" :key="row.label" class="border-b border-gray-50 last:border-0" :class="row.destaque ? 'bg-blue-50/40' : row.tipo === 'informativo' ? 'bg-gray-50/30' : indice % 2 ? 'bg-gray-50/60' : 'bg-white'">
              <td class="px-4 py-2.5 text-xs text-gray-700" :class="row.tipo === 'informativo' ? 'pl-7 text-gray-500' : row.bold ? 'font-bold' : 'font-medium'">{{ row.label }}</td>
              <td class="px-4 py-2.5 text-right font-mono text-xs tabular-nums text-gray-400">{{ row.vAnt }}</td>
              <td class="px-4 py-2.5 text-right font-mono text-xs tabular-nums" :class="row.bold ? 'font-bold text-gray-800' : row.tipo === 'informativo' ? 'text-gray-400' : 'text-gray-700'">{{ row.vAtu }}</td>
              <td class="px-4 py-2.5 text-right font-mono text-xs font-semibold tabular-nums" :class="row.tipo === 'informativo' ? 'text-gray-400' : corVar(row.tipo, row.nom.v)">{{ row.nom.t }}</td>
              <td class="px-4 py-2.5 text-right font-mono text-xs font-semibold tabular-nums" :class="row.tipo === 'informativo' ? 'text-gray-400' : corVar(row.tipo, row.rel.v)">{{ row.rel.t }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="dados && !erro" class="border-t border-gray-100 px-4 py-2 text-[10px] text-gray-500">Vendas pela data da venda; pagamentos pela data efetiva; compras pela emissão, apenas para consulta. O corte segue os documentos da DRE; a última data paga não comprova a cobertura da planilha de origem.</p>
    </div>
  </div>
</template>
