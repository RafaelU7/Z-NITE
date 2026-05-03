import { useCallback, useEffect, useRef, useState } from 'react'
import { Barcode, CheckCircle, AlertTriangle, Loader2, RefreshCw, PackagePlus } from 'lucide-react'
import { lookupEAN, cadastroRapidoProduto, patchProduto, ajusteEstoque, listUnidades, listPerfisTributarios } from '@/services/api/gerencial'
import type {
  EANLookupResult,
  ProdutoGerencialDTO,
  UnidadeDTO,
  PerfilTributarioSimpleDTO,
  CadastroRapidoRequest,
} from '@/shared/types/api'
import { Button } from '@/shared/ui/Button'
import { formatCurrency } from '@/shared/utils/format'

type Feedback =
  | { type: 'success'; msg: string }
  | { type: 'warning'; msg: string }
  | { type: 'error'; msg: string }
  | null

type Modo = 'idle' | 'produto_existente' | 'produto_novo'

interface FormState {
  descricao: string
  descricao_pdv: string
  marca: string
  preco_venda: string
  preco_custo: string
  estoque_inicial: string
  unidade_id: string
  perfil_tributario_id: string
}

const FORM_VAZIO: FormState = {
  descricao: '',
  descricao_pdv: '',
  marca: '',
  preco_venda: '',
  preco_custo: '',
  estoque_inicial: '0',
  unidade_id: '',
  perfil_tributario_id: '',
}

