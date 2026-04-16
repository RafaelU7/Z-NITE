import api from './client'
import type {
  SessaoCaixaDTO,
  AbrirSessaoRequest,
  FecharSessaoRequest,
} from '@/shared/types/api'

export async function abrirSessao(req: AbrirSessaoRequest): Promise<SessaoCaixaDTO> {
  const { data } = await api.post<SessaoCaixaDTO>('/caixa/sessoes', req)
  return data
}

export async function getSessaoAtiva(caixa_id: string): Promise<SessaoCaixaDTO> {
  const { data } = await api.get<SessaoCaixaDTO>('/caixa/sessao-ativa', {
    params: { caixa_id },
  })
  return data
}

export async function fecharSessao(
  sessao_id: string,
  req: FecharSessaoRequest,
): Promise<SessaoCaixaDTO> {
  const { data } = await api.post<SessaoCaixaDTO>(`/caixa/sessoes/${sessao_id}/fechar`, req)
  return data
}
