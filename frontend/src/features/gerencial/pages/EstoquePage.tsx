import { useEffect, useRef, useState } from 'react'
import {
  ArrowDownToLine,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  History,
  Search,
  Warehouse,
  X,
} from 'lucide-react'
import {
  entradaEstoque,
  inventarioEstoque,
  listEstoque,
  listMovimentacoes,
} from '@/services/api/gerencial'
import type {
  EstoqueProdutoDTO,
  MovimentacaoDTO,
} from '@/shared/types/api'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function filterDecimal(raw: string): string {
  let s = raw.replace(/[^0-9.,]/g, '')
  const firstComma = s.indexOf(',')
  const firstDot = s.indexOf('.')
  if (firstComma !== -1 && firstDot !== -1) {
    s = s.replace(',', '.')
  } else {
    s = s.replace(',', '.')
  }
  const parts = s.split('.')
  if (parts.length > 2) s = parts[0] + '.' + parts.slice(1).join('')
  return s
}

function parseDecimal(s: string): number {
  return parseFloat(s.replace(',', '.')) || 0
}

function fmtNum(n: number): string {
  return n.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 3 })
}

function fmtMoeda(s: string | number): string {
  return `R$ ${parseFloat(String(s)).toFixed(2).replace('.', ',')}`
}

const TIPO_LABEL: Record<string, string> = {
  entrada_compra: 'Entrada',
  saida_venda: 'Saída (venda)',
  ajuste_positivo: 'Ajuste +',
  ajuste_negativo: 'Ajuste −',
  inventario: 'Inventário',
  entrada_devolucao_cliente: 'Dev. cliente',
  saida_devolucao_fornecedor: 'Dev. fornecedor',
  entrada_transferencia: 'Transf. entrada',
  saida_transferencia: 'Transf. saída',
  perda: 'Perda',
}

const TIPO_COR: Record<string, string> = {
  entrada_compra: 'text-green-400',
  saida_venda: 'text-red-400',
  ajuste_positivo: 'text-green-400',
  ajuste_negativo: 'text-red-400',
  inventario: 'text-yellow-400',
  entrada_devolucao_cliente: 'text-green-400',
  saida_devolucao_fornecedor: 'text-red-400',
  entrada_transferencia: 'text-blue-400',
  saida_transferencia: 'text-blue-400',
  perda: 'text-red-400',
}

// ---------------------------------------------------------------------------
// Modal: Entrada de estoque
// ---------------------------------------------------------------------------

interface ModalEntradaProps {
  produto: EstoqueProdutoDTO
  onClose: () => void
  onSaved: (novaSaldo: number) => void
}

