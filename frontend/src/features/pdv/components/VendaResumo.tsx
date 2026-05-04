import { formatCurrency } from '@/shared/utils/format'
import type { TipoEmissao, VendaDTO } from '@/shared/types/api'
import clsx from 'clsx'

interface VendaResumoProps {
  venda: VendaDTO
  totalPago: number
  modoEmissaoSelecionado: TipoEmissao
}

export function VendaResumo({ venda, totalPago, modoEmissaoSelecionado }: VendaResumoProps) {
  const totalLiquido = parseFloat(venda.total_liquido)
  const totalDesconto = parseFloat(venda.total_desconto)
  const restante = Math.max(0, totalLiquido - totalPago)
  const troco = Math.max(0, totalPago - totalLiquido)
  const pago = totalPago > 0

  const isFiscal = modoEmissaoSelecionado === 'FISCAL'

  return (
    <div
      className={clsx(
        'flex flex-col gap-0.5 rounded-xl border p-4 transition-colors duration-300',
        isFiscal
          ? 'border-pdv-fiscal/40 bg-pdv-surface shadow-md shadow-black/25'
          : 'border-pdv-gerencial/40 bg-pdv-surface shadow-md shadow-black/25',
      )}
    >
      {/* ── Header do modo ── */}
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-400">Modo da Venda</p>
          <p className="text-xs text-slate-600">
            {isFiscal ? 'Vai emitir NFC-e ao concluir.' : 'Pedido gerencial sem valor fiscal.'}
          </p>
        </div>
        <span
          className={clsx(
            'rounded-full border px-2.5 py-1 text-[11px] font-bold tracking-wide shrink-0',
            isFiscal
              ? 'border-pdv-fiscal/50 bg-pdv-fiscal/15 text-pdv-fiscal'
              : 'border-pdv-gerencial/50 bg-pdv-gerencial/15 text-pdv-gerencial',
          )}
        >
          {isFiscal ? 'FISCAL' : 'GERENCIAL'}
        </span>
      </div>

      <ResumoRow label="Subtotal" value={formatCurrency(venda.total_bruto)} />

      {totalDesconto > 0 && (
        <ResumoRow
          label="Desconto"
          value={`− ${formatCurrency(venda.total_desconto)}`}
          className="text-amber-400"
        />
      )}

      <div className="my-2 border-t border-pdv-border/60" />

      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-300">Total</span>
        <span className="text-xl font-bold text-slate-100">
          {formatCurrency(venda.total_liquido)}
        </span>
      </div>

      {/* Valor restante — destaque forte */}
      <div
        className={clsx(
          'mt-2 flex items-center justify-between rounded-lg border px-3 py-2.5',
          restante > 0
            ? 'border-amber-700/40 bg-amber-500/10'
            : 'border-pdv-fiscal/30 bg-pdv-fiscal/10',
        )}
      >
        <span className="text-xs font-bold uppercase tracking-widest text-slate-400">Valor restante</span>
        <span
          className={clsx(
            'font-mono text-xl font-black',
            restante > 0 ? 'text-amber-400' : 'text-pdv-fiscal',
          )}
        >
          {formatCurrency(restante)}
        </span>
      </div>

      {pago && (
        <>
          <div className="my-2 border-t border-pdv-border/60" />
          <ResumoRow
            label="Total pago"
            value={formatCurrency(totalPago)}
            className="text-pdv-fiscal"
          />
          {restante > 0 ? (
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-red-400">Falta</span>
              <span className="text-lg font-bold text-red-400">{formatCurrency(restante)}</span>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-pdv-fiscal">Troco</span>
              <span className="text-lg font-bold text-pdv-fiscal">{formatCurrency(troco)}</span>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function ResumoRow({
  label,
  value,
  className,
}: {
  label: string
  value: string
  className?: string
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-slate-500">{label}</span>
      <span className={clsx('font-mono text-sm font-medium text-slate-300', className)}>
        {value}
      </span>
    </div>
  )
}
