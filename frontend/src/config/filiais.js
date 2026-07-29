/**
 * Configuração das filiais disponíveis no sistema.
 * Cada filial aponta para uma instância independente do Django backend.
 * As URLs devem corresponder às portas configuradas em Iniciar_Sistema_Producao.bat.
 */
export const FILIAIS = [
  { id: 'henriques', nome: 'Filial Henrique',  apiUrl: 'http://127.0.0.1:8001' },
  { id: 'centro',    nome: 'Filial Centro',    apiUrl: 'http://127.0.0.1:8002' },
]