function ModalEntrada({ produto, onClose, onSaved }: ModalEntradaProps) {
  const [qtdStr, setQtdStr] = useState('')
  const [obs, setObs] = useState('')
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  async function handleSalvar() {
    const qtd = parseDecimal(qtdStr)
    if (qtd <= 0) { setErro('Quantidade deve ser maior que zero.'); return }
    setLoading(true)
    setErro('')
    try {
      const resp = await entradaEstoque(produto.produto_id, { quantidade: qtd, observacao: obs || undefined })
      onSaved(resp.saldo_atual)
    } catch (e: any) {
      setErro(e?.response?.data?.detail || 'Erro ao registrar entrada.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-bg-surface border border-border rounded-xl shadow-2xl w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-text-primary font-semibold text-lg flex items-center gap-2">
            <ArrowDownToLine size={18} className="text-green-400" />
            Entrada de estoque
          </h2>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
            <X size={18} />
          </button>
        </div>

        <p className="text-text-secondary text-sm mb-4">
          <span className="text-text-primary font-medium">{produto.descricao}</span>
          {produto.codigo_barras && <span className="ml-2 text-text-muted">{produto.codigo_barras}</span>}
          <br />
          Saldo atual: <span className="text-accent font-semibold">{fmtNum(produto.saldo_atual)} {produto.unidade}</span>
        </p>

        <div className="space-y-3">
          <div>
            <label className="text-text-secondary text-xs mb-1 block">Quantidade a adicionar *</label>
            <input
              ref={inputRef}
              type="text"
              inputMode="decimal"
              value={qtdStr}
              onChange={e => setQtdStr(filterDecimal(e.target.value))}
              onFocus={e => e.target.select()}
              placeholder="Ex: 10"
              className="w-full bg-bg-base border border-border rounded-lg px-3 py-2 text-text-primary text-sm focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>
          <div>
            <label className="text-text-secondary text-xs mb-1 block">Observação (opcional)</label>
            <input
              type="text"
              value={obs}
              onChange={e => setObs(e.target.value)}
              placeholder="Ex: NF 12345"
              maxLength={300}
              className="w-full bg-bg-base border border-border rounded-lg px-3 py-2 text-text-primary text-sm focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>
        </div>

        {erro && <p className="mt-3 text-red-400 text-xs">{erro}</p>}

        <div className="flex gap-3 mt-5">
          <button
            onClick={onClose}
            className="flex-1 py-2 rounded-lg border border-border text-text-secondary text-sm hover:border-accent transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleSalvar}
            disabled={loading}
            className="flex-1 py-2 rounded-lg bg-green-600 hover:bg-green-500 text-white text-sm font-medium transition-colors disabled:opacity-50"
          >
            {loading ? 'Salvando…' : 'Confirmar entrada'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Modal: Ajuste de inventário (saldo contado)
// ---------------------------------------------------------------------------

interface ModalInventarioProps {
  produto: EstoqueProdutoDTO
  onClose: () => void
  onSaved: (novoSaldo: number) => void
}

function ModalInventario({ produto, onClose, onSaved }: ModalInventarioProps) {
  const [saldoStr, setSaldoStr] = useState('')
  const [obs, setObs] = useState('')
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  const saldoContado = parseDecimal(saldoStr)
  const diferenca = saldoStr !== '' ? saldoContado - produto.saldo_atual : null

  async function handleSalvar() {
    if (saldoStr === '') { setErro('Informe o saldo contado.'); return }
    if (saldoContado < 0) { setErro('Saldo não pode ser negativo.'); return }
    setLoading(true)
    setErro('')
    try {
      const resp = await inventarioEstoque(produto.produto_id, {
        saldo_contado: saldoContado,
        observacao: obs || undefined,
      })
      onSaved(resp.saldo_atual)
    } catch (e: any) {
      setErro(e?.response?.data?.detail || 'Erro ao ajustar estoque.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-bg-surface border border-border rounded-xl shadow-2xl w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-text-primary font-semibold text-lg flex items-center gap-2">
            <ClipboardList size={18} className="text-yellow-400" />
            Ajuste de inventário
          </h2>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
            <X size={18} />
          </button>
        </div>

        <p className="text-text-secondary text-sm mb-4">
          <span className="text-text-primary font-medium">{produto.descricao}</span>
          <br />
          Saldo no sistema: <span className="text-accent font-semibold">{fmtNum(produto.saldo_atual)} {produto.unidade}</span>
        </p>

        <div className="space-y-3">
          <div>
            <label className="text-text-secondary text-xs mb-1 block">Saldo contado (novo saldo) *</label>
            <input
              ref={inputRef}
              type="text"
              inputMode="decimal"
              value={saldoStr}
              onChange={e => setSaldoStr(filterDecimal(e.target.value))}
              onFocus={e => e.target.select()}
              placeholder="Ex: 25"
              className="w-full bg-bg-base border border-border rounded-lg px-3 py-2 text-text-primary text-sm focus:outline-none focus:ring-1 focus:ring-accent"
            />
            {diferenca !== null && (
              <p className={`text-xs mt-1 ${diferenca > 0 ? 'text-green-400' : diferenca < 0 ? 'text-red-400' : 'text-text-muted'}`}>
                Diferença: {diferenca > 0 ? '+' : ''}{fmtNum(diferenca)} {produto.unidade}
              </p>
            )}
          </div>
          <div>
            <label className="text-text-secondary text-xs mb-1 block">Observação (opcional)</label>
            <input
              type="text"
              value={obs}
              onChange={e => setObs(e.target.value)}
              placeholder="Ex: Contagem física mai/2026"
              maxLength={300}
              className="w-full bg-bg-base border border-border rounded-lg px-3 py-2 text-text-primary text-sm focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>
        </div>

        {erro && <p className="mt-3 text-red-400 text-xs">{erro}</p>}

        <div className="flex gap-3 mt-5">
          <button
            onClick={onClose}
            className="flex-1 py-2 rounded-lg border border-border text-text-secondary text-sm hover:border-accent transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleSalvar}
            disabled={loading}
            className="flex-1 py-2 rounded-lg bg-yellow-600 hover:bg-yellow-500 text-white text-sm font-medium transition-colors disabled:opacity-50"
          >
            {loading ? 'Salvando…' : 'Confirmar ajuste'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Painel: Histórico de movimentações
// ---------------------------------------------------------------------------

interface HistoricoProps {
  produtoId?: string
  produtoDescricao?: string
  onClose: () => void
}

function PainelHistorico({ produtoId, produtoDescricao, onClose }: HistoricoProps) {
  const [movs, setMovs] = useState<MovimentacaoDTO[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const PER_PAGE = 20

  useEffect(() => { load(1) }, [produtoId])

  async function load(p: number) {
    setLoading(true)
    try {
      const resp = await listMovimentacoes({
        produto_id: produtoId,
        page: p,
        per_page: PER_PAGE,
      })
      setMovs(resp.items)
      setTotal(resp.total)
      setPage(p)
    } finally {
      setLoading(false)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-bg-surface border border-border rounded-xl shadow-2xl w-full max-w-3xl mx-4 flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between p-5 border-b border-border shrink-0">
          <h2 className="text-text-primary font-semibold text-lg flex items-center gap-2">
            <History size={18} className="text-accent" />
            {produtoDescricao ? `Histórico — ${produtoDescricao}` : 'Histórico de movimentações'}
          </h2>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="overflow-auto flex-1">
          {loading ? (
            <div className="p-8 text-center text-text-muted text-sm">Carregando…</div>
          ) : movs.length === 0 ? (
            <div className="p-8 text-center text-text-muted text-sm">Nenhuma movimentação encontrada.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-bg-surface border-b border-border">
                <tr>
                  <th className="text-left px-4 py-2 text-text-muted font-medium">Data/hora</th>
                  {!produtoId && <th className="text-left px-4 py-2 text-text-muted font-medium">Produto</th>}
                  <th className="text-left px-4 py-2 text-text-muted font-medium">Tipo</th>
                  <th className="text-right px-4 py-2 text-text-muted font-medium">Qtd</th>
                  <th className="text-right px-4 py-2 text-text-muted font-medium">Saldo ant.</th>
                  <th className="text-right px-4 py-2 text-text-muted font-medium">Saldo após</th>
                  <th className="text-left px-4 py-2 text-text-muted font-medium">Observação</th>
                </tr>
              </thead>
              <tbody>
                {movs.map(m => (
                  <tr key={m.id} className="border-b border-border hover:bg-bg-base transition-colors">
                    <td className="px-4 py-2 text-text-secondary whitespace-nowrap">
                      {new Date(m.criado_em).toLocaleString('pt-BR', {
                        day: '2-digit', month: '2-digit', year: '2-digit',
                        hour: '2-digit', minute: '2-digit',
                      })}
                    </td>
                    {!produtoId && (
                      <td className="px-4 py-2 text-text-primary max-w-[160px] truncate">{m.produto_descricao}</td>
                    )}
                    <td className={`px-4 py-2 font-medium ${TIPO_COR[m.tipo] ?? 'text-text-secondary'}`}>
                      {TIPO_LABEL[m.tipo] ?? m.tipo}
                    </td>
                    <td className="px-4 py-2 text-right text-text-primary">{fmtNum(m.quantidade)}</td>
                    <td className="px-4 py-2 text-right text-text-muted">{fmtNum(m.saldo_anterior)}</td>
                    <td className="px-4 py-2 text-right text-text-primary font-semibold">{fmtNum(m.saldo_posterior)}</td>
                    <td className="px-4 py-2 text-text-muted text-xs max-w-[160px] truncate">{m.motivo ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-border shrink-0">
            <span className="text-text-muted text-xs">{total} movimentações</span>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => load(page - 1)}
                className="p-1 rounded text-text-muted hover:text-text-primary disabled:opacity-30"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="text-text-secondary text-xs self-center">{page}/{totalPages}</span>
              <button
                disabled={page >= totalPages}
                onClick={() => load(page + 1)}
                className="p-1 rounded text-text-muted hover:text-text-primary disabled:opacity-30"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Página principal
// ---------------------------------------------------------------------------

export function EstoquePage() {
  const [items, setItems] = useState<EstoqueProdutoDTO[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [busca, setBusca] = useState('')
  const [inputBusca, setInputBusca] = useState('')

  const [modalEntrada, setModalEntrada] = useState<EstoqueProdutoDTO | null>(null)
  const [modalInventario, setModalInventario] = useState<EstoqueProdutoDTO | null>(null)
  const [painelHistorico, setPainelHistorico] = useState<{ id?: string; desc?: string } | null>(null)

  const PER_PAGE = 20

  useEffect(() => { load(1, busca) }, [busca])

  async function load(p: number, q: string) {
    setLoading(true)
    try {
      const resp = await listEstoque({ q: q || undefined, page: p, per_page: PER_PAGE })
      setItems(resp.items)
      setTotal(resp.total)
      setPage(p)
    } finally {
      setLoading(false)
    }
  }

  function handleBuscar() {
    setBusca(inputBusca)
  }

  function handleEntradaSaved(produtoId: string, novoSaldo: number) {
    setItems(prev => prev.map(i => i.produto_id === produtoId ? { ...i, saldo_atual: novoSaldo } : i))
    setModalEntrada(null)
  }

  function handleInventarioSaved(produtoId: string, novoSaldo: number) {
    setItems(prev => prev.map(i => i.produto_id === produtoId ? { ...i, saldo_atual: novoSaldo } : i))
    setModalInventario(null)
  }

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Warehouse size={22} className="text-accent" />
          <div>
            <h1 className="text-text-primary text-xl font-semibold">Estoque</h1>
            <p className="text-text-muted text-xs">Saldo do local principal</p>
          </div>
        </div>
        <button
          onClick={() => setPainelHistorico({})}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border text-text-secondary text-sm hover:border-accent hover:text-accent transition-colors"
        >
          <History size={15} />
          Histórico geral
        </button>
      </div>

      {/* Busca */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={inputBusca}
            onChange={e => setInputBusca(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleBuscar()}
            placeholder="Buscar por nome ou EAN..."
            className="w-full bg-bg-surface border border-border rounded-lg pl-9 pr-3 py-2 text-text-primary text-sm focus:outline-none focus:ring-1 focus:ring-accent"
          />
        </div>
        <button
          onClick={handleBuscar}
          className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/80 transition-colors"
        >
          Buscar
        </button>
      </div>

      {/* Tabela */}
      <div className="bg-bg-surface border border-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-border">
            <tr>
              <th className="text-left px-4 py-3 text-text-muted font-medium">Produto</th>
              <th className="text-left px-4 py-3 text-text-muted font-medium hidden sm:table-cell">EAN</th>
              <th className="text-center px-4 py-3 text-text-muted font-medium">Un.</th>
              <th className="text-right px-4 py-3 text-text-muted font-medium">Saldo</th>
              <th className="text-right px-4 py-3 text-text-muted font-medium hidden md:table-cell">Preço venda</th>
              <th className="text-center px-4 py-3 text-text-muted font-medium hidden sm:table-cell">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-text-muted">Carregando…</td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-text-muted">Nenhum produto encontrado.</td>
              </tr>
            ) : (
              items.map(item => (
                <tr key={item.produto_id} className="border-b border-border hover:bg-bg-base transition-colors">
                  <td className="px-4 py-3 text-text-primary font-medium">{item.descricao}</td>
                  <td className="px-4 py-3 text-text-muted hidden sm:table-cell">
                    {item.codigo_barras ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-center text-text-secondary">{item.unidade ?? '—'}</td>
                  <td className={`px-4 py-3 text-right font-semibold ${item.saldo_atual <= 0 ? 'text-red-400' : 'text-green-400'}`}>
                    {fmtNum(item.saldo_atual)}
                  </td>
                  <td className="px-4 py-3 text-right text-text-secondary hidden md:table-cell">
                    {fmtMoeda(item.preco_venda)}
                  </td>
                  <td className="px-4 py-3 text-center hidden sm:table-cell">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${item.ativo ? 'bg-green-900/40 text-green-400' : 'bg-zinc-700 text-text-muted'}`}>
                      {item.ativo ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 justify-end">
                      <button
                        onClick={() => setModalEntrada(item)}
                        title="Entrada de estoque"
                        className="p-1.5 rounded-lg hover:bg-green-900/30 text-green-400 transition-colors"
                      >
                        <ArrowDownToLine size={15} />
                      </button>
                      <button
                        onClick={() => setModalInventario(item)}
                        title="Ajuste de inventário"
                        className="p-1.5 rounded-lg hover:bg-yellow-900/30 text-yellow-400 transition-colors"
                      >
                        <ClipboardList size={15} />
                      </button>
                      <button
                        onClick={() => setPainelHistorico({ id: item.produto_id, desc: item.descricao })}
                        title="Ver histórico"
                        className="p-1.5 rounded-lg hover:bg-bg-base text-text-muted hover:text-accent transition-colors"
                      >
                        <History size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Paginação */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-text-muted text-xs">{total} produtos</span>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => load(page - 1, busca)}
              className="p-1.5 rounded-lg border border-border text-text-muted hover:text-text-primary disabled:opacity-30 transition-colors"
            >
              <ChevronLeft size={15} />
            </button>
            <span className="text-text-secondary text-sm">{page} / {totalPages}</span>
            <button
              disabled={page >= totalPages}
              onClick={() => load(page + 1, busca)}
              className="p-1.5 rounded-lg border border-border text-text-muted hover:text-text-primary disabled:opacity-30 transition-colors"
            >
              <ChevronRight size={15} />
            </button>
          </div>
        </div>
      )}

      {/* Modais */}
      {modalEntrada && (
        <ModalEntrada
          produto={modalEntrada}
          onClose={() => setModalEntrada(null)}
          onSaved={novoSaldo => handleEntradaSaved(modalEntrada.produto_id, novoSaldo)}
        />
      )}
      {modalInventario && (
        <ModalInventario
          produto={modalInventario}
          onClose={() => setModalInventario(null)}
          onSaved={novoSaldo => handleInventarioSaved(modalInventario.produto_id, novoSaldo)}
        />
      )}
      {painelHistorico !== null && (
        <PainelHistorico
          produtoId={painelHistorico.id}
          produtoDescricao={painelHistorico.desc}
          onClose={() => setPainelHistorico(null)}
        />
      )}
    </div>
  )
}
