import { useState } from 'react'
import { DollarSign, QrCode, CreditCard, Banknote, MoreHorizontal, Check, Loader2, FileText, Receipt } from 'lucide-react'
import { formatCurrency } from '@/shared/utils/format'
import type { FormaPagamento, TipoEmissao, VendaDTO } from '@/shared/types/api'
import clsx from 'clsx'

interface PagamentoPanelProps {
  venda: VendaDTO
  totalPago: number
  onPagar: (forma: FormaPagamento, valor: number) => Promise<void>
  modoEmissaoSelecionado: TipoEmissao
  onSelecionarModoEmissao: (modo: TipoEmissao) => void
  onFinalizarFiscal: () => Promise<void>
  onFinalizarGerencial: () => Promise<void>
  onScannerFocusChange: (enabled: boolean) => void
  loadingFinalizar?: boolean
}

interface FormaInfo {
  key: FormaPagamento
  label: string
  icon: React.ReactNode
  color: string
  activeColor: string
}

const FORMAS: FormaInfo[] = [
  {
    key: '01',
    label: 'Dinheiro',
    icon: <Banknote size={16} />,
    color: 'border-[#1C4D2E]/80 bg-[#0F2E1A] hover:bg-[#162F1F] text-[#4CD137]',
    activeColor: 'border-pdv-fiscal/60 bg-pdv-fiscal/15 text-pdv-fiscal ring-1 ring-pdv-fiscal/25',
  },
  {
    key: '17',
    label: 'Pix',
    icon: <QrCode size={16} />,
    color: 'border-[#1A3D6B]/80 bg-[#0D2240] hover:bg-[#112645] text-[#4A8FE0]',
    activeColor: 'border-[#2C7BE5]/60 bg-[#2C7BE5]/15 text-[#5B9AF0] ring-1 ring-[#2C7BE5]/25',
  },
  {
    key: '04',
    label: 'Débito',
    icon: <CreditCard size={16} />,
    color: 'border-[#1A3050]/80 bg-[#0D1E35] hover:bg-[#111F38] text-[#6B9AC4]',
    activeColor: 'border-[#274C77]/70 bg-[#274C77]/20 text-[#90B8D8] ring-1 ring-[#274C77]/40',
  },
  {
    key: '03',
    label: 'Crédito',
    icon: <CreditCard size={16} />,
    color: 'border-[#4D3D0E]/80 bg-[#2A2006] hover:bg-[#2F2508] text-[#D4A62A]',
    activeColor: 'border-pdv-gerencial/60 bg-pdv-gerencial/15 text-pdv-gerencial ring-1 ring-pdv-gerencial/25',
  },
  {
    key: '99',
    label: 'Outros',
    icon: <MoreHorizontal size={16} />,
    color: 'border-pdv-border bg-pdv-surface-2/50 hover:bg-pdv-surface-2 text-pdv-muted',
    activeColor: 'border-pdv-muted/50 bg-pdv-surface-2 text-pdv-text ring-1 ring-pdv-muted/25',
  },
]

