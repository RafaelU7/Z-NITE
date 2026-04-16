import { Trash2, AlertTriangle } from 'lucide-react'
import { Modal } from '@/shared/ui/Modal'
import { Button } from '@/shared/ui/Button'
import type { ItemVendaDTO } from '@/shared/types/api'
import { formatCurrency, formatQuantity } from '@/shared/utils/format'

interface ModalRemocaoItemProps {
  open: boolean
  item: ItemVendaDTO | null
  onConfirm: () => void
  onCancel: () => void
  loading?: boolean
}

export function ModalRemocaoItem({
  open,
  item,
  onConfirm,
  onCancel,
  loading,
}: ModalRemocaoItemProps) {
  return (
    <Modal
      open={open}
      onClose={onCancel}
      title="Remover Item"
      size="sm"
    >
      <div className="flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-danger/10">
            <AlertTriangle size={18} className="text-danger-text" />
          </div>
          <div>
            <p className="text-sm text-text-primary">
              Deseja remover este item da venda?
            </p>
            {item && (
              <p className="mt-1 text-sm font-medium text-text-secondary">
                {item.descricao_produto} ·{' '}
                <span className="font-mono">{formatQuantity(item.quantidade)}</span> ×{' '}
                <span className="font-mono">{formatCurrency(item.preco_unitario)}</span>
              </p>
            )}
            <p className="mt-1.5 text-xs text-text-muted">
              O estoque será devolvido automaticamente.
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          <Button variant="ghost" fullWidth onClick={onCancel} disabled={loading} kbd="Esc">
            Cancelar
          </Button>
          <Button variant="danger" fullWidth onClick={onConfirm} loading={loading}>
            <Trash2 size={15} />
            Remover
          </Button>
        </div>
      </div>
    </Modal>
  )
}
