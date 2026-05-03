import axios from 'axios'

const _apiBase = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/v1`
  : '/v1'

export interface SetupStatusDTO {
  setup_required: boolean
}

export interface SetupEmpresaRequest {
  empresa: {
    nome_fantasia: string
    razao_social?: string
    cnpj?: string
    telefone?: string
    logo_url?: string
  }
  gerente: {
    nome: string
    email?: string
    codigo_operador: string
    pin: string
  }
  caixa_descricao: string
}

export interface SetupEmpresaResponse {
  empresa_id: string
  gerente_id: string
  caixa_id: string
  mensagem: string
}

export async function getSetupStatus(): Promise<SetupStatusDTO> {
  const r = await axios.get<SetupStatusDTO>(`${_apiBase}/setup/status`)
  return r.data
}

export async function setupEmpresa(
  data: SetupEmpresaRequest,
): Promise<SetupEmpresaResponse> {
  const r = await axios.post<SetupEmpresaResponse>(`${_apiBase}/setup/empresa`, data)
  return r.data
}
