import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, Loader2, Pencil } from 'lucide-react'
import {
  listProdutos,
  patchProduto,
  listPerfisTributarios,
} from '@/services/api/gerencial'
import type {
  ProdutoGerencialDTO,
  PerfilTributarioSimpleDTO,
  ProdutoPatchRequest,
} from '@/shared/types/api'
import { formatCurrency } from '@/shared/utils/format'
import { Modal } from '@/shared/ui/Modal'
import { Input } from '@/shared/ui/Input'
import { Button } from '@/shared/ui/Button'

function filterDecimal(raw: string): string {
  let v = raw.replace(',', '.')
  v = v.replace(/[^0-9.]/g, '')
  const pts = v.split('.')
  if (pts.length > 2) v = pts[0] + '.' + pts.slice(1).join('')
  return v
}

export function ProdutosPage() {
  const navigate = useNavigate()
  const [produtos, setProdutos] = useState<ProdutoGerencialDTO[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const PER_PAGE = 20
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState('')

  const [perfis, setPerfis] = useState<PerfilTributarioSimpleDTO[]>([])

  const [editTarget, setEditTarget] = useState<ProdutoGerencialDTO | null>(null)
  const [editPrecoStr, setEditPrecoStr] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveErr, setSaveErr] = useState('')

  async function load(newPage = page, newQ = q) {
    setLoading(true)
    setErro('')
    try {
      const res = await listProdutos({ q: newQ || undefined, page: newPage, per_page: PER_PAGE })
      setProdutos(res.items)
      setTotal(res.total)
    } catch {
      setErro('Erro ao carregar produtos.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])
  useEffect(() => {
    listPerfisTributarios().then(setPerfis).catch(() => {})
  }, [])

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
    load(1, q)
  }

  function openEdit(p: ProdutoGerencialDTO) {
    setEditTarget(p)
    setEditPrecoStr(String(p.preco_venda))
    setSaveErr('')
  }

  async function handlePatch(e: React.FormEvent) {
    e.preventDefault()
    if (!editTarget) return
    setSaving(true)
    setSaveErr('')
    try {
      const req: ProdutoPatchRequest = {
        descricao: editTarget.descricao,
        descricao_pdv: editTarget.descricao_pdv ?? undefined,
        preco_venda: parseFloat(editPrecoStr.replace(',', '.')) || 0,
        ativo: editTarget.ativo,
        destaque_pdv: editTarget.destaque_pdv,
        perfil_tributario_id: editTarget.perfil_tributario_id ?? undefined,
      }
      await patchProduto(editTarget.id, req)
      setEditTarget(null)
      load(page, q)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      setSaveErr(detail ?? 'Erro ao atualizar produto.')
    } finally {
      setSaving(false)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-primary">Produtos</h1>
        <Button variant="primary" size="sm" onClick={() => navigate('/gerencial/cadastro-rapido')}>
          <Plus size={14} /> Novo produto
        </Button>
      </div>

      {/* Busca */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <Input
          placeholder="Buscar por descrição, código ou SKU..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="flex-1"
        />
        <Button type="submit" variant="secondary" size="sm">
          <Search size={14} />
        </Button>
      </form>

      {loading && (
        <div className="flex items-center gap-2 text-text-muted text-sm">
          <Loader2 size={16} className="animate-spin" /> Carregando...
        </div>
      )}
      {erro && <p className="text-sm text-danger-text">{erro}</p>}

      {/* Tabela */}
      <div className="overflow-auto rounded-xl border border-border bg-bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-muted">
              <th className="px-3 py-2.5">Descrição</th>
              <th className="px-3 py-2.5">Cód. barras</th>
              <th className="px-3 py-2.5">Un.</th>
              <th className="px-3 py-2.5 text-right">Preço</th>
              <th className="px-3 py-2.5">Status</th>
              <th className="px-3 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {produtos.map((p) => (
              <tr key={p.id} className="border-b border-border last:border-0 hover:bg-bg-surface-2">
                <td className="px-3 py-2.5 font-medium text-text-primary max-w-[200px] truncate">
                  {p.descricao}
                </td>
                <td className="px-3 py-2.5 text-text-secondary font-mono text-xs">
                  {p.codigo_barras_principal ?? '—'}
                </td>
                <td className="px-3 py-2.5 text-text-secondary">{p.unidade_codigo ?? '—'}</td>
                <td className="px-3 py-2.5 text-right font-mono">{formatCurrency(p.preco_venda)}</td>
                <td className="px-3 py-2.5">
                  <StatusBadge ativo={p.ativo} />
                </td>
                <td className="px-3 py-2.5 text-right">
                  <button
                    onClick={() => openEdit(p)}
                    className="rounded p-1 text-text-muted hover:text-text-primary hover:bg-bg-surface-2"
                  >
                    <Pencil size={14} />
                  </button>
                </td>
              </tr>
            ))}
            {!loading && produtos.length === 0 && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-sm text-text-muted">
                  Nenhum produto encontrado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Paginação */}
      {totalPages > 1 && (
        <div className="flex items-center gap-2 text-sm">
          <button
            disabled={page === 1}
            onClick={() => { setPage(page - 1); load(page - 1, q) }}
            className="rounded-lg border border-border px-3 py-1.5 disabled:opacity-40 hover:bg-bg-surface-2"
          >
            ← Anterior
          </button>
          <span className="text-text-muted">
            {page} / {totalPages}
          </span>
          <button
            disabled={page === totalPages}
            onClick={() => { setPage(page + 1); load(page + 1, q) }}
            className="rounded-lg border border-border px-3 py-1.5 disabled:opacity-40 hover:bg-bg-surface-2"
          >
            Próximo →
          </button>
        </div>
      )}

      {/* Modal: editar produto */}
      <Modal
        open={!!editTarget}
        onClose={() => setEditTarget(null)}
        title="Editar produto"
        size="lg"
      >
        {editTarget && (
          <form onSubmit={handlePatch} className="flex flex-col gap-3 p-4">
            <Input
              label="Descrição *"
              value={editTarget.descricao}
              onChange={(e) => setEditTarget({ ...editTarget, descricao: e.target.value })}
              required
            />
            <Input
              label="Descrição PDV"
              value={editTarget.descricao_pdv ?? ''}
              onChange={(e) => setEditTarget({ ...editTarget, descricao_pdv: e.target.value })}
            />
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Preço de venda *</label>
              <input
                type="text"
                inputMode="decimal"
                required
                value={editPrecoStr}
                onChange={(e) => setEditPrecoStr(filterDecimal(e.target.value))}
                onFocus={(e) => e.currentTarget.select()}
                className="w-full rounded-lg border border-border bg-bg-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Perfil tributário</label>
              <select
                value={editTarget.perfil_tributario_id ?? ''}
                onChange={(e) =>
                  setEditTarget({ ...editTarget, perfil_tributario_id: e.target.value || null })
                }
                className="w-full rounded-lg border border-border bg-bg-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
              >
                <option value="">Nenhum</option>
                {perfis.map((p) => (
                  <option key={p.id} value={p.id}>{p.nome}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={editTarget.ativo}
                  onChange={(e) => setEditTarget({ ...editTarget, ativo: e.target.checked })}
                  className="rounded"
                />
                Ativo
              </label>
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={editTarget.destaque_pdv}
                  onChange={(e) => setEditTarget({ ...editTarget, destaque_pdv: e.target.checked })}
                  className="rounded"
                />
                Destaque PDV
              </label>
            </div>
            {saveErr && <p className="text-xs text-danger-text">{saveErr}</p>}
            <div className="flex justify-end gap-2 pt-1">
              <Button variant="ghost" size="sm" type="button" onClick={() => setEditTarget(null)}>
                Cancelar
              </Button>
              <Button variant="primary" size="sm" type="submit" disabled={saving}>
                {saving ? <Loader2 size={14} className="animate-spin" /> : null}
                Salvar
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  )
}

function StatusBadge({ ativo }: { ativo: boolean }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
        ativo ? 'bg-success/15 text-success-text' : 'bg-bg-surface-2 text-text-muted'
      }`}
    >
      {ativo ? 'Ativo' : 'Inativo'}
    </span>
  )
}
