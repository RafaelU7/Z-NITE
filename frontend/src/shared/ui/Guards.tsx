import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { usePDVStore } from '@/store/pdvStore'

export function RequireAuth({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated())
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

export function RequireCaixa({ children }: { children: ReactNode }) {
  const sessaoCaixa = usePDVStore((s) => s.sessaoCaixa)
  if (!sessaoCaixa) return <Navigate to="/caixa" replace />
  return <>{children}</>
}

const PERFIS_GERENCIAIS = ['gerente', 'admin', 'super_admin']

export function RequireGerente({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated())
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!PERFIS_GERENCIAIS.includes(user!.perfil)) return <Navigate to="/pdv" replace />
  return <>{children}</>
}
