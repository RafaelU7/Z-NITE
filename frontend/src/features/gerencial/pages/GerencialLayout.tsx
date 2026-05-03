import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Package, Users, CreditCard, LogOut, Zap, Warehouse, BarChart2, Store } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { logout } from '@/services/api/auth'
import { useEmpresaNome, getInitials } from '@/hooks/useEmpresaNome'
import clsx from 'clsx'

const NAV = [
  { to: '/gerencial', label: 'Dashboard', icon: <LayoutDashboard size={16} />, end: true },
  { to: '/gerencial/produtos', label: 'Produtos', icon: <Package size={16} /> },
  { to: '/gerencial/cadastro-rapido', label: 'Cadastro Rápido', icon: <Zap size={16} /> },
  { to: '/gerencial/estoque', label: 'Estoque', icon: <Warehouse size={16} /> },
  { to: '/gerencial/usuarios', label: 'Usuários', icon: <Users size={16} /> },
  { to: '/gerencial/caixas', label: 'Caixas', icon: <CreditCard size={16} /> },
  { to: '/gerencial/sessoes', label: 'Sessões', icon: <Store size={16} /> },
  { to: '/gerencial/relatorio-diario', label: 'Rel. Diário', icon: <BarChart2 size={16} /> },
]

export function GerencialLayout() {
  const { user, clearSession } = useAuthStore()
  const navigate = useNavigate()
  const empresaNome = useEmpresaNome()

  async function handleLogout() {
    try { await logout() } catch { /* best-effort */ }
    clearSession()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex h-screen flex-col bg-bg-base">
      {/* Top bar */}
      <header className="flex items-center justify-between border-b border-border bg-bg-surface px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/20 text-xs font-bold text-accent">
            {getInitials(empresaNome)}
          </div>
          <div className="flex flex-col leading-tight">
            <span className="font-semibold text-sm text-text-primary">{empresaNome}</span>
            <span className="text-[10px] text-text-muted tracking-wide uppercase">Zênite PDV — Retaguarda</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-text-muted">{user?.nome}</span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-text-secondary hover:bg-bg-surface-2 transition-colors"
          >
            <LogOut size={14} />
            Sair
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <nav className="flex w-48 flex-col gap-1 border-r border-border bg-bg-surface p-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm transition-colors',
                  isActive
                    ? 'bg-accent/15 text-accent font-medium'
                    : 'text-text-secondary hover:bg-bg-surface-2 hover:text-text-primary',
                )
              }
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
