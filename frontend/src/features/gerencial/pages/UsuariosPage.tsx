import { useEffect, useState } from 'react'
import { Plus, Loader2, Power, Pencil, KeyRound } from 'lucide-react'
import {
  listUsuarios,
  createUsuario,
  patchUsuarioStatus,
  updateUsuario,
  updateUsuarioPin,
} from '@/services/api/gerencial'
import type { UsuarioListDTO, UsuarioCreateRequest, UsuarioUpdateRequest } from '@/shared/types/api'
import { Modal } from '@/shared/ui/Modal'
import { Input } from '@/shared/ui/Input'
import { Button } from '@/shared/ui/Button'
import { formatDateTime } from '@/shared/utils/format'
import { useAuthStore } from '@/store/authStore'

// Perfis disponíveis para criar/editar — gerente só se o usuário logado for admin+
const PERFIS_OPERACIONAIS = [
  { value: 'operador_caixa', label: 'Operador de Caixa' },
  { value: 'estoquista', label: 'Estoquista' },
  { value: 'gerente', label: 'Gerente' },
]

// Mapeamento de nível de perfil para comparação
const PERFIL_NIVEL: Record<string, number> = {
  operador_caixa: 0,
  estoquista: 1,
  gerente: 2,
  admin: 3,
  super_admin: 4,
}

const VAZIO_CREATE: UsuarioCreateRequest = {
  nome: '',
  email: '',
  senha: '',
  perfil: 'operador_caixa',
  codigo_operador: '',
  pin: '',
}

const PERFIL_LABEL: Record<string, string> = {
  operador_caixa: 'Operador de Caixa',
  estoquista: 'Estoquista',
  gerente: 'Gerente',
  admin: 'Admin',
  super_admin: 'Super Admin',
}

