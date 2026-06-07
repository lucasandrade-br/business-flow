# **Documento Base de Conhecimento: Design System e Interface do Usuário (UI/UX)**

###### **1. Visão Geral (Filosofia de Design)**

A interface do sistema adota o padrão Data-Dense Minimalist (Minimalismo Focado em Dados). O objetivo principal é reduzir a carga cognitiva do operador durante rotinas de aprovação em massa. O sistema reflete a identidade visual da empresa de forma estratégica, comportando-se visualmente como um SaaS corporativo premium.

Nenhum elemento visual existe apenas por decoração; cores, sombras e formas indicam hierarquia e funcionalidade.



###### **2. Paleta de Cores e Aplicação Estratégica**

A paleta baseia-se na logomarca corporativa, traduzida para os padrões de usabilidade digital para evitar fadiga visual.

Elemento UI | Cor (Hex) | Aplicação no Sistema

Texto Principal | #373435 | "Textos padronizados, títulos de modais e conteúdo interno das tabelas. O contraste suave garante conforto em leituras prolongadas."

Superfície Primária | #dbc8b7 | "Menu lateral (Sidebar) e fundos de destaque. Envolve a aplicação, enquanto a área principal de dados (tabelas) mantém fundo #FFFFFF para máximo contraste."

Destaque Secundário | #e69551 | "Alertas de sistema e Badges (etiquetas) de status. Ideal para sinalizar itens ""Aguardando Categorização"" ou ""Dados Modificados"" (Diffs)."

Ação Primária (CTA) | #a82631 | "Botões de ação definitiva (""Aprovar e Salvar""), checkboxes ativos e abas selecionadas. É a âncora de atenção do operador."

Linhas e Bordas | #6b270e | "Aplicada com baixa opacidade (15% a 30%) para construir as divisões horizontais das tabelas e bordas sutis de formulários, sem poluir a tela."



###### **3. Geometria e Profundidade (Física da Interface)**

O sistema abandona o uso excessivo de sombras escuras e cantos pontiagudos em favor de uma geometria suave e camadas lógicas (Eixo Z).

Arredondamento (Border-Radius):

6px a 8px: Aplicado em todos os cartões principais, painéis e modais.

4px: Aplicado em campos de digitação (Inputs) e botões internos para transmitir precisão.

Elevação e Sombreamento (Drop Shadows):

Nível Base (Flat): Tabelas e painéis de dados não possuem sombra, apenas bordas de 1px usando a cor #6b270e transparente.

Nível Interação (Hover): Sombras incrivelmente difusas (0 4px 6px -1px rgba(0,0,0,0.05)) acionadas apenas quando o cursor repousar sobre linhas clicáveis ou botões secundários.

Nível Sobreposição (Modais): Sombras largas e esfumaçadas ao redor dos modais de validação para isolar o componente e ofuscar o fundo da aplicação.



###### **4. Estrutura de Componentes e Micro-interações**

O comportamento mecânico das peças da interface deve transmitir resposta tátil e alto desempenho.

Tabelas de Dados (DataTables): \* Foco absoluto no alinhamento. Divisores estritamente horizontais (linhas inferiores de 1px).

Sem linhas verticais separando colunas; o espaçamento em branco (padding) organiza a informação.

Feedback de Ações (Toasts/Alerts):

Renderizados de forma flutuante no canto inferior direito da tela.

Animação de entrada deslizando de baixo para cima (250ms ease-out).

Estrutura visual: Fundo branco, elevação suave e uma barra de destaque na borda esquerda indicando a natureza da notificação (Sucesso, Aviso ou Erro).

Transições e Estados (Hover/Focus):

Toda alteração de estado (um botão mudando de cor ao passar o mouse) ocorrerá com uma transição suave de 150ms. Elementos acendem suavemente, nunca piscam de forma abrupta.



###### **5. Arquitetura de Front-end Orientada a Componentes**

Tecnologia Base: Vue.js 3 (Composition API).

Estrutura Visual: Padrão Single-File Component (.vue), onde estrutura (HTML), lógica de consumo da API Django (JS) e estilização com CSS protegido (scoped) coexistem no mesmo arquivo.

Aceleração de UI: Utilização de bibliotecas Headless ou Unstyled (como Shadcn-vue ou PrimeVue) para injetar a paleta e os traços definidos acima sem herdar estilos engessados de terceiros.