export function PagamentoPanel({
  venda,
  totalPago,
  onPagar,
  modoEmissaoSelecionado,
  onSelecionarModoEmissao,
  onFinalizarFiscal,
  onFinalizarGerencial,
  onScannerFocusChange,
  loadingFinalizar,
}: PagamentoPanelProps) {
  const [formaSelecionada, setFormaSelecionada] = useState<FormaPagamento | null>(null)
  const [valorInput, setValorInput] = useState('')
  const [loadingPagamento, setLoadingPagamento] = useState(false)
  const [erro, setErro] = useState('')

  const totalLiquido = parseFloat(venda.total_liquido)
  const restante = Math.max(0, totalLiquido - totalPago)
  const podeFinalizar = totalPago >= totalLiquido && venda.itens.filter((i) => !i.cancelado).length > 0
  const isFiscal = modoEmissaoSelecionado === 'FISCAL'

  function handleSelecionarForma(forma: FormaPagamento) {
    setFormaSelecionada(forma)
    onScannerFocusChange(false)
    setValorInput(restante > 0 ? restante.toFixed(2).replace('.', ',') : '')
    setErro('')
  }

  async function handleConfirmarPagamento() {
    if (!formaSelecionada) return
    const valor = parseFloat(valorInput.replace(',', '.'))
    if (!valor || valor <= 0) {
      setErro('Informe um valor válido.')
      return
    }
    setLoadingPagamento(true)
    setErro('')
    try {
      await onPagar(formaSelecionada, valor)
      setFormaSelecionada(null)
      setValorInput('')
      onScannerFocusChange(true)
    } catch {
      setErro('Erro ao registrar pagamento.')
    } finally {
      setLoadingPagamento(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">

      {/* ══ BANNER DE MODO ══ */}
      <div
        className={clsx(
          'flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 font-bold uppercase tracking-widest text-sm',
          isFiscal
            ? 'bg-pdv-fiscal text-white shadow-lg shadow-pdv-fiscal/25'
            : 'bg-pdv-gerencial text-white shadow-lg shadow-pdv-gerencial/25',
        )}
      >
        {isFiscal ? <Receipt size={15} /> : <FileText size={15} />}
        {isFiscal ? 'Modo Fiscal — NFC-e' : 'Modo Gerencial'}
      </div>

      {/* ══ TIPO DE FINALIZAÇÃO ══ */}
      <div className="rounded-xl border border-pdv-border bg-pdv-surface/60 p-3">
        <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-600">
          Tipo de Finalização
        </p>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => onSelecionarModoEmissao('FISCAL')}
            className={clsx(
              'rounded-lg border px-3 py-2.5 text-left transition-all',
              isFiscal
                ? 'border-pdv-fiscal/60 bg-pdv-fiscal/15 text-pdv-fiscal shadow-sm shadow-pdv-fiscal/10'
                : 'border-pdv-border bg-pdv-bg/50 hover:bg-pdv-surface text-pdv-muted hover:text-pdv-text',
            )}
          >
            <div className="flex items-center gap-2 text-sm font-bold">
              <Receipt size={14} />
              Fiscal
            </div>
            <p className="mt-0.5 text-xs opacity-70">Gera NFC-e</p>
          </button>
          <button
            type="button"
            onClick={() => onSelecionarModoEmissao('GERENCIAL')}
            className={clsx(
              'rounded-lg border px-3 py-2.5 text-left transition-all',
              !isFiscal
                ? 'border-pdv-gerencial/60 bg-pdv-gerencial/15 text-pdv-gerencial shadow-sm shadow-pdv-gerencial/10'
                : 'border-pdv-border bg-pdv-bg/50 hover:bg-pdv-surface text-pdv-muted hover:text-pdv-text',
            )}
          >
            <div className="flex items-center gap-2 text-sm font-bold">
              <FileText size={14} />
              Gerencial
            </div>
            <p className="mt-0.5 text-xs opacity-70">Sem valor fiscal</p>
          </button>
        </div>
      </div>

      {/* ══ FORMA DE PAGAMENTO ══ */}
      <div>
        <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-600">
          Forma de Pagamento
        </p>
        <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
          {FORMAS.map((f) => (
            <button
              key={f.key}
              onClick={() => handleSelecionarForma(f.key)}
              className={clsx(
                'flex items-center gap-2 rounded-lg border px-2.5 py-2 text-sm font-medium transition-all',
                'focus:outline-none',
                formaSelecionada === f.key ? f.activeColor : f.color,
              )}
            >
              {f.icon}
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* ══ INPUT DE VALOR ══ */}
      {formaSelecionada && (
        <div className="flex flex-col gap-2 rounded-lg border border-pdv-border-2 bg-pdv-surface p-3 animate-slide-in">
          <div className="flex items-center gap-2">
            <DollarSign size={13} className="text-slate-500" />
            <span className="text-sm font-medium text-slate-300">
              Valor · {FORMAS.find((f) => f.key === formaSelecionada)?.label}
            </span>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={valorInput}
              onChange={(e) => setValorInput(e.target.value)}
              onFocus={() => onScannerFocusChange(false)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleConfirmarPagamento()
                if (e.key === 'Escape') {
                  setFormaSelecionada(null)
                  onScannerFocusChange(true)
                }
              }}
              placeholder="0,00"
              autoFocus
              className="flex-1 rounded-lg border border-pdv-border-2 bg-pdv-bg px-3 py-2.5 font-mono text-xl font-bold text-slate-100 placeholder-slate-700 outline-none focus:border-pdv-fiscal/60 focus:ring-1 focus:ring-pdv-fiscal/30"
              inputMode="decimal"
            />
            <button
              onClick={handleConfirmarPagamento}
              disabled={loadingPagamento}
              className="flex items-center gap-1.5 rounded-lg bg-pdv-fiscal hover:bg-pdv-fiscal-dk px-4 py-2 font-semibold text-white transition-colors disabled:opacity-50"
            >
              {loadingPagamento ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
              OK
            </button>
          </div>
          {erro && <p className="text-xs text-red-400">{erro}</p>}
          <p className="text-xs text-slate-600">Enter confirma · Esc cancela · Sug.: {formatCurrency(restante)}</p>
        </div>
      )}

      {/* ══ PAGAMENTOS REGISTRADOS ══ */}
      {venda.pagamentos.length > 0 && (
        <div>
          <p className="mb-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-600">
            Pagamentos
          </p>
          <ul className="flex flex-col gap-1">
            {venda.pagamentos.map((p) => (
              <li
                key={p.id}
                className="flex items-center justify-between rounded-lg border border-pdv-border bg-pdv-surface px-3 py-2 text-sm"
              >
                <span className="text-slate-500">{labelForma(p.forma_pagamento)}</span>
                <span className="font-mono font-semibold text-pdv-fiscal">
                  + {formatCurrency(p.valor)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ══ BOTÕES DE FINALIZAÇÃO — MODO-RESPONSIVOS ══ */}
      <div className="flex flex-col gap-2 pt-1">
        {isFiscal ? (
          <>
            {/* FISCAL modo → "Venda Fiscal" é o botão primário grande */}
            <button
              onClick={onFinalizarFiscal}
              disabled={!podeFinalizar || loadingFinalizar}
              className={clsx(
                'flex w-full items-center justify-center gap-3 rounded-xl px-4 py-4 font-bold text-base transition-all duration-200',
                podeFinalizar
                  ? 'bg-pdv-fiscal hover:bg-pdv-fiscal-dk text-white shadow-lg shadow-pdv-fiscal/30 hover:shadow-pdv-fiscal-dk/40'
                  : 'bg-pdv-surface border border-pdv-border text-slate-600 cursor-not-allowed',
              )}
            >
              {loadingFinalizar ? (
                <Loader2 size={20} className="animate-spin" />
              ) : (
                <Receipt size={20} />
              )}
              <span>Venda Fiscal</span>
              <kbd className="ml-auto rounded bg-white/15 px-2 py-0.5 font-mono text-sm">F4</kbd>
            </button>
            {/* Pedido/Gerencial — botão secundário menor */}
            <button
              onClick={onFinalizarGerencial}
              disabled={!podeFinalizar || loadingFinalizar}
              className={clsx(
                'flex w-full items-center justify-center gap-2 rounded-lg border px-3 py-2.5 text-sm font-medium transition-all',
                podeFinalizar
                  ? 'border-pdv-border-2 bg-pdv-surface hover:bg-pdv-surface-2 text-slate-400 hover:text-slate-300'
                  : 'border-pdv-border/50 bg-transparent text-slate-700 cursor-not-allowed',
              )}
            >
              <FileText size={15} />
              Pedido / Gerencial
              <kbd className="ml-auto rounded border border-pdv-border bg-pdv-bg px-1.5 py-0.5 font-mono text-xs text-slate-600">F2</kbd>
            </button>
          </>
        ) : (
          <>
            {/* GERENCIAL modo → "Pedido / Gerencial" é o botão primário grande */}
            <button
              onClick={onFinalizarGerencial}
              disabled={!podeFinalizar || loadingFinalizar}
              className={clsx(
                'flex w-full items-center justify-center gap-3 rounded-xl px-4 py-4 font-bold text-base transition-all duration-200',
                podeFinalizar
                  ? 'bg-amber-500 hover:bg-amber-400 text-white shadow-lg shadow-amber-500/30 hover:shadow-amber-400/40'
                  : 'bg-pdv-surface border border-pdv-border text-slate-600 cursor-not-allowed',
              )}
            >
              {loadingFinalizar ? (
                <Loader2 size={20} className="animate-spin" />
              ) : (
                <FileText size={20} />
              )}
              <span>Pedido / Gerencial</span>
              <kbd className="ml-auto rounded bg-white/15 px-2 py-0.5 font-mono text-sm">F2</kbd>
            </button>
            {/* Venda Fiscal — botão secundário menor */}
            <button
              onClick={onFinalizarFiscal}
              disabled={!podeFinalizar || loadingFinalizar}
              className={clsx(
                'flex w-full items-center justify-center gap-2 rounded-lg border px-3 py-2.5 text-sm font-medium transition-all',
                podeFinalizar
                  ? 'border-pdv-border-2 bg-pdv-surface hover:bg-pdv-surface-2 text-slate-400 hover:text-slate-300'
                  : 'border-pdv-border/50 bg-transparent text-slate-700 cursor-not-allowed',
              )}
            >
              <Receipt size={15} />
              Venda Fiscal
              <kbd className="ml-auto rounded border border-pdv-border bg-pdv-bg px-1.5 py-0.5 font-mono text-xs text-slate-600">F4</kbd>
            </button>
          </>
        )}
      </div>

      {!podeFinalizar && venda.itens.filter((i) => !i.cancelado).length > 0 && (
        <p className="text-center text-xs text-red-500">
          Falta {formatCurrency(restante)} para finalizar
        </p>
      )}
    </div>
  )
}

function labelForma(forma: string): string {
  const map: Record<string, string> = {
    '01': 'Dinheiro',
    '03': 'Cartão Crédito',
    '04': 'Cartão Débito',
    '17': 'Pix',
    '99': 'Outros',
  }
  return map[forma] ?? forma
}

