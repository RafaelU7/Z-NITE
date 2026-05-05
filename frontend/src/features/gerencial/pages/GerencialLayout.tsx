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
      {/* ── Top bar ── */}
      <header className="flex items-center justify-between border-b border-border bg-[#060f15] px-4 py-2.5 shadow-sm shadow-black/40 shrink-0 z-10">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-pdv-gerencial/15 text-xs font-bold text-pdv-gerencial ring-1 ring-pdv-gerencial/30">
            {getInitials(empresaNome)}
          </div>
          <div className="flex flex-col leading-tight">
            <span className="font-bold text-sm text-text-primary">{empresaNome}</span>
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] text-text-muted tracking-wide uppercase">Zênite PDV</span>
              <span className="rounded-md bg-pdv-gerencial/15 border border-pdv-gerencial/40 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-pdv-gerencial">
                Retaguarda
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-text-secondary font-medium">Admin {user?.nome}</span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-text-muted border border-border hover:border-danger/40 hover:text-danger-text transition-colors"
          >
            <LogOut size={14} />
            Sair
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* ── Sidebar ── */}
        <nav className="flex w-48 shrink-0 flex-col gap-0.5 border-r border-border bg-[#060f15] p-3 overflow-y-auto">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm transition-colors',
                  isActive
                    ? 'bg-pdv-gerencial/20 text-pdv-gerencial font-medium'
                    : 'text-text-muted hover:bg-white/5 hover:text-text-secondary',
                )
              }
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* ── Content ── */}
        <main className="flex-1 overflow-auto p-6 bg-bg-base">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
