import { useState } from 'react'
import { Zap, Store, User, CheckCircle, ChevronRight, Loader2, Eye, EyeOff } from 'lucide-react'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { setupEmpresa } from '@/services/api/setup'
import type { SetupEmpresaRequest } from '@/services/api/setup'

interface Props {
  onConcluido: (empresaId: string) => void
  preview?: boolean
}

type Etapa = 'mercado' | 'gerente' | 'sucesso'

function getInitials(name: string): string {
  return name.split(' ').filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase()
}

const VAZIO: SetupEmpresaRequest = {
  empresa: { nome_fantasia: '', razao_social: '', cnpj: '', telefone: '' },
  gerente: { nome: '', email: '', codigo_operador: '900', pin: '' },
  caixa_descricao: 'Caixa 01 - Principal',
}

export function SetupWizard({ onConcluido, preview = false }: Props) {
  const [etapa, setEtapa] = useState<Etapa>('mercado')
  const [dados, setDados] = useState<SetupEmpresaRequest>(VAZIO)
  const [confirmarPin, setConfirmarPin] = useState('')
  const [mostrarPin, setMostrarPin] = useState(false)
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState('')

  function setEmp(field: keyof SetupEmpresaRequest['empresa'], value: string) {
    setDados((d) => ({ ...d, empresa: { ...d.empresa, [field]: value } }))
  }

  function setGer(field: keyof SetupEmpresaRequest['gerente'], value: string) {
    setDados((d) => ({ ...d, gerente: { ...d.gerente, [field]: value } }))
  }

  const nomeFantasia = dados.empresa.nome_fantasia.trim()
  const initials = nomeFantasia ? getInitials(nomeFantasia) : '?'

  const podeAvancarMercado = nomeFantasia.length >= 2

  const podeAvancarGerente =
    dados.gerente.nome.trim().length >= 2 &&
    dados.gerente.codigo_operador.trim().length >= 1 &&
    /^\d{4,6}$/.test(dados.gerente.pin) &&
    dados.gerente.pin === confirmarPin

  async function handleFinalizar() {
    setErro('')
    if (!podeAvancarGerente) return
    setLoading(true)
    try {
      if (preview) {
        setEtapa('sucesso')
        setTimeout(() => onConcluido('preview-mode'), 2500)
        return
      }

      // Limpa campos opcionais vazios
      const payload: SetupEmpresaRequest = {
        ...dados,
        empresa: {
          nome_fantasia: dados.empresa.nome_fantasia.trim(),
          razao_social: dados.empresa.razao_social?.trim() || undefined,
          cnpj: dados.empresa.cnpj?.replace(/\D/g, '') || undefined,
          telefone: dados.empresa.telefone?.trim() || undefined,
        },
        gerente: {
          nome: dados.gerente.nome.trim(),
          email: dados.gerente.email?.trim() || undefined,
          codigo_operador: dados.gerente.codigo_operador.trim(),
          pin: dados.gerente.pin,
        },
      }
      const res = await setupEmpresa(payload)
      setEtapa('sucesso')
      setTimeout(() => onConcluido(res.empresa_id), 2500)
    } catch (e: unknown) {
      const detail =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErro(detail ?? 'Erro ao configurar o sistema. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="flex min-h-screen items-center justify-center p-4"
      style={{ background: 'radial-gradient(ellipse at 40% 45%, #0f3444 0%, #0a2030 50%, #07151d 100%)' }}
    >
      {/* Teal grid overlay */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.025]"
        style={{
          backgroundImage: `linear-gradient(rgba(25,199,181,1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(25,199,181,1) 1px, transparent 1px)`,
          backgroundSize: '40px 40px',
        }}
      />
      <div
        className="pointer-events-none absolute inset-0"
        style={{ background: 'radial-gradient(ellipse 600px 400px at 50% 50%, rgba(25,199,181,0.04) 0%, transparent 70%)' }}
      />

      <div className="relative w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="mb-3 flex justify-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent/15 ring-1 ring-accent/30 shadow-lg shadow-accent/10">
              <Zap size={28} className="text-accent" fill="currentColor" />
            </div>
          </div>
          {preview && (
            <div className="mb-3 inline-flex items-center rounded-full border border-warning/30 bg-warning/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-warning-text">
              Preview QA
            </div>
          )}
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            Primeiro acesso
          </h1>
          <p className="mt-1.5 text-sm text-text-muted">
            Cadastre seu mercado — leva menos de 2 minutos
          </p>
        </div>

        {/* Steps pill */}
        {etapa !== 'sucesso' && (
          <div className="mb-6 flex items-center justify-center gap-3 text-xs">
            {(['mercado', 'gerente'] as const).map((e, i) => (
              <div key={e} className="flex items-center gap-3">
                <div
                  className={`flex items-center gap-1.5 rounded-full px-3 py-1 font-medium transition-all
                    ${etapa === e
                      ? 'bg-accent text-white shadow-sm shadow-accent/40'
                      : 'bg-bg-surface-2 text-text-muted'}`}
                >
                  {e === 'mercado' ? <Store size={12} /> : <User size={12} />}
                  {e === 'mercado' ? 'Mercado' : 'Gerente'}
                </div>
                {i === 0 && <ChevronRight size={12} className="text-text-muted" />}
              </div>
            ))}
          </div>
        )}

        {/* Card principal */}
        <div className="rounded-2xl border border-pdv-border bg-pdv-surface p-8 shadow-2xl shadow-black/50">

          {/* â”€â”€ ETAPA: MERCADO â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
          {etapa === 'mercado' && (
            <div className="flex flex-col gap-5">
              {/* Avatar preview */}
              {nomeFantasia && (
                <div className="flex items-center gap-3 rounded-xl border border-border bg-bg-surface-2 p-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent/20 text-sm font-bold text-accent">
                    {initials}
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-text-primary">{nomeFantasia}</p>
                    <p className="text-xs text-text-muted">Aparência no PDV e Retaguarda</p>
                  </div>
                </div>
              )}

              <div>
                <Input
                  label="Nome do mercado *"
                  value={dados.empresa.nome_fantasia}
                  onChange={(e) => setEmp('nome_fantasia', e.target.value)}
                  placeholder="Ex: Mercadinho do João"
                  autoFocus
                />
                <p className="mt-1 text-xs text-text-muted">
                  Usado no PDV, relatórios e retaguarda.
                </p>
              </div>

              <Input
                label="Razão Social (opcional)"
                value={dados.empresa.razao_social ?? ''}
                onChange={(e) => setEmp('razao_social', e.target.value)}
                placeholder="Ex: João Silva ME"
              />

              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="CNPJ (opcional)"
                  value={dados.empresa.cnpj ?? ''}
                  onChange={(e) => setEmp('cnpj', e.target.value.replace(/\D/g, ''))}
                  placeholder="00000000000000"
                  maxLength={14}
                />
                <Input
                  label="Telefone (opcional)"
                  value={dados.empresa.telefone ?? ''}
                  onChange={(e) => setEmp('telefone', e.target.value)}
                  placeholder="(00) 00000-0000"
                />
              </div>

              <Button
                className="mt-1 w-full"
                onClick={() => setEtapa('gerente')}
                disabled={!podeAvancarMercado}
              >
                Próximo — Dados do gerente <ChevronRight size={16} />
              </Button>
            </div>
          )}

          {/* â”€â”€ ETAPA: GERENTE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
          {etapa === 'gerente' && (
            <div className="flex flex-col gap-5">
              <div className="rounded-xl border border-accent/20 bg-accent/5 px-4 py-3 text-xs text-text-muted">
                O gerente terá acesso à <span className="font-semibold text-text-primary">Retaguarda</span> (produtos, estoque, relatórios).
                Você poderá adicionar operadores de caixa depois.
              </div>

              <Input
                label="Nome completo *"
                value={dados.gerente.nome}
                onChange={(e) => setGer('nome', e.target.value)}
                placeholder="Ex: João Silva"
                autoFocus
              />

              <Input
                label="E-mail (opcional)"
                type="email"
                value={dados.gerente.email ?? ''}
                onChange={(e) => setGer('email', e.target.value)}
                placeholder="gerente@email.com"
              />

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Input
                    label="Código operador *"
                    value={dados.gerente.codigo_operador}
                    onChange={(e) => setGer('codigo_operador', e.target.value.replace(/\D/g, ''))}
                    placeholder="900"
                    maxLength={10}
                  />
                  <p className="mt-1 text-xs text-text-muted">Usado para identificar no PDV</p>
                </div>
                <div className="relative">
                  <Input
                    label="PIN *"
                    type={mostrarPin ? 'text' : 'password'}
                    value={dados.gerente.pin}
                    onChange={(e) => setGer('pin', e.target.value.replace(/\D/g, ''))}
                    placeholder="4–6 dígitos"
                    maxLength={6}
                    suffix={
                      <button
                        type="button"
                        onClick={() => setMostrarPin((v) => !v)}
                        className="text-text-muted hover:text-text-primary"
                        tabIndex={-1}
                      >
                        {mostrarPin ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                    }
                  />
                </div>
              </div>

              <Input
                label="Confirmar PIN *"
                type={mostrarPin ? 'text' : 'password'}
                value={confirmarPin}
                onChange={(e) => setConfirmarPin(e.target.value.replace(/\D/g, ''))}
                placeholder="Repita o PIN"
                maxLength={6}
                error={confirmarPin && dados.gerente.pin !== confirmarPin ? 'PINs não coincidem' : undefined}
              />

              {erro && (
                <p className="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger-text">{erro}</p>
              )}

              <div className="flex gap-3">
                <Button
                  variant="ghost"
                  className="flex-1"
                  onClick={() => setEtapa('mercado')}
                  disabled={loading}
                >
                  Voltar
                </Button>
                <Button
                  className="flex-1"
                  onClick={handleFinalizar}
                  disabled={!podeAvancarGerente || loading}
                >
                  {loading
                    ? <><Loader2 size={15} className="animate-spin" /> Criando...</>
                    : 'Concluir setup'}
                </Button>
              </div>
            </div>
          )}

          {/* â”€â”€ SUCESSO â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
          {etapa === 'sucesso' && (
            <div className="flex flex-col items-center gap-5 py-4 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-success/15 ring-2 ring-success/30">
                <CheckCircle size={36} className="text-success-text" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-text-primary">
                  {nomeFantasia} está pronto!
                </h2>
                <p className="mt-1.5 text-sm text-text-muted">
                  Empresa, gerente e caixa criados com sucesso.
                  <br />
                  Redirecionando para o login…
                </p>
              </div>
              <Loader2 size={20} className="animate-spin text-text-muted" />
            </div>
          )}
        </div>

        {/* Footer hint */}
        {etapa !== 'sucesso' && (
          <p className="mt-4 text-center text-xs text-text-muted">
            {preview
              ? 'Modo visual de QA: nenhuma empresa, usuário ou caixa será criado.'
              : 'Essas informações serão usadas na retaguarda, PDV e relatórios.'}
          </p>
        )}
      </div>
    </div>
  )
}

