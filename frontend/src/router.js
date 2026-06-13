import { createRouter, createWebHistory } from "vue-router";
import MainLayout from "@/layouts/MainLayout.vue";
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
        redirect: "/validacao/produtos",
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
