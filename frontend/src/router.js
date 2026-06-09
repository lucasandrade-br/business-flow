import { createRouter, createWebHistory } from "vue-router";
import MainLayout from "@/layouts/MainLayout.vue";
import ValidacaoPendentes from "@/pages/Validacao/Pendentes.vue";
import DashboardReconciliacao from "@/pages/Validacao/DashboardReconciliacao.vue";
import Clientes from "@/pages/Cadastros/Clientes.vue";
import Fornecedores from "@/pages/Cadastros/Fornecedores.vue";
import Parametros from "@/pages/Cadastros/Parametros.vue";
import PlanoContas from "@/pages/Cadastros/PlanoContas.vue";
import ProdutosOficiais from "@/pages/Cadastros/ProdutosOficiais.vue";
import SistemaPainel from "@/pages/Sistema/Painel.vue";

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
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
