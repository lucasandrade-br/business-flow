import { createRouter, createWebHistory } from "vue-router";
import MainLayout from "@/layouts/MainLayout.vue";
import HomeView from "@/pages/HomeView.vue";
import ValidacaoPendentes from "@/pages/Validacao/Pendentes.vue";
import DashboardReconciliacao from "@/pages/Validacao/DashboardReconciliacao.vue";
import Clientes from "@/pages/Cadastros/Clientes.vue";
import Compras from "@/pages/Compras/Compras.vue";
import Fornecedores from "@/pages/Cadastros/Fornecedores.vue";
import ItensCompra from "@/pages/Compras/ItensCompra.vue";
import Parametros from "@/pages/Cadastros/Parametros.vue";
import PlanoContas from "@/pages/Cadastros/PlanoContas.vue";
import ProdutosOficiais from "@/pages/Cadastros/ProdutosOficiais.vue";
import SistemaPainel from "@/pages/Sistema/Painel.vue";
import ReconciliacaoCompras from "@/pages/Compras/ReconciliacaoCompras.vue";
import ItensVenda from "@/pages/Vendas/ItensVenda.vue";
import PagamentosVenda from "@/pages/Vendas/PagamentosVenda.vue";
import Vendas from "@/pages/Vendas/Vendas.vue";

const routes = [
  {
    path: "/",
    component: MainLayout,
    children: [
      {
        path: "",
        name: "home",
        component: HomeView,
      },
      {
        path: "dashboard",
        redirect: "/analise/visao-geral",
      },
      {
        path: "analise",
        component: () => import("@/layouts/AnaliseLayout.vue"),
        children: [
          { path: "", redirect: "/analise/visao-geral" },
          {
            path: "visao-geral",
            redirect: (to) => ({ path: "/analise/visao-geral/anual", query: to.query }),
          },
          {
            path: "visao-geral/anual",
            name: "analise-dre-anual",
            component: () => import("@/pages/analise/DreAnualView.vue"),
            meta: { title: "DRE Anual" },
          },
          {
            path: "visao-geral/mensal",
            name: "analise-dre-mensal",
            component: () => import("@/pages/analise/DreMensalView.vue"),
            meta: { title: "DRE Mensal" },
          },
          {
            path: "vendas",
            name: "analise-vendas",
            component: () => import("@/pages/analise/VendasView.vue"),
            meta: { title: "Vendas" },
          },
          {
            path: "movimento-clientes",
            name: "analise-movimento-clientes",
            component: () => import("@/pages/analise/MovimentoClientesView.vue"),
            meta: { title: "Movimento de Clientes" },
          },
          {
            path: "compras",
            name: "analise-compras",
            component: () => import("@/pages/analise/ComprasView.vue"),
            meta: { title: "Compras" },
          },
          {
            path: "categorias/vendas",
            name: "analise-categorias-vendas",
            component: () => import("@/pages/analise/VendasCategoriasView.vue"),
            meta: { title: "Vendas por Categoria" },
          },
          {
            path: "categorias/vendas/quarentena",
            name: "analise-categorias-vendas-quarentena",
            component: () => import("@/pages/analise/VendasQuarentenaView.vue"),
            meta: { title: "Categorias em Quarentena" },
          },
          {
            path: "categorias/produtos/vendas",
            name: "analise-categorias-produtos-vendas",
            component: () => import("@/pages/analise/VendasProdutosView.vue"),
            meta: { title: "Vendas por Produto" },
          },
          {
            path: "categorias/compras",
            name: "analise-categorias-compras",
            component: () => import("@/pages/analise/ComprasCategoriasView.vue"),
            meta: { title: "Compras por Categoria" },
          },
          {
            path: "categorias/produtos/compras",
            name: "analise-categorias-produtos-compras",
            component: () => import("@/pages/analise/ComprasProdutosView.vue"),
            meta: { title: "Compras por Produto" },
          },
          {
            path: "despesas",
            name: "analise-despesas",
            component: () => import("@/pages/Despesas/DespesasBIView.vue"),
            meta: { title: "Despesas" },
          },
          {
            path: "despesas/tipos",
            name: "analise-despesas-tipos",
            component: () => import("@/pages/Despesas/DespesasBITiposView.vue"),
            meta: { title: "Despesas por Tipo" },
          },
        ],
      },
      {
        path: "validacao/produtos",
        name: "validacao-produtos",
        component: ValidacaoPendentes,
      },
      {
        path: "validacao/reconciliacao",
        name: "validacao-reconciliacao",
        component: DashboardReconciliacao,
      },
      {
        path: "compras/reconciliacao",
        name: "compras-reconciliacao",
        component: ReconciliacaoCompras,
      },
      {
        path: "compras/compras",
        name: "compras-compras",
        component: Compras,
      },
      {
        path: "compras/itens",
        name: "compras-itens",
        component: ItensCompra,
      },
      { path: "despesas/tipos", component: () => import("@/pages/Despesas/DespesasTiposView.vue") },
      { path: "despesas/movimentos", component: () => import("@/pages/Despesas/DespesasMovimentosView.vue") },
      { path: "despesas/captura", component: () => import("@/pages/Despesas/DespesasCapturaView.vue") },
      {
        path: "cadastros/plano-contas",
        name: "cadastros-plano-contas",
        component: PlanoContas,
      },
      {
        path: "cadastros/produtos",
        name: "cadastros-produtos",
        component: ProdutosOficiais,
      },
      {
        path: "cadastros/unidades-medida",
        redirect: "/cadastros/parametros",
      },
      {
        path: "cadastros/clientes",
        name: "cadastros-clientes",
        component: Clientes,
      },
      {
        path: "cadastros/fornecedores",
        name: "cadastros-fornecedores",
        component: Fornecedores,
      },
      {
        path: "cadastros/parametros",
        name: "cadastros-parametros",
        component: Parametros,
      },
      {
        path: "sistema",
        name: "sistema",
        component: SistemaPainel,
      },
      {
        path: "vendas/vendas",
        name: "vendas-vendas",
        component: Vendas,
      },
      {
        path: "vendas/itens",
        name: "vendas-itens",
        component: ItensVenda,
      },
      {
        path: "vendas/pagamentos",
        name: "vendas-pagamentos",
        component: PagamentosVenda,
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
