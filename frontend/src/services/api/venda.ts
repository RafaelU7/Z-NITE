import api from './client'
import type {
  VendaDTO,
  IniciarVendaRequest,
  AdicionarItemRequest,
  AdicionarPagamentoRequest,
  TipoEmissao,
} from '@/shared/types/api'

export async function iniciarVenda(req: IniciarVendaRequest): Promise<VendaDTO> {
  const { data } = await api.post<VendaDTO>('/vendas/', req)
  return data
}

export async function getVenda(venda_id: string): Promise<VendaDTO> {
  const { data } = await api.get<VendaDTO>(`/vendas/${venda_id}`)
  return data
}

export async function adicionarItem(
  venda_id: string,
  req: AdicionarItemRequest,
): Promise<VendaDTO> {
  const { data } = await api.post<VendaDTO>(`/vendas/${venda_id}/itens`, req)
  return data
}

export async function removerItem(venda_id: string, item_id: string): Promise<VendaDTO> {
  const { data } = await api.delete<VendaDTO>(`/vendas/${venda_id}/itens/${item_id}`)
  return data
}

export async function adicionarPagamento(
  venda_id: string,
  req: AdicionarPagamentoRequest,
): Promise<VendaDTO> {
  const { data } = await api.post<VendaDTO>(`/vendas/${venda_id}/pagamentos`, req)
  return data
}

export async function finalizarVenda(
  venda_id: string,
  tipoEmissao: TipoEmissao = 'FISCAL',
): Promise<VendaDTO> {
  const { data } = await api.post<VendaDTO>(`/vendas/${venda_id}/finalizar`, {
    tipo_emissao: tipoEmissao,
  })
  return data
}
