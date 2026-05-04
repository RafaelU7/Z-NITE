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
      <div className="flex flex-1 flex-col items-center justify-center gap-3 py-16 text-slate-600">
        <svg
          width="56"
          height="56"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1"
          className="opacity-25"
        >
          <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
          <line x1="3" y1="6" x2="21" y2="6" />
          <path d="M16 10a4 4 0 01-8 0" />
        </svg>
        <p className="text-sm font-medium text-slate-500">Nenhum item adicionado</p>
        <p className="text-xs text-slate-600">Leia o código de barras para adicionar</p>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col overflow-auto">
      {/* Cabeçalho */}
      <div className="grid grid-cols-[2rem_1fr_5rem_5rem_6rem_2.5rem] gap-2 border-b border-pdv-border px-3 py-2 text-xs font-medium uppercase tracking-wide text-slate-600">
        <span>#</span>
        <span>Produto</span>
        <span className="text-right">Qtd</span>
        <span className="text-right">Unit.</span>
        <span className="text-right">Total</span>
        <span />
      </div>

      {/* Itens */}
      <ul className="divide-y divide-pdv-border/40">
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
                  ? 'bg-pdv-fiscal/10 border-l-2 border-l-pdv-fiscal'
                  : 'hover:bg-pdv-surface/60',
              )}
            >
              <span className="text-xs font-mono text-slate-600">{index + 1}</span>

              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-200">
                  {item.descricao_produto}
                </p>
                {item.codigo_barras && (
                  <p className="font-mono text-xs text-slate-600">{item.codigo_barras}</p>
                )}
              </div>

              <span className="text-right font-mono text-sm text-slate-300">
                {formatQuantity(item.quantidade)}
                {item.unidade && (
                  <span className="ml-1 text-xs text-slate-600">{item.unidade}</span>
                )}
              </span>

              <span className="text-right font-mono text-sm text-slate-500">
                {formatCurrency(item.preco_unitario)}
              </span>

              <span className="text-right font-mono text-sm font-semibold text-slate-100">
                {formatCurrency(item.total_item)}
              </span>

              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onRemoveItem(item.id)
                }}
                className="flex items-center justify-center rounded p-1 text-slate-600 hover:bg-red-500/20 hover:text-red-400 transition-colors"
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
