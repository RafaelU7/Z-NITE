import axios, { AxiosError } from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios'

// Acessa o token em memória sem criar dependência circular com o store
let _accessToken: string | null = null
let _empresaId: string | null = null

export function setClientToken(token: string | null) {
  _accessToken = token
}

export function setClientEmpresaId(id: string | null) {
  _empresaId = id
}

// Em dev o Vite proxy encaminha /v1 → localhost:8000 (sem VITE_API_BASE_URL).
// Em produção (Vercel) defina VITE_API_BASE_URL=https://<seu-backend>.railway.app
const _apiBase = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/v1`
  : '/v1'

const api: AxiosInstance = axios.create({
  baseURL: _apiBase,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
})

// Injeta Authorization + X-Empresa-ID em cada requisição
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (_accessToken) {
    config.headers.Authorization = `Bearer ${_accessToken}`
  }
  if (_empresaId) {
    config.headers['X-Empresa-ID'] = _empresaId
  }
  return config
})

// Normaliza erros para sempre terem uma mensagem legível
api.interceptors.response.use(
  (res) => res,
  (error: AxiosError<{ detail?: unknown; message?: string }>) => {
    const raw = error.response?.data?.detail
    let detail: string
    if (Array.isArray(raw)) {
      // FastAPI 422: detail é lista de objetos de validação
      detail = raw
        .map((e: { msg?: string; message?: string }) => e.msg ?? e.message ?? JSON.stringify(e))
        .join(' · ')
    } else if (typeof raw === 'string') {
      detail = raw
    } else {
      detail =
        error.response?.data?.message ??
        error.message ??
        'Erro desconhecido'
    }
    return Promise.reject(new Error(detail))
  },
)

export default api
