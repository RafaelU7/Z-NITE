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