export function CadastroRapidoPage() {
  const [ean, setEan] = useState('')
  const [buscando, setBuscando] = useState(false)
  const [modo, setModo] = useState<Modo>('idle')
  const [feedback, setFeedback] = useState<Feedback>(null)
  const [produtoExistente, setProdutoExistente] = useState<ProdutoGerencialDTO | null>(null)
  const [saldoAtual, setSaldoAtual] = useState<number | null>(null)
  const [form, setForm] = useState<FormState>(FORM_VAZIO)
  const [salvando, setSalvando] = useState(false)
  const [erros, setErros] = useState<Partial<Record<keyof FormState, string>>>({})
  const [unidades, setUnidades] = useState<UnidadeDTO[]>([])
  const [perfis, setPerfis] = useState<PerfilTributarioSimpleDTO[]>([])

  const eanRef = useRef<HTMLInputElement>(null)
  const nomeRef = useRef<HTMLInputElement>(null)
  const precoRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    listUnidades().then(setUnidades).catch(() => {})
    listPerfisTributarios().then(setPerfis).catch(() => {})
  }, [])

  const focarEAN = useCallback(() => {
    setTimeout(() => eanRef.current?.focus(), 80)
  }, [])

  useEffect(() => {
    focarEAN()
  }, [focarEAN])

  function resetarFormulario() {
    setEan('')
    setModo('idle')
    setForm(FORM_VAZIO)
    setErros({})
    setProdutoExistente(null)
    setSaldoAtual(null)
    setFeedback(null)
    focarEAN()
  }

  function preencherFormComSugestao(sugestao: EANLookupResult['sugestao']) {
    if (!sugestao) return
    setForm((prev) => ({
      ...prev,
      descricao: sugestao.nome || prev.descricao,
      descricao_pdv: (sugestao.nome || '').slice(0, 60),
      marca: sugestao.marca || prev.marca,
    }))
  }

  async function handleBuscarEAN(e: React.FormEvent) {
    e.preventDefault()
    const eanTrim = ean.trim()
    if (!eanTrim) return

    setBuscando(true)
    setFeedback(null)
    setModo('idle')
    setProdutoExistente(null)
    setSaldoAtual(null)

    try {
      const result = await lookupEAN(eanTrim)

      if (result.status === 'found_local') {
        setProdutoExistente(result.produto)
        setSaldoAtual(result.saldo_atual ?? 0)
        setForm({
          descricao: result.produto?.descricao ?? '',
          descricao_pdv: result.produto?.descricao_pdv ?? '',
          marca: '',
          preco_venda: result.produto?.preco_venda.toString() ?? '',
          preco_custo: '',
          estoque_inicial: '0',
          unidade_id: result.produto?.unidade_id ?? '',
          perfil_tributario_id: result.produto?.perfil_tributario_id ?? '',
        })
        setModo('produto_existente')
        setFeedback({
          type: 'warning',
          msg: `Produto já cadastrado — "${result.produto?.descricao}". Você pode editar preço ou ajustar estoque.`,
        })
        setTimeout(() => precoRef.current?.focus(), 100)
      } else if (result.status === 'found_external') {
        preencherFormComSugestao(result.sugestao)
        setModo('produto_novo')
        setFeedback({
          type: 'success',
          msg: `Produto encontrado via base externa. Confirme os dados e salve.`,
        })
        setTimeout(() => precoRef.current?.focus(), 100)
      } else {
        setForm(FORM_VAZIO)
        setModo('produto_novo')
        setFeedback({
          type: 'warning',
          msg: 'Produto não encontrado. Preencha os dados manualmente.',
        })
        setTimeout(() => nomeRef.current?.focus(), 100)
      }
    } catch {
      setFeedback({ type: 'error', msg: 'Erro ao consultar EAN. Verifique a conexão.' })
    } finally {
      setBuscando(false)
    }
  }

  function field(key: keyof FormState, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }))
    setErros((prev) => ({ ...prev, [key]: undefined }))
  }

  function validar(): boolean {
    const novosErros: typeof erros = {}
    if (!form.descricao.trim()) novosErros.descricao = 'Nome obrigatório'
    if (!form.preco_venda || parseFloat(form.preco_venda) <= 0)
      novosErros.preco_venda = 'Preço de venda obrigatório e maior que zero'
    if (form.preco_custo && parseFloat(form.preco_custo) < 0)
      novosErros.preco_custo = 'Preço de custo não pode ser negativo'
    if (parseFloat(form.estoque_inicial || '0') < 0)
      novosErros.estoque_inicial = 'Estoque não pode ser negativo'
    setErros(novosErros)
    return Object.keys(novosErros).length === 0
  }

  async function handleSalvarNovo(e: React.FormEvent) {
    e.preventDefault()
    if (!validar()) return

    setSalvando(true)
    setFeedback(null)
    try {
      const req: CadastroRapidoRequest = {
        ean: ean.trim() || undefined,
        descricao: form.descricao.trim(),
        descricao_pdv: form.descricao_pdv.trim() || undefined,
        marca: form.marca.trim() || undefined,
        preco_venda: parseFloat(form.preco_venda),
        preco_custo: form.preco_custo ? parseFloat(form.preco_custo) : undefined,
        estoque_inicial: parseFloat(form.estoque_inicial || '0'),
        unidade_id: form.unidade_id || undefined,
        perfil_tributario_id: form.perfil_tributario_id || undefined,
      }
      const resp = await cadastroRapidoProduto(req)
      const msg = resp.aviso
        ? `Produto salvo (inativo — ${resp.aviso}) — bipe o próximo!`
        : `Produto salvo com sucesso! Saldo: ${resp.saldo_atual} UN — bipe o próximo!`
      setFeedback({ type: 'success', msg })
      resetarFormulario()
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (detail?.includes('EAN já cadastrado')) {
        setFeedback({ type: 'error', msg: 'Este EAN já está cadastrado nesta empresa.' })
      } else {
        setFeedback({ type: 'error', msg: detail || 'Erro ao salvar produto.' })
      }
    } finally {
      setSalvando(false)
    }
  }

  async function handleSalvarExistente(e: React.FormEvent) {
    e.preventDefault()
    if (!produtoExistente || !validar()) return

    setSalvando(true)
    setFeedback(null)
    try {
      const novoPreco = parseFloat(form.preco_venda)
      const ajuste = parseFloat(form.estoque_inicial || '0')

      await patchProduto(produtoExistente.id, { preco_venda: novoPreco })

      let novoSaldo = saldoAtual ?? 0
      if (ajuste !== 0) {
        const resp = await ajusteEstoque(produtoExistente.id, {
          quantidade: ajuste,
          motivo: 'Ajuste manual via Cadastro Rápido',
        })
        novoSaldo = resp.saldo_atual
      }

      setFeedback({
        type: 'success',
        msg: `Produto atualizado! Preço: ${formatCurrency(novoPreco)} | Saldo: ${novoSaldo} UN — bipe o próximo!`,
      })
      resetarFormulario()
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setFeedback({ type: 'error', msg: detail || 'Erro ao atualizar produto.' })
    } finally {
      setSalvando(false)
    }
  }

  const handleSalvar = modo === 'produto_existente' ? handleSalvarExistente : handleSalvarNovo

  return (
    <div className="mx-auto max-w-xl">
      <div className="mb-5 flex items-center gap-2.5">
        <PackagePlus size={20} className="text-accent" />
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Cadastro Rápido</h1>
          <p className="text-xs text-text-muted">Bipe o EAN ou digite o código e pressione Enter</p>
        </div>
      </div>

      {/* EAN input */}
      <form onSubmit={handleBuscarEAN} className="mb-4 flex gap-2">
        <div className="relative flex-1">
          <Barcode
            size={16}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
          />
          <input
            ref={eanRef}
            type="text"
            value={ean}
            onChange={(e) => setEan(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                void handleBuscarEAN(e as unknown as React.FormEvent)
              }
            }}
            placeholder="EAN / código de barras"
            className="w-full rounded-lg border border-border bg-bg-surface pl-9 pr-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none"
            autoComplete="off"
            disabled={buscando || salvando}
          />
        </div>
        <Button type="submit" disabled={buscando || !ean.trim()} size="sm">
          {buscando ? <Loader2 size={14} className="animate-spin" /> : 'Buscar'}
        </Button>
        {modo !== 'idle' && (
          <Button type="button" variant="ghost" size="sm" onClick={resetarFormulario}>
            <RefreshCw size={14} />
          </Button>
        )}
      </form>

      {/* Feedback banner */}
      {feedback && (
        <div
          className={`mb-4 flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm ${
            feedback.type === 'success'
              ? 'border-green-500/30 bg-green-500/10 text-green-400'
              : feedback.type === 'warning'
                ? 'border-yellow-500/30 bg-yellow-500/10 text-yellow-400'
                : 'border-red-500/30 bg-red-500/10 text-red-400'
          }`}
        >
          {feedback.type === 'success' ? (
            <CheckCircle size={15} className="mt-0.5 shrink-0" />
          ) : (
            <AlertTriangle size={15} className="mt-0.5 shrink-0" />
          )}
          <span>{feedback.msg}</span>
        </div>
      )}

      {/* Formulário (novo ou existente) */}
      {modo !== 'idle' && (
        <form onSubmit={handleSalvar} className="space-y-3 rounded-xl border border-border bg-bg-surface p-4">
          {/* Saldo atual (produto existente) */}
          {modo === 'produto_existente' && saldoAtual !== null && (
            <div className="rounded-lg bg-bg-surface-2 px-3 py-2 text-xs text-text-muted">
              Saldo atual no estoque principal:{' '}
              <span className="font-semibold text-text-primary">{saldoAtual} UN</span>
            </div>
          )}

          {/* Nome */}
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">
              Nome do produto *
            </label>
            <input
              ref={nomeRef}
              type="text"
              value={form.descricao}
              onChange={(e) => field('descricao', e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && e.preventDefault()}
              disabled={salvando}
              placeholder="Ex: Refrigerante Cola 2L"
              className="w-full rounded-lg border border-border bg-bg-base px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none disabled:opacity-50"
            />
            {erros.descricao && <p className="mt-1 text-xs text-red-400">{erros.descricao}</p>}
          </div>

          {/* Nome PDV */}
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">
              Nome PDV (até 60 chars)
            </label>
            <input
              type="text"
              value={form.descricao_pdv}
              onChange={(e) => field('descricao_pdv', e.target.value.slice(0, 60))}
              onKeyDown={(e) => e.key === 'Enter' && e.preventDefault()}
              disabled={salvando}
              placeholder="Nome curto exibido no PDV"
              className="w-full rounded-lg border border-border bg-bg-base px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none disabled:opacity-50"
            />
          </div>

          {/* Marca */}
          {modo === 'produto_novo' && (
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Marca</label>
              <input
                type="text"
                value={form.marca}
                onChange={(e) => field('marca', e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && e.preventDefault()}
                disabled={salvando}
                placeholder="Ex: Coca-Cola"
                className="w-full rounded-lg border border-border bg-bg-base px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none disabled:opacity-50"
              />
            </div>
          )}

          {/* Preço venda + custo */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">
                Preço de venda (R$) *
              </label>
              <input
                ref={precoRef}
                type="number"
                step="0.01"
                min="0.01"
                value={form.preco_venda}
                onChange={(e) => field('preco_venda', e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && e.preventDefault()}
                disabled={salvando}
                placeholder="0,00"
                className="w-full rounded-lg border border-border bg-bg-base px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none disabled:opacity-50"
              />
              {erros.preco_venda && (
                <p className="mt-1 text-xs text-red-400">{erros.preco_venda}</p>
              )}
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">
                Preço de custo (R$)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={form.preco_custo}
                onChange={(e) => field('preco_custo', e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && e.preventDefault()}
                disabled={salvando}
                placeholder="0,00"
                className="w-full rounded-lg border border-border bg-bg-base px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none disabled:opacity-50"
              />
              {erros.preco_custo && (
                <p className="mt-1 text-xs text-red-400">{erros.preco_custo}</p>
              )}
            </div>
          </div>

          {/* Estoque */}
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">
              {modo === 'produto_existente'
                ? 'Ajuste de estoque (+/−)'
                : 'Estoque inicial'}
            </label>
            <input
              type="number"
              step="1"
              min={modo === 'produto_existente' ? undefined : '0'}
              value={form.estoque_inicial}
              onChange={(e) => field('estoque_inicial', e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && e.preventDefault()}
              disabled={salvando}
              placeholder="0"
              className="w-full rounded-lg border border-border bg-bg-base px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none disabled:opacity-50"
            />
            {erros.estoque_inicial && (
              <p className="mt-1 text-xs text-red-400">{erros.estoque_inicial}</p>
            )}
            {modo === 'produto_existente' && (
              <p className="mt-1 text-xs text-text-muted">
                Use valores positivos para entrada, negativos para saída
              </p>
            )}
          </div>

          {/* Unidade + Perfil tributário (só para produto novo) */}
          {modo === 'produto_novo' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-text-secondary">
                  Unidade
                </label>
                <select
                  value={form.unidade_id}
                  onChange={(e) => field('unidade_id', e.target.value)}
                  disabled={salvando}
                  className="w-full rounded-lg border border-border bg-bg-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none disabled:opacity-50"
                >
                  <option value="">Automático (UN)</option>
                  {unidades.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.codigo} — {u.descricao}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-text-secondary">
                  Perfil tributário
                </label>
                <select
                  value={form.perfil_tributario_id}
                  onChange={(e) => field('perfil_tributario_id', e.target.value)}
                  disabled={salvando}
                  className="w-full rounded-lg border border-border bg-bg-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none disabled:opacity-50"
                >
                  <option value="">Automático</option>
                  {perfis.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nome}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Botões */}
          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              onClick={resetarFormulario}
              disabled={salvando}
              className="text-xs text-text-muted hover:text-text-secondary transition-colors disabled:opacity-40"
            >
              Cancelar
            </button>
            <Button type="submit" disabled={salvando}>
              {salvando ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Salvando…
                </>
              ) : modo === 'produto_existente' ? (
                'Atualizar produto'
              ) : (
                'Salvar produto'
              )}
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}
