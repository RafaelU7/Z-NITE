import api from './client'
import type { TokenResponse, UsuarioPublicoDTO } from '@/shared/types/api'

export interface PinLoginPayload {
  empresa_id: string
  codigo_operador: string
  pin: string
}

export async function pinLogin(payload: PinLoginPayload): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/auth/pin-login', payload)
  return data
}

export async function getMe(): Promise<UsuarioPublicoDTO> {
  const { data } = await api.get<UsuarioPublicoDTO>('/auth/me')
  return data
}

export async function logout(refresh_token?: string): Promise<void> {
  await api.post('/auth/logout', { refresh_token: refresh_token ?? null })
}
