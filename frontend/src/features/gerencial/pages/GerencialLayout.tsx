import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Package, Users, CreditCard, LogOut, Store } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { logout } from '@/services/api/auth'
import clsx from 'clsx'

const NAV = [
  { to: '/gerencial', label: 'Dashboard', icon: <LayoutDashboard size={16} />, end: true },
  { to: '/gerencial/produtos', label: 'Produtos', icon: <Package size={16} /> },
  { to: '/gerencial/usuarios', label: 'Usuários', icon: <Users size={16} /> },
  { to: '/gerencial/caixas', label: 'Caixas', icon: <CreditCard size={16} /> },
  { to: '/gerencial/sessoes', label: 'Sessões', icon: <Store size={16} /> },
]

export function GerencialLayout() {
  const { user, clearSession } = useAuthStore()
  const navigate = useNavigate()

  async function handleLogout() {
    try { await logout() } catch { /* best-effort */ }
    clearSession()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex h-screen flex-col bg-bg-base">
      {/* Top bar */}
      <header className="flex items-center justify-between border-b border-border bg-bg-surface px-4 py-3">
        <div className="flex items-center gap-2 text-text-primary">
          <Store size={18} className="text-accent" />
          <span className="font-semibold text-sm">Zênite PDV — Retaguarda</span>
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
