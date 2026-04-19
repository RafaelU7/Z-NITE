import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { listSessoes } from '@/services/api/gerencial'
import type { SessaoListDTO } from '@/shared/types/api'
import { formatCurrency, formatDateTime } from '@/shared/utils/format'

const STATUS_LABEL: Record<string, string> = {
  aberta: 'Aberta',
  fechada: 'Fechada',
}

export function SessoesPage() {
  const [sessoes, setSessoes] = useState<SessaoListDTO[]>([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')

  useEffect(() => {
    listSessoes(30)
      .then(setSessoes)
      .catch(() => setErro('Erro ao carregar sessões.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold text-text-primary">Sessões de Caixa</h1>

      {loading && (
        <div className="flex items-center gap-2 text-text-muted text-sm">
          <Loader2 size={16} className="animate-spin" /> Carregando...
        </div>
      )}
      {erro && <p className="text-sm text-danger-text">{erro}</p>}

      <div className="overflow-auto rounded-xl border border-border bg-bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-muted">
              <th className="px-3 py-2.5">Caixa</th>
              <th className="px-3 py-2.5">Operador</th>
              <th className="px-3 py-2.5">Abertura</th>
              <th className="px-3 py-2.5">Fechamento</th>
              <th className="px-3 py-2.5 text-right">Total</th>
              <th className="px-3 py-2.5 text-center">Vendas</th>
              <th className="px-3 py-2.5">Status</th>
            </tr>
          </thead>
          <tbody>
            {sessoes.map((s) => (
              <tr key={s.id} className="border-b border-border last:border-0 hover:bg-bg-surface-2">
                <td className="px-3 py-2.5 font-medium text-text-primary">
                  {s.caixa_descricao ?? `Caixa ${s.caixa_numero}`}
                </td>
                <td className="px-3 py-2.5 text-text-secondary">{s.operador_nome}</td>
                <td className="px-3 py-2.5 text-xs text-text-muted">
                  {formatDateTime(s.data_abertura)}
                </td>
                <td className="px-3 py-2.5 text-xs text-text-muted">
                  {s.data_fechamento ? formatDateTime(s.data_fechamento) : '—'}
                </td>
                <td className="px-3 py-2.5 text-right font-mono">
                  {formatCurrency(Number(s.total_liquido))}
                </td>
                <td className="px-3 py-2.5 text-center text-text-secondary">
                  {s.quantidade_vendas}
                </td>
                <td className="px-3 py-2.5">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      s.status === 'aberta'
                        ? 'bg-success/15 text-success-text'
                        : 'bg-bg-surface-2 text-text-muted'
                    }`}
                  >
                    {STATUS_LABEL[s.status] ?? s.status}
                  </span>
                </td>
              </tr>
            ))}
            {!loading && sessoes.length === 0 && (
              <tr>
                <td colSpan={7} className="py-8 text-center text-sm text-text-muted">
                  Nenhuma sessão encontrada.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
