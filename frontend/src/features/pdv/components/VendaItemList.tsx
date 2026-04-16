import clsx from 'clsx'
import { Trash2 } from 'lucide-react'
import { formatCurrency, formatQuantity } from '@/shared/utils/format'
import type { ItemVendaDTO } from '@/shared/types/api'

interface VendaItemListProps {
  itens: ItemVendaDTO[]
  itemSelecionadoId: string | null
  onSelectItem: (id: string) => void
  onRemoveItem: (id: string) => void
}

export function VendaItemList({
  itens,
  itemSelecionadoId,
  onSelectItem,
  onRemoveItem,
}: VendaItemListProps) {
  const ativos = itens.filter((i) => !i.cancelado)

  if (ativos.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 py-16 text-text-muted">
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="opacity-30"
        >
          <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
          <line x1="3" y1="6" x2="21" y2="6" />
          <path d="M16 10a4 4 0 01-8 0" />
        </svg>
        <p className="text-sm">Nenhum item adicionado</p>
        <p className="text-xs opacity-60">Leia o código de barras para adicionar</p>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col overflow-auto">
      {/* Cabeçalho */}
      <div className="grid grid-cols-[2rem_1fr_5rem_5rem_6rem_2.5rem] gap-2 border-b border-border px-3 py-2 text-xs font-medium uppercase tracking-wide text-text-muted">
        <span>#</span>
        <span>Produto</span>
        <span className="text-right">Qtd</span>
        <span className="text-right">Unit.</span>
        <span className="text-right">Total</span>
        <span />
      </div>

      {/* Itens */}
      <ul className="divide-y divide-border/50">
        {ativos.map((item, index) => {
          const isSelected = itemSelecionadoId === item.id
          return (
            <li
              key={item.id}
              onClick={() => onSelectItem(isSelected ? '' : item.id)}
              className={clsx(
                'grid grid-cols-[2rem_1fr_5rem_5rem_6rem_2.5rem] cursor-pointer items-center gap-2 px-3 py-3',
                'transition-colors duration-100',
                isSelected
                  ? 'bg-accent/10 border-l-2 border-l-accent'
                  : 'hover:bg-bg-surface-2',
              )}
            >
              <span className="text-xs font-mono text-text-muted">{index + 1}</span>

              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-text-primary">
                  {item.descricao_produto}
                </p>
                {item.codigo_barras && (
                  <p className="font-mono text-xs text-text-muted">{item.codigo_barras}</p>
                )}
              </div>

              <span className="text-right font-mono text-sm text-text-primary">
                {formatQuantity(item.quantidade)}
                {item.unidade && (
                  <span className="ml-1 text-xs text-text-muted">{item.unidade}</span>
                )}
              </span>

              <span className="text-right font-mono text-sm text-text-secondary">
                {formatCurrency(item.preco_unitario)}
              </span>

              <span className="text-right font-mono text-sm font-semibold text-text-primary">
                {formatCurrency(item.total_item)}
              </span>

              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onRemoveItem(item.id)
                }}
                className="flex items-center justify-center rounded p-1 text-text-muted hover:bg-danger/20 hover:text-danger-text transition-colors"
                title="Remover item (F8)"
              >
                <Trash2 size={14} />
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
