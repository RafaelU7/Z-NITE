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
      <header className="flex items-center justify-between border-b border-border bg-white px-4 py-2.5 shadow-sm shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-amber-500/15 text-xs font-bold text-amber-700 ring-1 ring-amber-500/30">
            {getInitials(empresaNome)}
          </div>
          <div className="flex flex-col leading-tight">
            <span className="font-bold text-sm text-text-primary">{empresaNome}</span>
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] text-text-muted tracking-wide uppercase">Zênite PDV</span>
              <span className="rounded bg-amber-100 border border-amber-300 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-amber-700">
                Retaguarda
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-text-secondary">{user?.nome}</span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-text-secondary border border-border hover:bg-bg-surface-2 transition-colors"
          >
            <LogOut size={14} />
            Sair
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* ── Sidebar ── */}
        <nav className="flex w-48 shrink-0 flex-col gap-0.5 border-r border-white/10 bg-slate-900 p-3 overflow-y-auto">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm transition-colors',
                  isActive
                    ? 'bg-amber-500/20 text-amber-300 font-medium'
                    : 'text-slate-400 hover:bg-white/10 hover:text-slate-100',
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
