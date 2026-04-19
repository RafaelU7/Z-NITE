// Tipos espelhando os DTOs do backend Zênite PDV

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface UsuarioPublicoDTO {
  id: string
  nome: string
  email: string
  perfil: string
  empresa_id: string
  codigo_operador: string | null
  ultimo_acesso: string | null
  ativo: boolean
}

// --- Caixa ---

export interface AbrirSessaoRequest {
  caixa_id: string
  saldo_abertura: number
}

export interface FecharSessaoRequest {
  saldo_informado_fechamento: number
  observacao?: string
}

export interface SessaoCaixaDTO {
  id: string
  empresa_id: string
  caixa_id: string
  operador_id: string
  status: 'aberta' | 'fechada'
  data_abertura: string
  saldo_abertura: string
  data_fechamento: string | null
  operador_fechamento_id: string | null
  saldo_informado_fechamento: string | null
  saldo_sistema_fechamento: string | null
  diferenca_fechamento: string | null
  total_vendas_bruto: string
  total_descontos: string
  total_liquido: string
  total_dinheiro: string
  total_pix: string
  total_cartao_debito: string
  total_cartao_credito: string
  total_outros: string
  quantidade_vendas: number
  ticket_medio: string | null
  observacao_fechamento: string | null
}

// --- Produto ---

export interface ProdutoDTO {
  id: string
  empresa_id: string
  sku: string | null
  codigo_barras_principal: string | null
  descricao: string
  descricao_pdv: string | null
  marca: string | null
  preco_venda: string
  custo_medio: string | null
  unidade_codigo: string | null
  controla_estoque: boolean
  pesavel: boolean
  perfil_tributario_id: string | null
  ncm: string | null
  cfop: string | null
  csosn: string | null
  cst_icms: string | null
  ativo: boolean
  destaque_pdv: boolean
  ean_pesquisado: string | null
  ean_fator_quantidade: string
}

// --- Venda ---

export type FormaPagamento =
  | '01'
  | '03'
  | '04'
  | '17'
  | '99'

export type TipoEmissao = 'FISCAL' | 'GERENCIAL'

export type StatusVenda = 'em_aberto' | 'concluida' | 'cancelada'

export interface IniciarVendaRequest {
  sessao_caixa_id: string
  chave_idempotencia?: string
  data_venda?: string
  origem_pdv?: string
}

export interface AdicionarItemRequest {
  produto_id: string
  quantidade: number
  preco_unitario?: number
  desconto_unitario?: number
}

export interface AdicionarPagamentoRequest {
  forma_pagamento: FormaPagamento
  valor: number
  troco?: number
  nsu?: string
  bandeira_cartao?: string
  autorizacao_cartao?: string
}

export interface ItemVendaDTO {
  id: string
  produto_id: string
  descricao_produto: string
  codigo_barras: string | null
  unidade: string | null
  sequencia: number
  quantidade: string
  preco_unitario: string
  desconto_unitario: string
  total_item: string
  cancelado: boolean
}

export interface PagamentoDTO {
  id: string
  forma_pagamento: FormaPagamento
  valor: string
  troco: string
  nsu: string | null
  bandeira_cartao: string | null
}

export interface VendaDTO {
  id: string
  empresa_id: string
  sessao_caixa_id: string
  operador_id: string
  numero_venda_local: number
  status: StatusVenda
  tipo_emissao: TipoEmissao
  data_venda: string
  total_bruto: string
  total_desconto: string
  total_liquido: string
  chave_idempotencia: string | null
  itens: ItemVendaDTO[]
  pagamentos: PagamentoDTO[]
  /** ID do DocumentoFiscal criado ao finalizar a venda */
  documento_fiscal_id?: string | null
}

// --- Fiscal ---

export type StatusDocumentoFiscal =
  | 'pendente'
  | 'emitida'
  | 'cancelada'
  | 'rejeitada'
  | 'em_contingencia'
  | 'inutilizada'
  | 'erro'

export interface DocumentoFiscalDTO {
  id: string
  empresa_id: string
  venda_id: string | null
  tipo: string
  status: StatusDocumentoFiscal
  ambiente: string
  numero: number | null
  serie: number | null
  chave_acesso: string | null
  tentativas: number
  proxima_tentativa_em: string | null
  data_emissao: string | null
  data_autorizacao: string | null
  protocolo_autorizacao: string | null
  codigo_retorno: string | null
  mensagem_retorno: string | null
  url_danfe: string | null
  url_qrcode: string | null
  provider_id: string | null
  criado_em: string | null
  atualizado_em: string | null
}

// --- Erros API ---
export interface ApiErrorDetail {
  detail: string
  code?: string
}

// --- Gerencial ---

export interface DashboardPagamentoPorForma {
  forma: string
  label: string
  total: string
  qtd: number
}

export interface DashboardDTO {
  data_referencia: string
  total_vendas: string
  qtd_vendas: number
  ticket_medio: string
  por_forma_pagamento: DashboardPagamentoPorForma[]
  sessoes_abertas: number
}

export interface ProdutoGerencialDTO {
  id: string
  sku: string | null
  codigo_barras_principal: string | null
  descricao: string
  descricao_pdv: string | null
  preco_venda: string
  unidade_id: string
  unidade_codigo: string | null
  perfil_tributario_id: string | null
  categoria_id: string | null
  controla_estoque: boolean
  ativo: boolean
  destaque_pdv: boolean
}

export interface PaginatedProdutos {
  items: ProdutoGerencialDTO[]
  total: number
  page: number
  per_page: number
}

export interface ProdutoCreateRequest {
  descricao: string
  descricao_pdv?: string
  codigo_barras_principal?: string
  sku?: string
  preco_venda: number
  unidade_id: string
  perfil_tributario_id?: string
  categoria_id?: string
  controla_estoque?: boolean
  ativo?: boolean
  destaque_pdv?: boolean
}

export interface ProdutoPatchRequest {
  descricao?: string
  descricao_pdv?: string
  preco_venda?: number
  ativo?: boolean
  destaque_pdv?: boolean
  perfil_tributario_id?: string
}

export interface UnidadeDTO {
  id: string
  codigo: string
  descricao: string
}

export interface PerfilTributarioSimpleDTO {
  id: string
  nome: string
}

export interface CategoriaDTO {
  id: string
  nome: string
  categoria_pai_id: string | null
  ativo: boolean
}

export interface UsuarioListDTO {
  id: string
  nome: string
  email: string
  perfil: string
  codigo_operador: string | null
  ativo: boolean
  ultimo_acesso: string | null
}

export interface UsuarioCreateRequest {
  nome: string
  email: string
  senha: string
  perfil?: string
  codigo_operador?: string
  pin?: string
}

export interface SessaoListDTO {
  id: string
  caixa_id: string
  caixa_descricao: string | null
  caixa_numero: number
  operador_id: string
  operador_nome: string
  status: string
  data_abertura: string
  data_fechamento: string | null
  total_liquido: string
  quantidade_vendas: number
}

export interface CaixaDTO {
  id: string
  numero: number
  descricao: string | null
  numero_serie: string | null
  ativo: boolean
}

export interface CaixaCreateRequest {
  numero: number
  descricao?: string
  numero_serie?: string
}
