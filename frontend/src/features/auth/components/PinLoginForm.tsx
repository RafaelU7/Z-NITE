import { useState, useRef, useEffect } from 'react'
import { LogIn, Hash, Lock, Zap } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { useAuthStore } from '@/store/authStore'
import { pinLogin } from '@/services/api/auth'
import { getMe } from '@/services/api/auth'
import { setClientEmpresaId, setClientToken } from '@/services/api/client'

// ID da empresa — em produção viria de config/env ou seleção inicial
const EMPRESA_ID = import.meta.env.VITE_EMPRESA_ID ?? ''

export function PinLoginForm() {
  const navigate = useNavigate()
  const [codigo, setCodigo] = useState('')
  const [pin, setPin] = useState('')
  const [empresaId, setEmpresaId] = useState(EMPRESA_ID)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const codigoRef = useRef<HTMLInputElement>(null)
  const pinRef = useRef<HTMLInputElement>(null)
  const setSession = useAuthStore((s) => s.setSession)
  const clearSession = useAuthStore((s) => s.clearSession)

  useEffect(() => {
    codigoRef.current?.focus()
  }, [])

  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault()
    if (!empresaId || !codigo.trim() || !pin.trim()) {
      setError('Preencha todos os campos.')
      return
    }
    setError('')
    setLoading(true)
    try {
      const tokens = await pinLogin({
        empresa_id: empresaId,
        codigo_operador: codigo.trim(),
        pin: pin.trim(),
      })

      // Instala o token no cliente antes de chamar endpoints protegidos.
      setClientToken(tokens.access_token)
      setClientEmpresaId(empresaId)

      // Busca perfil do operador já autenticado.
      const user = await getMe()
      setSession(tokens.access_token, tokens.refresh_token, user, empresaId)
      navigate('/caixa', { replace: true })
    } catch (err) {
      clearSession()
      setError(err instanceof Error ? err.message : 'Erro ao autenticar.')
      setPin('')
      pinRef.current?.focus()
    } finally {
      setLoading(false)
    }
  }

  // Enter no código avança para PIN; Enter no PIN submete
  function handleCodigoKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && codigo.trim()) {
      e.preventDefault()
      pinRef.current?.focus()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
      {/* Campo empresa — colapsado quando vem do env */}
      {!EMPRESA_ID && (
        <Input
          label="ID da Empresa"
          placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          value={empresaId}
          onChange={(e) => setEmpresaId(e.target.value)}
          prefix={<Hash size={14} />}
          autoComplete="off"
        />
      )}

      <Input
        ref={codigoRef}
        label="Código do Operador"
        placeholder="Ex: 001"
        value={codigo}
        onChange={(e) => setCodigo(e.target.value)}
        onKeyDown={handleCodigoKeyDown}
        prefix={<Hash size={14} />}
        autoComplete="username"
        autoCorrect="off"
        spellCheck={false}
      />

      <Input
        ref={pinRef}
        label="PIN"
        type="password"
        placeholder="••••"
        value={pin}
        onChange={(e) => setPin(e.target.value)}
        prefix={<Lock size={14} />}
        autoComplete="current-password"
        inputMode="numeric"
        maxLength={6}
      />

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2.5 text-sm text-danger-text">
          <span className="shrink-0">⚠</span>
          <span>{error}</span>
        </div>
      )}

      <Button
        type="submit"
        size="lg"
        fullWidth
        loading={loading}
        className="mt-1"
      >
        <LogIn size={18} />
        Entrar no Caixa
      </Button>

      <p className="text-center text-xs text-text-muted">
        <Zap size={10} className="mr-1 inline" />
        Zênite PDV · Acesso por PIN do operador
      </p>
    </form>
  )
}
