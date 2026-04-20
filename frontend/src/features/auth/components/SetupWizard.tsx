import { useState } from 'react'
import { Zap, Building2, User, Monitor, CheckCircle, ChevronRight, Loader2 } from 'lucide-react'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { inicializarSistema } from '@/services/api/setup'
import type { SetupInicializarRequest } from '@/services/api/setup'

interface Props {
  onConcluido: (empresaId: string) => void
}

type Etapa = 'empresa' | 'usuarios' | 'revisao' | 'sucesso'

const REGIME_OPTIONS = [
  { value: 'SN', label: 'Simples Nacional' },
  { value: 'LP', label: 'Lucro Presumido' },
  { value: 'LR', label: 'Lucro Real' },
] as const

const VAZIO: SetupInicializarRequest = {
  empresa: { razao_social: '', nome_fantasia: '', cnpj: '', regime_tributario: 'SN' },
  gerente: { nome: '', email: '', senha: '', codigo_operador: '', pin: '' },
  operador: { nome: '', email: '', codigo_operador: '', pin: '' },
  caixa_descricao: 'Caixa Principal',
}

export function SetupWizard({ onConcluido }: Props) {
  const [etapa, setEtapa] = useState<Etapa>('empresa')
  const [dados, setDados] = useState<SetupInicializarRequest>(VAZIO)
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState('')

  function setEmpresa(field: string, value: string) {
    setDados((d) => ({ ...d, empresa: { ...d.empresa, [field]: value } }))
  }

  function setGerente(field: string, value: string) {
    setDados((d) => ({ ...d, gerente: { ...d.gerente, [field]: value } }))
  }

  function setOperador(field: string, value: string) {
    setDados((d) => ({ ...d, operador: { ...d.operador, [field]: value } }))
  }

  async function handleFinalizar() {
    setErro('')
    setLoading(true)
    try {
      const res = await inicializarSistema(dados)
      setEtapa('sucesso')
      // Aguarda um tick para o usuário ver o sucesso, depois redireciona
      setTimeout(() => onConcluido(res.empresa_id), 3000)
    } catch (e: unknown) {
      const msg =
        e instanceof Error
          ? e.message
          : (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
            'Erro ao inicializar sistema.'
      setErro(msg)
    } finally {
      setLoading(false)
    }
  }

  const ETAPAS: { id: Etapa; label: string; icon: React.ReactNode }[] = [
    { id: 'empresa', label: 'Empresa', icon: <Building2 size={14} /> },
    { id: 'usuarios', label: 'Usuários', icon: <User size={14} /> },
    { id: 'revisao', label: 'Revisão', icon: <Monitor size={14} /> },
  ]

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg-base p-4">
      <div className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(rgba(99,102,241,1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(99,102,241,1) 1px, transparent 1px)`,
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative w-full max-w-lg">
        {/* Header */}
        <div className="mb-6 text-center">
          <div className="mb-3 flex justify-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-accent/15 ring-1 ring-accent/30">
              <Zap size={28} className="text-accent" fill="currentColor" />
            </div>
          </div>
          <h1 className="text-xl font-bold text-text-primary">
            Bem-vindo ao Zênite<span className="text-accent"> PDV</span>
          </h1>
          <p className="mt-1 text-sm text-text-muted">Configure seu sistema em 3 etapas simples</p>
        </div>

        {/* Progress */}
        {etapa !== 'sucesso' && (
          <div className="mb-6 flex items-center justify-center gap-2">
            {ETAPAS.map((e, i) => (
              <div key={e.id} className="flex items-center gap-2">
                <div
                  className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors
                    ${etapa === e.id ? 'bg-accent text-white' : 'bg-bg-surface-2 text-text-muted'}`}
                >
                  {e.icon} {e.label}
                </div>
                {i < ETAPAS.length - 1 && <ChevronRight size={14} className="text-text-muted" />}
              </div>
            ))}
          </div>
        )}

        {/* Card */}
        <div className="rounded-2xl border border-border bg-bg-surface p-8 shadow-2xl">
          {/* ── ETAPA 1: EMPRESA ─────────────────────────────── */}
          {etapa === 'empresa' && (
            <div className="flex flex-col gap-4">
              <h2 className="font-semibold text-text-primary">Dados da Empresa</h2>

              <Input
                label="Razão Social *"
                value={dados.empresa.razao_social}
                onChange={(e) => setEmpresa('razao_social', e.target.value)}
                placeholder="Empresa Exemplo Ltda"
              />
              <Input
                label="Nome Fantasia"
                value={dados.empresa.nome_fantasia ?? ''}
                onChange={(e) => setEmpresa('nome_fantasia', e.target.value)}
                placeholder="Loja Exemplo"
              />
              <Input
                label="CNPJ * (somente números)"
                value={dados.empresa.cnpj}
                onChange={(e) => setEmpresa('cnpj', e.target.value.replace(/\D/g, ''))}
                placeholder="00000000000000"
                maxLength={14}
              />

              <div className="flex flex-col gap-1">
                <label className="text-xs font-medium text-text-secondary">
                  Regime Tributário *
                </label>
                <select
                  className="w-full rounded-lg border border-border bg-bg-surface-2 px-3 py-2.5 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/40"
                  value={dados.empresa.regime_tributario}
                  onChange={(e) => setEmpresa('regime_tributario', e.target.value)}
                >
                  {REGIME_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>

              <Button
                className="mt-2 w-full"
                onClick={() => setEtapa('usuarios')}
                disabled={!dados.empresa.razao_social || dados.empresa.cnpj.length < 11}
              >
                Próximo <ChevronRight size={16} />
              </Button>
            </div>
          )}

          {/* ── ETAPA 2: USUÁRIOS ────────────────────────────── */}
          {etapa === 'usuarios' && (
            <div className="flex flex-col gap-5">
              <h2 className="font-semibold text-text-primary">Gerente e Operador Iniciais</h2>

              <div className="rounded-xl border border-accent/20 bg-accent/5 p-4">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-accent">
                  Primeiro Gerente (acesso à retaguarda)
                </p>
                <div className="flex flex-col gap-3">
                  <Input label="Nome *" value={dados.gerente.nome} onChange={(e) => setGerente('nome', e.target.value)} placeholder="João Silva" />
                  <Input label="E-mail *" type="email" value={dados.gerente.email} onChange={(e) => setGerente('email', e.target.value)} placeholder="gerente@empresa.com" />
                  <Input label="Senha *" type="password" value={dados.gerente.senha} onChange={(e) => setGerente('senha', e.target.value)} placeholder="mínimo 6 caracteres" />
                  <div className="grid grid-cols-2 gap-3">
                    <Input label="Código operador *" value={dados.gerente.codigo_operador} onChange={(e) => setGerente('codigo_operador', e.target.value)} placeholder="Ex: 900" />
                    <Input label="PIN *" type="password" value={dados.gerente.pin} onChange={(e) => setGerente('pin', e.target.value)} placeholder="4–6 dígitos" maxLength={6} />
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-border bg-bg-surface-2 p-4">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Primeiro Operador de Caixa
                </p>
                <div className="flex flex-col gap-3">
                  <Input label="Nome *" value={dados.operador.nome} onChange={(e) => setOperador('nome', e.target.value)} placeholder="Maria Santos" />
                  <Input label="E-mail *" type="email" value={dados.operador.email} onChange={(e) => setOperador('email', e.target.value)} placeholder="operador@empresa.com" />
                  <div className="grid grid-cols-2 gap-3">
                    <Input label="Código operador *" value={dados.operador.codigo_operador} onChange={(e) => setOperador('codigo_operador', e.target.value)} placeholder="Ex: 001" />
                    <Input label="PIN *" type="password" value={dados.operador.pin} onChange={(e) => setOperador('pin', e.target.value)} placeholder="4–6 dígitos" maxLength={6} />
                  </div>
                </div>
              </div>

              <div className="flex gap-3">
                <Button variant="ghost" className="flex-1" onClick={() => setEtapa('empresa')}>
                  Voltar
                </Button>
                <Button
                  className="flex-1"
                  onClick={() => setEtapa('revisao')}
                  disabled={
                    !dados.gerente.nome || !dados.gerente.email || !dados.gerente.senha ||
                    !dados.gerente.codigo_operador || dados.gerente.pin.length < 4 ||
                    !dados.operador.nome || !dados.operador.email ||
                    !dados.operador.codigo_operador || dados.operador.pin.length < 4
                  }
                >
                  Revisar <ChevronRight size={16} />
                </Button>
              </div>
            </div>
          )}

          {/* ── ETAPA 3: REVISÃO ─────────────────────────────── */}
          {etapa === 'revisao' && (
            <div className="flex flex-col gap-4">
              <h2 className="font-semibold text-text-primary">Confirme os dados</h2>

              <div className="flex flex-col gap-2 rounded-xl border border-border bg-bg-surface-2 p-4 text-sm">
                <Row label="Razão social" value={dados.empresa.razao_social} />
                {dados.empresa.nome_fantasia && <Row label="Nome fantasia" value={dados.empresa.nome_fantasia} />}
                <Row label="CNPJ" value={dados.empresa.cnpj} />
                <Row label="Regime" value={REGIME_OPTIONS.find(o => o.value === dados.empresa.regime_tributario)?.label ?? ''} />
              </div>

              <div className="flex flex-col gap-2 rounded-xl border border-border bg-bg-surface-2 p-4 text-sm">
                <p className="text-xs font-semibold text-text-muted uppercase mb-1">Gerente</p>
                <Row label="Nome" value={dados.gerente.nome} />
                <Row label="E-mail" value={dados.gerente.email} />
                <Row label="Código" value={dados.gerente.codigo_operador} />
              </div>

              <div className="flex flex-col gap-2 rounded-xl border border-border bg-bg-surface-2 p-4 text-sm">
                <p className="text-xs font-semibold text-text-muted uppercase mb-1">Operador</p>
                <Row label="Nome" value={dados.operador.nome} />
                <Row label="E-mail" value={dados.operador.email} />
                <Row label="Código" value={dados.operador.codigo_operador} />
              </div>

              {erro && (
                <p className="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger-text">{erro}</p>
              )}

              <div className="flex gap-3">
                <Button variant="ghost" className="flex-1" onClick={() => setEtapa('usuarios')} disabled={loading}>
                  Voltar
                </Button>
                <Button className="flex-1" onClick={handleFinalizar} disabled={loading}>
                  {loading ? <><Loader2 size={16} className="animate-spin" /> Criando...</> : 'Finalizar configuração'}
                </Button>
              </div>
            </div>
          )}

          {/* ── SUCESSO ──────────────────────────────────────── */}
          {etapa === 'sucesso' && (
            <div className="flex flex-col items-center gap-4 py-4 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-success/15 ring-2 ring-success/30">
                <CheckCircle size={36} className="text-success-text" />
              </div>
              <h2 className="text-lg font-bold text-text-primary">Sistema configurado!</h2>
              <p className="text-sm text-text-muted">
                Empresa, gerente, operador e caixa criados com sucesso.
                <br />
                Redirecionando para o login...
              </p>
              <Loader2 size={20} className="animate-spin text-text-muted" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-text-muted">{label}</span>
      <span className="font-medium text-text-primary">{value}</span>
    </div>
  )
}
