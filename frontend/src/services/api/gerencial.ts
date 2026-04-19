import api from './client'
import type {
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
