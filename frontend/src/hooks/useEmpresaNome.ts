import { useAuthStore } from '@/store/authStore'

const FALLBACK = import.meta.env.VITE_EMPRESA_NOME ?? 'Zênite PDV'

/** Retorna o nome da empresa na ordem: backend → VITE_EMPRESA_NOME → 'Zênite PDV' */
export function useEmpresaNome(): string {
  const empresaNome = useAuthStore((s) => s.empresaNome)
  return empresaNome ?? FALLBACK
}

export function getInitials(name: string): string {
  return name.split(' ').filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase()
}
