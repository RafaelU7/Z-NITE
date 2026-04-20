import axios from 'axios'

const _apiBase = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/v1`
  : '/v1'

export interface SetupStatusDTO {
  necessita_setup: boolean
}

export interface SetupInicializarRequest {
  empresa: {
    razao_social: string
    nome_fantasia?: string
    cnpj: string
    regime_tributario: 'SN' | 'SNE' | 'LP' | 'LR'
  }
  gerente: {
    nome: string
    email: string
    senha: string
    codigo_operador: string
    pin: string
  }
  operador: {
    nome: string
    email: string
    codigo_operador: string
    pin: string
  }
  caixa_descricao: string
}

export interface SetupInicializarResponse {
  empresa_id: string
  gerente_id: string
  operador_id: string
  caixa_id: string
  mensagem: string
}

export async function getSetupStatus(): Promise<SetupStatusDTO> {
  const r = await axios.get<SetupStatusDTO>(`${_apiBase}/setup/status`)
  return r.data
}

export async function inicializarSistema(
  data: SetupInicializarRequest,
): Promise<SetupInicializarResponse> {
  const r = await axios.post<SetupInicializarResponse>(`${_apiBase}/setup/inicializar`, data)
  return r.data
}
