import { useEffect, useRef, useState } from 'react'
import { Monitor, Zap, ArrowRight, LogOut, X, LockKeyhole, CheckCircle2, AlertTriangle } from 'lucide-react'
import { CaixaAberturaForm } from '../components/CaixaAberturaForm'
import { SessaoAtiva } from '../components/SessaoAtiva'
import { Button } from '@/shared/ui/Button'
import { getSessaoAtiva, fecharSessao } from '@/services/api/caixa'
import { useAuthStore } from '@/store/authStore'
import { usePDVStore } from '@/store/pdvStore'
import { useNavigate } from 'react-router-dom'
import { formatCurrency, formatDateTime } from '@/shared/utils/format'
import type { SessaoCaixaDTO } from '@/shared/types/api'
import clsx from 'clsx'

function filterDecimal(v: string) {
  return v.replace(/[^0-9.,]/g, '').replace(',', '.')
}

const CAIXA_ID_DEFAULT = import.meta.env.VITE_CAIXA_ID ?? ''
const TEM_CAIXA_ID_CONFIGURADO = CAIXA_ID_DEFAULT.trim().length > 0

// ---------------------------------------------------------------------------
// Modal de fechamento de caixa
// ---------------------------------------------------------------------------
interface ModalFecharProps {
  sessao: SessaoCaixaDTO
  onClose: () => void
  onFechado: (sessaoFechada: SessaoCaixaDTO) => void
}

