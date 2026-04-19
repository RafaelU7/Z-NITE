import { useEffect, useState } from 'react'
import { Plus, Loader2 } from 'lucide-react'
import { listCaixas, createCaixa, patchCaixaStatus } from '@/services/api/gerencial'
import type { CaixaDTO, CaixaCreateRequest } from '@/shared/types/api'
import { Modal } from '@/shared/ui/Modal'
import { Input } from '@/shared/ui/Input'
import { Button } from '@/shared/ui/Button'

const VAZIO: CaixaCreateRequest = { numero: 1, descricao: '', numero_serie: '' }

export function CaixasPage() {
  const [caixas, setCaixas] = useState<CaixaDTO[]>([])
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<CaixaCreateRequest>(VAZIO)
  const [saving, setSaving] = useState(false)
  const [saveErr, setSaveErr] = useState('')

  async function load() {
    setLoading(true)
    setErro('')
    try {
      setCaixas(await listCaixas())
    } catch {
      setErro('Erro ao carregar caixas.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setSaveErr('')
    try {
      await createCaixa({
        numero: Number(form.numero),
        descricao: form.descricao || undefined,
        numero_serie: form.numero_serie || undefined,
      })
      setShowCreate(false)
      setForm(VAZIO)
      load()
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      setSaveErr(detail ?? 'Erro ao criar caixa.')
    } finally {
      setSaving(false)
    }
  }

  async function toggleAtivo(c: CaixaDTO) {
    try {
      const updated = await patchCaixaStatus(c.id, !c.ativo)
      setCaixas((prev) => prev.map((x) => (x.id === updated.id ? updated : x)))
    } catch {
      alert('Erro ao alterar status do caixa.')
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-primary">Caixas</h1>
        <Button variant="primary" size="sm" onClick={() => { setForm(VAZIO); setSaveErr(''); setShowCreate(true) }}>
          <Plus size={14} /> Novo caixa
        </Button>
      </div>

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
              <th className="px-3 py-2.5">Nº</th>
              <th className="px-3 py-2.5">Descrição</th>
              <th className="px-3 py-2.5">Nº Série</th>
              <th className="px-3 py-2.5">Status</th>
              <th className="px-3 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {caixas.map((c) => (
              <tr key={c.id} className="border-b border-border last:border-0 hover:bg-bg-surface-2">
                <td className="px-3 py-2.5 font-mono font-medium text-text-primary">{c.numero}</td>
                <td className="px-3 py-2.5 text-text-secondary">{c.descricao ?? '—'}</td>
                <td className="px-3 py-2.5 text-text-muted font-mono text-xs">{c.numero_serie ?? '—'}</td>
                <td className="px-3 py-2.5">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${c.ativo ? 'bg-success/15 text-success-text' : 'bg-danger/15 text-danger-text'}`}>
                    {c.ativo ? 'Ativo' : 'Inativo'}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-right">
                  <button
                    onClick={() => toggleAtivo(c)}
                    className="rounded px-2 py-1 text-xs text-text-muted hover:text-text-primary hover:bg-bg-surface-2"
                  >
                    {c.ativo ? 'Desativar' : 'Ativar'}
                  </button>
                </td>
              </tr>
            ))}
            {!loading && caixas.length === 0 && (
              <tr>
                <td colSpan={5} className="py-8 text-center text-sm text-text-muted">
                  Nenhum caixa cadastrado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Novo caixa" size="sm">
        <form onSubmit={handleCreate} className="flex flex-col gap-3 p-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">Número *</label>
            <input
              type="number"
              min={1}
              required
              value={form.numero}
              onChange={(e) => setForm({ ...form, numero: parseInt(e.target.value) || 1 })}
              className="w-full rounded-lg border border-border bg-bg-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
            />
          </div>
          <Input
            label="Descrição"
            placeholder="Ex: Caixa Principal"
            value={form.descricao}
            onChange={(e) => setForm({ ...form, descricao: e.target.value })}
          />
          <Input
            label="Número de série"
            placeholder="Opcional"
            value={form.numero_serie}
            onChange={(e) => setForm({ ...form, numero_serie: e.target.value })}
          />
          {saveErr && <p className="text-xs text-danger-text">{saveErr}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" size="sm" type="button" onClick={() => setShowCreate(false)}>
              Cancelar
            </Button>
            <Button variant="primary" size="sm" type="submit" disabled={saving}>
              {saving ? <Loader2 size={14} className="animate-spin" /> : null}
              Criar caixa
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