function apiErr(err: unknown): string {
  return (
    (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
    'Erro inesperado.'
  )
}

export function UsuariosPage() {
  const [usuarios, setUsuarios] = useState<UsuarioListDTO[]>([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')
  const currentUser = useAuthStore((s) => s.user)
  const currentNivel = PERFIL_NIVEL[currentUser?.perfil ?? ''] ?? 0

  // Modal criar
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<UsuarioCreateRequest>(VAZIO_CREATE)
  const [saving, setSaving] = useState(false)
  const [saveErr, setSaveErr] = useState('')

  // Modal editar
  const [editTarget, setEditTarget] = useState<UsuarioListDTO | null>(null)
  const [editForm, setEditForm] = useState<UsuarioUpdateRequest>({ nome: '', perfil: 'operador_caixa' })
  const [editSaving, setEditSaving] = useState(false)
  const [editErr, setEditErr] = useState('')

  // Modal alterar PIN
  const [pinTarget, setPinTarget] = useState<UsuarioListDTO | null>(null)
  const [newPin, setNewPin] = useState('')
  const [pinSaving, setPinSaving] = useState(false)
  const [pinErr, setPinErr] = useState('')

  // Toggle ativo
  const [togglingId, setTogglingId] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setErro('')
    try {
      const res = await listUsuarios()
      setUsuarios(res)
    } catch {
      setErro('Erro ao carregar usuários.')
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
      await createUsuario({
        ...form,
        codigo_operador: form.codigo_operador || undefined,
        pin: form.pin || undefined,
      })
      setShowCreate(false)
      setForm(VAZIO_CREATE)
      load()
    } catch (err: unknown) {
      setSaveErr(apiErr(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleToggle(u: UsuarioListDTO) {
    setTogglingId(u.id)
    try {
      const updated = await patchUsuarioStatus(u.id, !u.ativo)
      setUsuarios((prev) => prev.map((x) => (x.id === updated.id ? updated : x)))
    } catch (err: unknown) {
      alert(apiErr(err))
    } finally {
      setTogglingId(null)
    }
  }

  function openEdit(u: UsuarioListDTO) {
    setEditTarget(u)
    setEditForm({ nome: u.nome, perfil: u.perfil, codigo_operador: u.codigo_operador ?? '' })
    setEditErr('')
  }

  async function handleEdit(e: React.FormEvent) {
    e.preventDefault()
    if (!editTarget) return
    setEditSaving(true)
    setEditErr('')
    try {
      const updated = await updateUsuario(editTarget.id, {
        nome: editForm.nome,
        perfil: editForm.perfil,
        codigo_operador: editForm.codigo_operador || undefined,
      })
      setUsuarios((prev) => prev.map((x) => (x.id === updated.id ? updated : x)))
      setEditTarget(null)
    } catch (err: unknown) {
      setEditErr(apiErr(err))
    } finally {
      setEditSaving(false)
    }
  }

  function openPin(u: UsuarioListDTO) {
    setPinTarget(u)
    setNewPin('')
    setPinErr('')
  }

  async function handlePin(e: React.FormEvent) {
    e.preventDefault()
    if (!pinTarget) return
    if (!/^\d{4,6}$/.test(newPin)) {
      setPinErr('PIN deve ter 4 a 6 dígitos numéricos.')
      return
    }
    setPinSaving(true)
    setPinErr('')
    try {
      await updateUsuarioPin(pinTarget.id, { pin: newPin })
      setPinTarget(null)
    } catch (err: unknown) {
      setPinErr(apiErr(err))
    } finally {
      setPinSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-primary">Usuários</h1>
        <Button variant="primary" size="sm" onClick={() => { setForm(VAZIO_CREATE); setSaveErr(''); setShowCreate(true) }}>
          <Plus size={14} /> Novo usuário
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
              <th className="px-3 py-2.5">Nome</th>
              <th className="px-3 py-2.5">E-mail</th>
              <th className="px-3 py-2.5">Perfil</th>
              <th className="px-3 py-2.5">Cód. operador</th>
              <th className="px-3 py-2.5">Último acesso</th>
              <th className="px-3 py-2.5">Status</th>
              <th className="px-3 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {usuarios.map((u) => (
              <tr key={u.id} className="border-b border-border last:border-0 hover:bg-bg-surface-2">
                <td className="px-3 py-2.5 font-medium text-text-primary">{u.nome}</td>
                <td className="px-3 py-2.5 text-text-secondary">{u.email}</td>
                <td className="px-3 py-2.5 text-text-secondary">
                  {PERFIL_LABEL[u.perfil] ?? u.perfil}
                </td>
                <td className="px-3 py-2.5 font-mono text-xs text-text-muted">
                  {u.codigo_operador ?? '—'}
                </td>
                <td className="px-3 py-2.5 text-xs text-text-muted">
                  {u.ultimo_acesso ? formatDateTime(u.ultimo_acesso) : '—'}
                </td>
                <td className="px-3 py-2.5">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      u.ativo
                        ? 'bg-success/15 text-success-text'
                        : 'bg-danger/15 text-danger-text'
                    }`}
                  >
                    {u.ativo ? 'Ativo' : 'Inativo'}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-right">
                  <div className="flex items-center justify-end gap-1">
                    {u.id !== currentUser?.id && (PERFIL_NIVEL[u.perfil] ?? 0) < currentNivel && (
                      <>
                        <button
                          title="Editar usuário"
                          onClick={() => openEdit(u)}
                          className="rounded p-1 text-text-muted transition-colors hover:bg-bg-surface-2 hover:text-text-primary"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          title="Alterar PIN"
                          onClick={() => openPin(u)}
                          className="rounded p-1 text-text-muted transition-colors hover:bg-bg-surface-2 hover:text-text-primary"
                        >
                          <KeyRound size={14} />
                        </button>
                      </>
                    )}
                    {u.id !== currentUser?.id && (
                      <button
                        title={u.ativo ? 'Desativar' : 'Ativar'}
                        onClick={() => handleToggle(u)}
                        disabled={togglingId === u.id}
                        className={`rounded p-1 transition-colors ${
                          u.ativo
                            ? 'text-danger-text hover:bg-danger/10'
                            : 'text-success-text hover:bg-success/10'
                        } disabled:opacity-40`}
                      >
                        {togglingId === u.id ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <Power size={14} />
                        )}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {!loading && usuarios.length === 0 && (
              <tr>
                <td colSpan={7} className="py-8 text-center text-sm text-text-muted">
                  Nenhum usuário encontrado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Modal criar usuário */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Novo usuário" size="md">
        <form onSubmit={handleCreate} className="flex flex-col gap-3 p-4">
          <Input
            label="Nome completo *"
            value={form.nome}
            onChange={(e) => setForm({ ...form, nome: e.target.value })}
            required
          />
          <Input
            label="E-mail (opcional)"
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <Input
            label="Senha *"
            type="password"
            value={form.senha}
            onChange={(e) => setForm({ ...form, senha: e.target.value })}
            required
          />
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">Perfil *</label>
            <select
              required
              value={form.perfil}
              onChange={(e) => setForm({ ...form, perfil: e.target.value })}
              className="w-full rounded-lg border border-border bg-bg-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
            >
              {PERFIS_OPERACIONAIS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Código operador"
              value={form.codigo_operador}
              onChange={(e) => setForm({ ...form, codigo_operador: e.target.value })}
            />
            <Input
              label="PIN (4-6 dígitos)"
              type="password"
              maxLength={6}
              value={form.pin}
              onChange={(e) => setForm({ ...form, pin: e.target.value })}
            />
          </div>
          {saveErr && <p className="text-xs text-danger-text">{saveErr}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" size="sm" type="button" onClick={() => setShowCreate(false)}>
              Cancelar
            </Button>
            <Button variant="primary" size="sm" type="submit" disabled={saving}>
              {saving ? <Loader2 size={14} className="animate-spin" /> : null}
              Criar usuário
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal editar usuário */}
      <Modal open={!!editTarget} onClose={() => setEditTarget(null)} title="Editar usuário" size="md">
        <form onSubmit={handleEdit} className="flex flex-col gap-3 p-4">
          <Input
            label="Nome completo *"
            value={editForm.nome}
            onChange={(e) => setEditForm({ ...editForm, nome: e.target.value })}
            required
          />
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">Perfil *</label>
            <select
              required
              value={editForm.perfil}
              onChange={(e) => setEditForm({ ...editForm, perfil: e.target.value })}
              className="w-full rounded-lg border border-border bg-bg-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
            >
              {PERFIS_OPERACIONAIS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>
          <Input
            label="Código operador"
            value={editForm.codigo_operador ?? ''}
            onChange={(e) => setEditForm({ ...editForm, codigo_operador: e.target.value })}
          />
          {editErr && <p className="text-xs text-danger-text">{editErr}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" size="sm" type="button" onClick={() => setEditTarget(null)}>
              Cancelar
            </Button>
            <Button variant="primary" size="sm" type="submit" disabled={editSaving}>
              {editSaving ? <Loader2 size={14} className="animate-spin" /> : null}
              Salvar alterações
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal alterar PIN */}
      <Modal open={!!pinTarget} onClose={() => setPinTarget(null)} title={`Alterar PIN — ${pinTarget?.nome ?? ''}`} size="sm">
        <form onSubmit={handlePin} className="flex flex-col gap-3 p-4">
          <Input
            label="Novo PIN (4-6 dígitos) *"
            type="password"
            maxLength={6}
            value={newPin}
            onChange={(e) => setNewPin(e.target.value)}
            required
          />
          {pinErr && <p className="text-xs text-danger-text">{pinErr}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" size="sm" type="button" onClick={() => setPinTarget(null)}>
              Cancelar
            </Button>
            <Button variant="primary" size="sm" type="submit" disabled={pinSaving}>
              {pinSaving ? <Loader2 size={14} className="animate-spin" /> : null}
              Alterar PIN
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