function ModalFecharCaixa({ sessao, onClose, onFechado }: ModalFecharProps) {
  const [valorContado, setValorContado] = useState('')
  const [observacao, setObservacao] = useState('')
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const valor = parseFloat(filterDecimal(valorContado))
    if (isNaN(valor) || valor < 0) {
      setErro('Informe o valor contado em dinheiro.')
      return
    }
    setLoading(true)
    setErro('')
    try {
      const fechada = await fecharSessao(sessao.id, {
        saldo_informado_fechamento: valor,
        observacao: observacao.trim() || undefined,
      })
      onFechado(fechada)
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Erro ao fechar o caixa.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-bg-surface p-6 shadow-2xl">
        <div className="mb-5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <LockKeyhole size={18} className="text-warning-text" />
            <h2 className="font-semibold text-text-primary">Fechar Caixa</h2>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">
            <X size={18} />
          </button>
        </div>

        {/* Info da sessão */}
        <div className="mb-4 rounded-xl border border-border bg-bg-surface-2 p-4 text-sm">
          <div className="grid grid-cols-2 gap-2 text-text-secondary">
            <span className="text-text-muted">Abertura:</span>
            <span>{formatDateTime(sessao.data_abertura)}</span>
            <span className="text-text-muted">Vendas:</span>
            <span>{sessao.quantidade_vendas}</span>
            <span className="text-text-muted">Total vendido:</span>
            <span className="font-mono font-medium text-text-primary">
              {formatCurrency(Number(sessao.total_liquido))}
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-text-primary">
              Valor contado em dinheiro (R$)
            </label>
            <input
              ref={inputRef}
              type="text"
              inputMode="decimal"
              placeholder="0,00"
              value={valorContado}
              onChange={(e) => setValorContado(e.target.value)}
              className="w-full rounded-lg border border-border bg-bg-base px-3 py-2.5 text-sm text-text-primary placeholder-text-muted focus:border-accent focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-text-secondary">
              Observação (opcional)
            </label>
            <textarea
              rows={2}
              placeholder="Ex: sem diferença, conferido..."
              value={observacao}
              onChange={(e) => setObservacao(e.target.value)}
              className="w-full resize-none rounded-lg border border-border bg-bg-base px-3 py-2.5 text-sm text-text-primary placeholder-text-muted focus:border-accent focus:outline-none"
            />
          </div>

          {erro && (
            <p className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger-text">
              {erro}
            </p>
          )}

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border border-border py-2.5 text-sm text-text-secondary hover:bg-bg-surface-2 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-lg bg-warning/90 py-2.5 text-sm font-semibold text-white hover:bg-warning transition-colors disabled:opacity-50"
            >
              {loading ? 'Fechando...' : 'Confirmar Fechamento'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Resumo pós-fechamento
// ---------------------------------------------------------------------------
function ResumoFechamento({ sessao }: { sessao: SessaoCaixaDTO }) {
  const diferenca = Number(sessao.diferenca_fechamento ?? 0)
  const positivo = diferenca >= 0

  const formas = [
    { label: 'Dinheiro', valor: Number(sessao.total_dinheiro) },
    { label: 'Pix', valor: Number(sessao.total_pix) },
    { label: 'Cartão Débito', valor: Number(sessao.total_cartao_debito) },
    { label: 'Cartão Crédito', valor: Number(sessao.total_cartao_credito) },
    { label: 'Outros', valor: Number(sessao.total_outros) },
  ].filter((f) => f.valor > 0)

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2 rounded-xl border border-success/30 bg-success/10 px-4 py-3">
        <CheckCircle2 size={18} className="text-success-text shrink-0" />
        <span className="text-sm font-medium text-success-text">Caixa fechado com sucesso!</span>
      </div>

      <div className={clsx(
        'flex items-center justify-between rounded-xl border px-4 py-3',
        positivo ? 'border-success/30 bg-success/10' : 'border-danger/30 bg-danger/10',
      )}>
        <div className="flex items-center gap-2">
          <AlertTriangle size={15} className={positivo ? 'text-success-text' : 'text-danger-text'} />
          <span className={clsx('text-sm font-medium', positivo ? 'text-success-text' : 'text-danger-text')}>
            Diferença de caixa
          </span>
        </div>
        <span className={clsx('font-mono font-bold text-lg', positivo ? 'text-success-text' : 'text-danger-text')}>
          {positivo ? '+' : ''}{formatCurrency(diferenca)}
        </span>
      </div>

      <div className="rounded-xl border border-border bg-bg-surface-2 p-4 text-sm">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-muted">Resumo</p>
        <div className="flex flex-col gap-1.5">
          <div className="flex justify-between">
            <span className="text-text-muted">Total vendido</span>
            <span className="font-mono font-semibold text-text-primary">{formatCurrency(Number(sessao.total_liquido))}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Vendas</span>
            <span className="text-text-secondary">{sessao.quantidade_vendas}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Esperado em dinheiro</span>
            <span className="font-mono text-text-secondary">{formatCurrency(Number(sessao.saldo_sistema_fechamento ?? 0))}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Contado em dinheiro</span>
            <span className="font-mono text-text-secondary">{formatCurrency(Number(sessao.saldo_informado_fechamento ?? 0))}</span>
          </div>
          {formas.length > 0 && (
            <>
              <div className="my-1.5 border-t border-border" />
              {formas.map((f) => (
                <div key={f.label} className="flex justify-between">
                  <span className="text-text-muted">{f.label}</span>
                  <span className="font-mono text-text-secondary">{formatCurrency(f.valor)}</span>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Página principal
// ---------------------------------------------------------------------------
export function CaixaPage() {
  const { user, clearSession } = useAuthStore()
  const { sessaoCaixa, setSessaoCaixa } = usePDVStore()
  const navigate = useNavigate()
  const [sessaoAberta, setSessaoAberta] = useState<SessaoCaixaDTO | null>(sessaoCaixa)
  const [loadingSessao, setLoadingSessao] = useState(!!(sessaoCaixa?.caixa_id || CAIXA_ID_DEFAULT))
  const [erroSessao, setErroSessao] = useState('')
  const [modalFecharAberto, setModalFecharAberto] = useState(false)
  const [sessaoFechada, setSessaoFechada] = useState<SessaoCaixaDTO | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadSessaoAtiva() {
      // Sempre re-busca ao montar: obtém dados frescos e detecta sessão de dia anterior
      const caixaId = sessaoCaixa?.caixa_id || CAIXA_ID_DEFAULT
      if (!caixaId) {
        setLoadingSessao(false)
        return
      }

      try {
        const sessao = await getSessaoAtiva(caixaId)
        if (cancelled) return
        setSessaoAberta(sessao)
        setSessaoCaixa(sessao)
      } catch (err) {
        if (cancelled) return
        // Limpa sessão obsoleta do store (auto-encerrada ou não encontrada)
        setSessaoAberta(null)
        setSessaoCaixa(null)
        if (!(err instanceof Error && err.message.includes('Nenhuma sessão aberta'))) {
          setErroSessao(err instanceof Error ? err.message : 'Erro ao carregar sessão do caixa.')
        }
      } finally {
        if (!cancelled) setLoadingSessao(false)
      }
    }

    loadSessaoAtiva()
    return () => { cancelled = true }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function handleAberto(sessao: SessaoCaixaDTO) {
    setSessaoAberta(sessao)
    setSessaoCaixa(sessao)
    setSessaoFechada(null)
  }

  function handleIrAoPDV() {
    navigate('/pdv')
  }

  function handleLogout() {
    clearSession()
    setSessaoCaixa(null)
    navigate('/login', { replace: true })
  }

  function handleFechado(sessao: SessaoCaixaDTO) {
    setSessaoFechada(sessao)
    setSessaoAberta(null)
    setSessaoCaixa(null)   // Limpa a sessão do store → PDV bloqueado
    setModalFecharAberto(false)
  }

  const sessaoIsAberta = sessaoAberta?.status === 'aberta'

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
            <div className={clsx(
              'flex h-11 w-11 items-center justify-center rounded-xl ring-1',
              sessaoIsAberta
                ? 'bg-success/15 ring-success/30'
                : sessaoFechada
                  ? 'bg-text-muted/10 ring-border'
                  : 'bg-accent/10 ring-accent/30',
            )}>
              <Monitor size={22} className={sessaoIsAberta ? 'text-success' : 'text-text-muted'} />
            </div>
            <div>
              <h1 className="font-semibold text-text-primary">
                {sessaoIsAberta
                  ? 'Sessão em Andamento'
                  : sessaoFechada
                    ? 'Sessão Encerrada'
                    : 'Abrir Caixa'}
              </h1>
              <p className="text-sm text-text-muted">
                {sessaoIsAberta
                  ? 'Sessão de caixa aberta'
                  : sessaoFechada
                    ? 'Abra uma nova sessão para continuar'
                    : 'Informe o fundo de troco para iniciar o turno'}
              </p>
            </div>
          </div>

          {loadingSessao ? (
            <div className="rounded-xl border border-border bg-bg-surface-2 p-5 text-sm text-text-secondary">
              Verificando sessão ativa do caixa...
            </div>
          ) : sessaoFechada ? (
            <div className="flex flex-col gap-4">
              <ResumoFechamento sessao={sessaoFechada} />
              <CaixaAberturaForm onAberto={handleAberto} />
            </div>
          ) : sessaoIsAberta ? (
            <div className="flex flex-col gap-4">
              <SessaoAtiva sessao={sessaoAberta!} />
              <Button size="lg" fullWidth onClick={handleIrAoPDV}>
                <ArrowRight size={18} />
                Continuar Sessão
              </Button>
              <button
                onClick={() => setModalFecharAberto(true)}
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-warning/40 py-2.5 text-sm font-medium text-warning-text hover:bg-warning/10 transition-colors"
              >
                <LockKeyhole size={15} />
                Fechar Caixa
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {!TEM_CAIXA_ID_CONFIGURADO && (
                <div className="rounded-lg border border-warning/30 bg-warning/10 px-3 py-2.5 text-sm text-warning-text">
                  Caixa padrão não configurado. Informe o ID do caixa manualmente para abrir ou retomar uma sessão.
                </div>
              )}
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

      {/* Modal Fechar Caixa */}
      {modalFecharAberto && sessaoAberta && (
        <ModalFecharCaixa
          sessao={sessaoAberta}
          onClose={() => setModalFecharAberto(false)}
          onFechado={handleFechado}
        />
      )}
    </div>
  )
}
