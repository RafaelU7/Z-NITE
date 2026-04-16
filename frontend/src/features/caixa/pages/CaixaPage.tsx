import { useEffect, useState } from 'react'
import { Monitor, Zap, ArrowRight, LogOut } from 'lucide-react'
import { CaixaAberturaForm } from '../components/CaixaAberturaForm'
import { SessaoAtiva } from '../components/SessaoAtiva'
import { Button } from '@/shared/ui/Button'
import { getSessaoAtiva } from '@/services/api/caixa'
import { useAuthStore } from '@/store/authStore'
import { usePDVStore } from '@/store/pdvStore'
import { useNavigate } from 'react-router-dom'
import type { SessaoCaixaDTO } from '@/shared/types/api'

const CAIXA_ID_DEFAULT = import.meta.env.VITE_CAIXA_ID ?? ''

export function CaixaPage() {
  const { user, clearSession } = useAuthStore()
  const { sessaoCaixa, setSessaoCaixa } = usePDVStore()
  const navigate = useNavigate()
  const [sessaoAberta, setSessaoAberta] = useState<SessaoCaixaDTO | null>(sessaoCaixa)
  const [loadingSessao, setLoadingSessao] = useState(!!CAIXA_ID_DEFAULT && !sessaoCaixa)
  const [erroSessao, setErroSessao] = useState('')

  useEffect(() => {
    let cancelled = false

    async function loadSessaoAtiva() {
      if (!CAIXA_ID_DEFAULT || sessaoCaixa) {
        setLoadingSessao(false)
        return
      }

      try {
        const sessao = await getSessaoAtiva(CAIXA_ID_DEFAULT)
        if (cancelled) return
        setSessaoAberta(sessao)
        setSessaoCaixa(sessao)
      } catch (err) {
        if (cancelled) return
        if (err instanceof Error && err.message.includes('Nenhuma sessão aberta')) {
          setErroSessao('')
        } else {
          setErroSessao(err instanceof Error ? err.message : 'Erro ao carregar sessão do caixa.')
        }
      } finally {
        if (!cancelled) setLoadingSessao(false)
      }
    }

    loadSessaoAtiva()
    return () => {
      cancelled = true
    }
  }, [sessaoCaixa, setSessaoCaixa])

  function handleAberto(sessao: SessaoCaixaDTO) {
    setSessaoAberta(sessao)
    setSessaoCaixa(sessao)
  }

  function handleIrAoPDV() {
    navigate('/pdv')
  }

  function handleLogout() {
    clearSession()
    setSessaoCaixa(null)
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg-base p-4">
      {/* Background grid */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(rgba(99,102,241,1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(99,102,241,1) 1px, transparent 1px)`,
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative w-full max-w-md">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap size={20} className="text-accent" fill="currentColor" />
            <span className="font-bold text-text-primary">Zênite PDV</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-text-secondary">{user?.nome}</span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs text-text-muted hover:border-danger/40 hover:text-danger-text transition-colors"
            >
              <LogOut size={12} />
              Sair
            </button>
          </div>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-border bg-bg-surface p-8 shadow-2xl">
          <div className="mb-6 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-success/15 ring-1 ring-success/30">
              <Monitor size={22} className="text-success" />
            </div>
            <div>
              <h1 className="font-semibold text-text-primary">
                {sessaoAberta ? 'Sessão em Andamento' : 'Abrir Caixa'}
              </h1>
              <p className="text-sm text-text-muted">
                {sessaoAberta ? 'Já existe uma sessão aberta para este caixa' : 'Informe o fundo de troco para iniciar o turno'}
              </p>
            </div>
          </div>

          {loadingSessao ? (
            <div className="rounded-xl border border-border bg-bg-surface-2 p-5 text-sm text-text-secondary">
              Verificando sessão ativa do caixa...
            </div>
          ) : sessaoAberta ? (
            <div className="flex flex-col gap-4">
              <SessaoAtiva sessao={sessaoAberta} />
              <Button size="lg" fullWidth onClick={handleIrAoPDV}>
                <ArrowRight size={18} />
                Continuar Sessão
              </Button>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {erroSessao && (
                <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2.5 text-sm text-danger-text">
                  {erroSessao}
                </div>
              )}
              <CaixaAberturaForm onAberto={handleAberto} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
