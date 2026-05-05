import { Zap } from 'lucide-react'
import { PinLoginForm } from '../components/PinLoginForm'

export function LoginPage() {
  return (
    <div
      className="flex min-h-screen items-center justify-center p-4"
      style={{ background: 'radial-gradient(ellipse at 40% 45%, #0f3444 0%, #0a2030 50%, #07151d 100%)' }}
    >
      {/* Teal grid overlay — mesma linguagem do PDV */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(rgba(25,199,181,1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(25,199,181,1) 1px, transparent 1px)`,
          backgroundSize: '40px 40px',
        }}
      />
      {/* Glow radial sutil no centro */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{ background: 'radial-gradient(ellipse 600px 400px at 50% 50%, rgba(25,199,181,0.04) 0%, transparent 70%)' }}
      />

      <div className="relative w-full max-w-sm">
        {/* Card */}
        <div className="rounded-2xl border border-pdv-border bg-pdv-surface p-8 shadow-2xl shadow-black/50">
          {/* Logo / Brand */}
          <div className="mb-8 flex flex-col items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-accent/15 ring-1 ring-accent/30 shadow-lg shadow-accent/10">
              <Zap size={28} className="text-accent" fill="currentColor" />
            </div>
            <div className="text-center">
              <h1 className="text-xl font-bold tracking-tight text-text-primary">
                Zênite<span className="text-accent"> PDV</span>
              </h1>
              <p className="mt-0.5 text-sm text-text-muted">Automação Comercial</p>
            </div>
          </div>

          <PinLoginForm />
        </div>

        {/* Bottom hint */}
        <p className="mt-4 text-center text-xs text-text-muted">
          Use Tab / Enter para navegar entre campos
        </p>
      </div>
    </div>
  )
}
