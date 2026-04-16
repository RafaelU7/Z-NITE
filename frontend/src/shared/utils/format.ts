/**
 * Utilitários de formatação para o PDV
 */

const BRL = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

export function formatCurrency(value: string | number): string {
  const n = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(n)) return 'R$ 0,00'
  return BRL.format(n)
}

export function formatQuantity(value: string | number): string {
  const n = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(n)) return '0'
  // Remove zeros desnecessários: 1.000 → 1, 1.500 → 1,500
  return n.toLocaleString('pt-BR', { maximumFractionDigits: 3 })
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatTime(iso?: string): string {
  const d = iso ? new Date(iso) : new Date()
  return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

export function totalPago(pagamentos: Array<{ valor: string; cancelado?: boolean }>): number {
  return pagamentos.reduce((acc, p) => acc + parseFloat(p.valor || '0'), 0)
}
