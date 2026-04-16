import { useState, useRef, useEffect } from 'react'
import { DollarSign, Monitor } from 'lucide-react'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { abrirSessao, getSessaoAtiva } from '@/services/api/caixa'
import { usePDVStore } from '@/store/pdvStore'
import type { SessaoCaixaDTO } from '@/shared/types/api'

// Em produção, a lista de caixas viria de uma API /caixas
// Para o MVP, o operador informa o caixa_id manualmente ou vem de config
const CAIXA_ID_DEFAULT = import.meta.env.VITE_CAIXA_ID ?? ''

interface CaixaAberturaFormProps {
  onAberto: (sessao: SessaoCaixaDTO) => void
}

export function CaixaAberturaForm({ onAberto }: CaixaAberturaFormProps) {
  const [caixaId, setCaixaId] = useState(CAIXA_ID_DEFAULT)
  const [saldo, setSaldo] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const setSessaoCaixa = usePDVStore((s) => s.setSessaoCaixa)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!caixaId.trim()) { setError('Informe o ID do caixa.'); return }
    const saldoNum = parseFloat(saldo.replace(',', '.')) || 0
    setError('')
    setLoading(true)
    try {
      const sessao = await abrirSessao({ caixa_id: caixaId.trim(), saldo_abertura: saldoNum })
      setSessaoCaixa(sessao)
      onAberto(sessao)
    } catch (err) {
      if (err instanceof Error && err.message.includes('sessão aberta')) {
        try {
          const sessao = await getSessaoAtiva(caixaId.trim())
          setSessaoCaixa(sessao)
          onAberto(sessao)
          return
        } catch {
          setError('Já existe uma sessão aberta para este caixa.')
          return
        }
      }
      setError(err instanceof Error ? err.message : 'Erro ao abrir caixa.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
      {!CAIXA_ID_DEFAULT && (
        <Input
          ref={inputRef}
          label="ID do Caixa"
          placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          value={caixaId}
          onChange={(e) => setCaixaId(e.target.value)}
          prefix={<Monitor size={14} />}
          autoComplete="off"
        />
      )}

      <Input
        ref={CAIXA_ID_DEFAULT ? inputRef : undefined}
        label="Fundo de Troco (R$)"
        placeholder="0,00"
        value={saldo}
        onChange={(e) => setSaldo(e.target.value)}
        prefix={<DollarSign size={14} />}
        inputMode="decimal"
        hint="Valor em espécie disponível para troco no início do turno"
      />

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2.5 text-sm text-danger-text">
          <span>⚠</span>
          <span>{error}</span>
        </div>
      )}

      <Button type="submit" size="lg" fullWidth loading={loading} variant="success">
        <Monitor size={18} />
        Abrir Caixa
      </Button>
    </form>
  )
}
