import api from './client'
import type { DocumentoFiscalDTO } from '@/shared/types/api'

export async function getDocumentoPorVenda(venda_id: string): Promise<DocumentoFiscalDTO> {
  const { data } = await api.get<DocumentoFiscalDTO>(`/fiscal/vendas/${venda_id}/documento`)
  return data
}

export async function getStatusDocumento(doc_id: string): Promise<DocumentoFiscalDTO> {
  const { data } = await api.get<DocumentoFiscalDTO>(`/fiscal/documentos/${doc_id}/status`)
  return data
}

export async function reprocessarDocumento(doc_id: string): Promise<DocumentoFiscalDTO> {
  const { data } = await api.post<DocumentoFiscalDTO>(
    `/fiscal/documentos/${doc_id}/reprocessar`,
    {},
  )
  return data
}
