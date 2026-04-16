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

  return (
    <div className="flex flex-col gap-0.5 rounded-xl border border-border bg-bg-surface-2 p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-text-muted">Modo da venda</p>
          <p className="text-xs text-text-muted">
            {modoEmissaoSelecionado === 'FISCAL'
              ? 'Vai emitir NFC-e ao concluir.'
              : 'Pedido gerencial sem valor fiscal.'}
          </p>
        </div>
        <span
          className={clsx(
            'rounded-full border px-2.5 py-1 text-[11px] font-bold tracking-wide',
            modoEmissaoSelecionado === 'FISCAL'
              ? 'border-info/40 bg-info/10 text-info-text'
              : 'border-warning/40 bg-warning/10 text-warning-text',
          )}
        >
          {modoEmissaoSelecionado === 'FISCAL' ? 'FISCAL' : 'GERENCIAL'}
        </span>
      </div>

      <ResumoRow label="Subtotal" value={formatCurrency(venda.total_bruto)} />

      {totalDesconto > 0 && (
        <ResumoRow
          label="Desconto"
          value={`− ${formatCurrency(venda.total_desconto)}`}
          className="text-warning-text"
        />
      )}

      <div className="my-2 border-t border-border" />

      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-text-secondary">Total</span>
        <span className="text-xl font-bold text-text-primary">
          {formatCurrency(venda.total_liquido)}
        </span>
      </div>

      <div className="mt-2 flex items-center justify-between rounded-lg border border-border/60 bg-bg-surface px-3 py-2">
        <span className="text-xs font-medium uppercase tracking-wider text-text-muted">Valor restante</span>
        <span className={clsx('font-mono text-base font-semibold', restante > 0 ? 'text-warning-text' : 'text-success-text')}>
          {formatCurrency(restante)}
        </span>
      </div>

      {pago && (
        <>
          <div className="my-2 border-t border-border" />
          <ResumoRow
            label="Total pago"
            value={formatCurrency(totalPago)}
            className="text-success-text"
          />
          {restante > 0 ? (
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-danger-text">Falta</span>
              <span className={clsx('text-lg font-bold text-danger-text')}>
                {formatCurrency(restante)}
              </span>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-success-text">Troco</span>
              <span className="text-lg font-bold text-success-text">
                {formatCurrency(troco)}
              </span>
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
      <span className="text-sm text-text-secondary">{label}</span>
      <span className={clsx('font-mono text-sm font-medium text-text-primary', className)}>
        {value}
      </span>
    </div>
  )
}
