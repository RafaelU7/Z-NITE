import { Zap } from 'lucide-react'
import { PinLoginForm } from '../components/PinLoginForm'

export function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-bg-base p-4">
      {/* Background grid effect */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(rgba(99,102,241,1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(99,102,241,1) 1px, transparent 1px)`,
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative w-full max-w-sm">
        {/* Card */}
        <div className="rounded-2xl border border-border bg-bg-surface p-8 shadow-2xl">
          {/* Logo / Brand */}
          <div className="mb-8 flex flex-col items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-accent/15 ring-1 ring-accent/30">
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
