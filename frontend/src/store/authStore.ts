import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { setClientToken, setClientEmpresaId } from '@/services/api/client'
import type { UsuarioPublicoDTO } from '@/shared/types/api'

interface AuthState {
  // Token em memória — nunca vai para localStorage
  accessToken: string | null
  // Refresh token em sessionStorage (via persist)
  refreshToken: string | null
  user: UsuarioPublicoDTO | null
  empresaId: string | null
  empresaNome: string | null

  setSession: (
    accessToken: string,
    refreshToken: string,
    user: UsuarioPublicoDTO,
    empresaId: string,
  ) => void
  setEmpresaNome: (nome: string) => void
  clearSession: () => void
  isAuthenticated: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      empresaId: null,
      empresaNome: null,

      setSession(accessToken, refreshToken, user, empresaId) {
        // Sincroniza axios client imediatamente
        setClientToken(accessToken)
        setClientEmpresaId(empresaId)
        set({ accessToken, refreshToken, user, empresaId })
      },

      setEmpresaNome(nome) {
        set({ empresaNome: nome })
      },

      clearSession() {
        setClientToken(null)
        setClientEmpresaId(null)
        set({ accessToken: null, refreshToken: null, user: null, empresaId: null, empresaNome: null })
      },

      isAuthenticated() {
        return !!get().accessToken
      },
    }),
    {
      name: 'zenite-auth',
      storage: createJSONStorage(() => sessionStorage),
      // accessToken fica apenas em memória — mas para a sessão sobreviver
      // ao refresh de página, persistimos tudo em sessionStorage.
      // Para ambiente de produção, usar refresh-token rotation com HttpOnly cookie.
      partialize: (state) => ({
        user: state.user,
        empresaId: state.empresaId,
        empresaNome: state.empresaNome,
        refreshToken: state.refreshToken,
        // accessToken NÃO é persistido — requer re-login após fechar tab
        accessToken: state.accessToken,
      }),
    },
  ),
)

// Rehidrata o axios client ao carregar a página (sessionStorage restore)
const stored = sessionStorage.getItem('zenite-auth')
if (stored) {
  try {
    const parsed = JSON.parse(stored) as { state?: { accessToken?: string; empresaId?: string } }
    if (parsed?.state?.accessToken) setClientToken(parsed.state.accessToken)
    if (parsed?.state?.empresaId) setClientEmpresaId(parsed.state.empresaId)
  } catch {
    /* ignora parse error */
  }
}
