import api from './client'
import type {
  CaixaDTO,
  CaixaCreateRequest,
  CategoriaDTO,
  DashboardDTO,
  PaginatedProdutos,
  ProdutoGerencialDTO,
  ProdutoCreateRequest,
  ProdutoPatchRequest,
  UnidadeDTO,
  PerfilTributarioSimpleDTO,
  UsuarioListDTO,
  UsuarioCreateRequest,
  SessaoListDTO,
  RelatorioDiarioDTO,
  EANLookupResult,
  CadastroRapidoRequest,
  CadastroRapidoResponse,
  AjusteEstoqueRequest,
  AjusteEstoqueResponse,
  PaginatedEstoque,
  EntradaEstoqueRequest,
  EntradaEstoqueResponse,
  InventarioRequest,
  InventarioResponse,
  PaginatedMovimentacoes,
} from '@/shared/types/api'

export async function getDashboard(): Promise<DashboardDTO> {
  const { data } = await api.get<DashboardDTO>('/gerencial/dashboard')
  return data
}

export async function listProdutos(params?: {
  q?: string
  page?: number
  per_page?: number
}): Promise<PaginatedProdutos> {
  const { data } = await api.get<PaginatedProdutos>('/gerencial/produtos', { params })
  return data
}

export async function createProduto(req: ProdutoCreateRequest): Promise<ProdutoGerencialDTO> {
  const { data } = await api.post<ProdutoGerencialDTO>('/gerencial/produtos', req)
  return data
}

export async function patchProduto(
  id: string,
  req: ProdutoPatchRequest,
): Promise<ProdutoGerencialDTO> {
  const { data } = await api.patch<ProdutoGerencialDTO>(`/gerencial/produtos/${id}`, req)
  return data
}

export async function listUnidades(): Promise<UnidadeDTO[]> {
  const { data } = await api.get<UnidadeDTO[]>('/gerencial/unidades')
  return data
}

export async function listCategorias(): Promise<CategoriaDTO[]> {
  const { data } = await api.get<CategoriaDTO[]>('/gerencial/categorias')
  return data
}

export async function listPerfisTributarios(): Promise<PerfilTributarioSimpleDTO[]> {
  const { data } = await api.get<PerfilTributarioSimpleDTO[]>('/gerencial/perfis-tributarios')
  return data
}

export async function listUsuarios(): Promise<UsuarioListDTO[]> {
  const { data } = await api.get<UsuarioListDTO[]>('/gerencial/usuarios')
  return data
}

export async function createUsuario(req: UsuarioCreateRequest): Promise<UsuarioListDTO> {
  const { data } = await api.post<UsuarioListDTO>('/gerencial/usuarios', req)
  return data
}

export async function patchUsuarioStatus(id: string, ativo: boolean): Promise<UsuarioListDTO> {
  const { data } = await api.patch<UsuarioListDTO>(`/gerencial/usuarios/${id}/status`, null, {
    params: { ativo },
  })
  return data
}

export async function listSessoes(limit?: number): Promise<SessaoListDTO[]> {
  const { data } = await api.get<SessaoListDTO[]>('/gerencial/sessoes', {
    params: limit ? { limit } : undefined,
  })
  return data
}

export async function listCaixas(): Promise<CaixaDTO[]> {
  const { data } = await api.get<CaixaDTO[]>('/gerencial/caixas')
  return data
}

export async function createCaixa(req: CaixaCreateRequest): Promise<CaixaDTO> {
  const { data } = await api.post<CaixaDTO>('/gerencial/caixas', req)
  return data
}

export async function patchCaixaStatus(id: string, ativo: boolean): Promise<CaixaDTO> {
  const { data } = await api.patch<CaixaDTO>(`/gerencial/caixas/${id}/status`, null, {
    params: { ativo },
  })
  return data
}

export async function lookupEAN(ean: string): Promise<EANLookupResult> {
  const { data } = await api.get<EANLookupResult>('/gerencial/produtos/lookup-ean', {
    params: { ean },
  })
  return data
}

export async function cadastroRapidoProduto(
  req: CadastroRapidoRequest,
): Promise<CadastroRapidoResponse> {
  const { data } = await api.post<CadastroRapidoResponse>('/gerencial/produtos/cadastro-rapido', req)
  return data
}

export async function ajusteEstoque(
  produtoId: string,
  req: AjusteEstoqueRequest,
): Promise<AjusteEstoqueResponse> {
  const { data } = await api.post<AjusteEstoqueResponse>(
    `/gerencial/produtos/${produtoId}/ajuste-estoque`,
    req,
  )
  return data
}

// --- Módulo de Estoque ---

export async function listEstoque(params?: {
  q?: string
  page?: number
  per_page?: number
}): Promise<PaginatedEstoque> {
  const { data } = await api.get<PaginatedEstoque>('/gerencial/estoque', { params })
  return data
}

export async function entradaEstoque(
  produtoId: string,
  req: EntradaEstoqueRequest,
): Promise<EntradaEstoqueResponse> {
  const { data } = await api.post<EntradaEstoqueResponse>(
    `/gerencial/produtos/${produtoId}/entrada-estoque`,
    req,
  )
  return data
}

export async function inventarioEstoque(
  produtoId: string,
  req: InventarioRequest,
): Promise<InventarioResponse> {
  const { data } = await api.post<InventarioResponse>(
    `/gerencial/produtos/${produtoId}/inventario`,
    req,
  )
  return data
}

export async function listMovimentacoes(params?: {
  produto_id?: string
  page?: number
  per_page?: number
}): Promise<PaginatedMovimentacoes> {
  const { data } = await api.get<PaginatedMovimentacoes>('/gerencial/movimentacoes', { params })
  return data
}

export async function getRelatorioDiario(data?: string): Promise<RelatorioDiarioDTO> {
  const { data: resp } = await api.get<RelatorioDiarioDTO>('/gerencial/relatorio-diario', {
    params: data ? { data } : undefined,
  })
  return resp
}

