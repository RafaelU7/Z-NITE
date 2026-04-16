import { useEffect, useCallback } from 'react'
import { Plus, CreditCard, ShoppingBag, LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'

import { usePDVStore } from '@/store/pdvStore'
import { useAuthStore } from '@/store/authStore'
import { useConnectivity } from '@/hooks/useConnectivity'
import { usePDV } from '../hooks/usePDV'

import { StatusBarPDV } from '../components/StatusBarPDV'
import { BarcodeInput } from '../components/BarcodeInput'
import { VendaItemList } from '../components/VendaItemList'
import { VendaResumo } from '../components/VendaResumo'
import { PagamentoPanel } from '../components/PagamentoPanel'
import { ModalRemocaoItem } from '../components/ModalRemocaoItem'
import { OfflineBanner } from '../components/OfflineBanner'
import { SyncStatusIndicator } from '../components/SyncStatusIndicator'
import { Button } from '@/shared/ui/Button'

export function PDVPage() {
  const navigate = useNavigate()
  const {
    sessaoCaixa,
    vendaAtual,
    ultimoProduto,
    itemSelecionadoId,
    painelPagamentoAberto,
    modalRemocaoAberto,
    flash,
    isOffline,
    modoEmissaoSelecionado,
    scannerPodeFocar,
    setItemSelecionadoId,
    setModoEmissaoSelecionado,
    setPainelPagamentoAberto,
    setModalRemocaoAberto,
  } = usePDVStore()

  const { clearSession } = useAuthStore()
  // Registra o detector de conectividade (uma vez por montagem da página)
  useConnectivity()
  const { loadingBarcode, loadingAcao, novaVenda, ensureVendaAberta, lerBarcode, removerItemVenda, registrarPagamento, finalizarVenda, selecionarModoEmissao, setScannerPodeFocar } =
    usePDV()

  // Redireciona se não há sessão de caixa
  useEffect(() => {
    if (!sessaoCaixa) navigate('/caixa')
  }, [sessaoCaixa, navigate])

  useEffect(() => {
    if (!sessaoCaixa) return
    if (!vendaAtual || vendaAtual.status !== 'em_aberto') {
      void ensureVendaAberta()
    }
  }, [ensureVendaAberta, sessaoCaixa, vendaAtual])

  // ----- Atalhos de teclado globais -----
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      const isEditable =
        target.isContentEditable ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT'

      if ((e.ctrlKey || e.metaKey || e.altKey) && isEditable) {
        return
      }

      // F2 → Finalizar como GERENCIAL (Pedido / Orçamento)
      if (e.key === 'F2') {
        e.preventDefault()
        setModoEmissaoSelecionado('GERENCIAL')
        if (!loadingAcao && vendaAtual) void finalizarVenda('GERENCIAL')
        return
      }
      // F4 → Finalizar como FISCAL (NFC-e)
      if (e.key === 'F4') {
        e.preventDefault()
        setModoEmissaoSelecionado('FISCAL')
        if (!loadingAcao && vendaAtual) void finalizarVenda('FISCAL')
        return
      }
      // F6 → Nova Venda manual
      if (e.key === 'F6') {
        e.preventDefault()
        if (!loadingAcao) novaVenda()
        return
      }
      // F8 → Remover item selecionado
      if (e.key === 'F8') {
        e.preventDefault()
        if (itemSelecionadoId) setModalRemocaoAberto(true)
        return
      }
      // Esc → Fechar painéis
      if (e.key === 'Escape') {
        if (modalRemocaoAberto) { setModalRemocaoAberto(false); return }
        if (painelPagamentoAberto) { setPainelPagamentoAberto(false); return }
        setItemSelecionadoId(null)
        return
      }
    },
    [
      finalizarVenda,
      novaVenda,
      loadingAcao,
      vendaAtual,
      itemSelecionadoId,
      painelPagamentoAberto,
      modalRemocaoAberto,
      setItemSelecionadoId,
      setModoEmissaoSelecionado,
      setPainelPagamentoAberto,
      setModalRemocaoAberto,
    ],
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  const itensAtivos = vendaAtual?.itens.filter((i) => !i.cancelado) ?? []
  const totalPago = vendaAtual?.pagamentos.reduce((s, p) => s + parseFloat(p.valor), 0) ?? 0
  const itemSelecionado = vendaAtual?.itens.find((i) => i.id === itemSelecionadoId) ?? null

  return (
    <div className="flex h-screen flex-col bg-bg-base overflow-hidden">
      {/* Barra de status */}
      <StatusBarPDV sessao={sessaoCaixa} venda={vendaAtual ?? null} />

      {/* Banner de modo offline */}
      {isOffline && <OfflineBanner />}

      {/* Flash notification */}
      {flash && (
        <div
          className={clsx(
            'fixed right-4 top-12 z-40 max-w-xs rounded-xl border px-4 py-3 text-sm font-medium shadow-xl',
            'animate-slide-in',
            flash.type === 'success' && 'border-success/40 bg-success/15 text-success-text',
            flash.type === 'error' && 'border-danger/40 bg-danger/15 text-danger-text',
            flash.type === 'info' && 'border-info/40 bg-info/15 text-info-text',
          )}
        >
          {flash.message}
        </div>
      )}

      {/* Área principal */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── COLUNA ESQUERDA: Barcode + Itens ── */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Barcode input */}
          <div className="border-b border-border bg-bg-surface p-4 pb-8">
            <BarcodeInput
              onScan={lerBarcode}
              loading={loadingBarcode}
              disabled={vendaAtual?.status === 'concluida'}
              autoFocusEnabled={scannerPodeFocar && !!vendaAtual && vendaAtual.status === 'em_aberto'}
              lastProduct={ultimoProduto?.produto.descricao_pdv ?? ultimoProduto?.produto.descricao}
            />
          </div>

          {/* Toolbar */}
          <div className="flex items-center gap-2 border-b border-border bg-bg-surface px-4 py-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                void novaVenda()
              }}
              loading={loadingAcao && !vendaAtual}
              kbd="F6"
            >
              <Plus size={14} />
              Nova Venda
            </Button>

            {itemSelecionadoId && (
              <Button
                variant="danger"
                size="sm"
                onClick={() => setModalRemocaoAberto(true)}
                kbd="F8"
              >
                Remover Item
              </Button>
            )}

            <div className="flex-1" />

            {/* Indicador de sync pendente */}
            <SyncStatusIndicator />

            {vendaAtual && (
              <span className="text-xs text-text-muted">
                {itensAtivos.length} {itensAtivos.length === 1 ? 'item' : 'itens'}
              </span>
            )}
          </div>

          {/* Lista de itens */}
          <div className="flex flex-1 flex-col overflow-auto">
            {vendaAtual ? (
              <VendaItemList
                itens={vendaAtual.itens}
                itemSelecionadoId={itemSelecionadoId}
                onSelectItem={setItemSelecionadoId}
                onRemoveItem={(id) => {
                  setItemSelecionadoId(id)
                  setModalRemocaoAberto(true)
                }}
              />
            ) : (
              <div className="flex flex-1 flex-col items-center justify-center gap-3 py-16 text-text-muted">
                <ShoppingBag size={48} className="opacity-20" />
                <p className="text-sm">Nenhuma venda em andamento</p>
                <p className="text-xs opacity-60">
                  Leia um produto ou pressione{' '}
                  <kbd className="rounded border border-border bg-bg-surface-2 px-1.5 py-0.5 font-mono text-xs">
                    F6
                  </kbd>{' '}
                  para iniciar
                </p>
              </div>
            )}
          </div>
        </div>

        {/* ── COLUNA DIREITA: Resumo + Pagamento ── */}
        <div className="flex w-80 shrink-0 flex-col gap-0 border-l border-border bg-bg-surface xl:w-96">
          {/* Header da coluna direita */}
          <div className="flex items-center gap-2 border-b border-border px-4 py-3">
            <CreditCard size={15} className="text-text-muted" />
            <span className="text-sm font-semibold text-text-primary">Pagamento</span>
            <div className="flex-1" />
            <button
              onClick={() => setPainelPagamentoAberto(!painelPagamentoAberto)}
              className="text-xs text-text-muted hover:text-accent transition-colors"
            >
              {painelPagamentoAberto ? 'Ocultar' : 'Mostrar'}
            </button>
          </div>

          <div className="flex flex-1 flex-col gap-4 overflow-auto p-4">
            {/* Resumo financeiro da venda */}
            {vendaAtual ? (
              <VendaResumo
                venda={vendaAtual}
                totalPago={totalPago}
                modoEmissaoSelecionado={modoEmissaoSelecionado}
              />
            ) : (
              <div className="rounded-xl border border-border/50 bg-bg-surface-2 p-4 text-center text-sm text-text-muted">
                Sem venda ativa
              </div>
            )}

            {/* Painel de pagamento */}
            {vendaAtual && (
              <PagamentoPanel
                venda={vendaAtual}
                totalPago={totalPago}
                onPagar={registrarPagamento}
                modoEmissaoSelecionado={modoEmissaoSelecionado}
                onSelecionarModoEmissao={selecionarModoEmissao}
                onFinalizarFiscal={() => finalizarVenda('FISCAL')}
                onFinalizarGerencial={() => finalizarVenda('GERENCIAL')}
                onScannerFocusChange={setScannerPodeFocar}
                loadingFinalizar={loadingAcao}
              />
            )}

            {/* Botão logout / fechar caixa */}
            <div className="mt-auto pt-2 border-t border-border/50">
              <button
                onClick={() => { clearSession(); navigate('/login') }}
                className="flex w-full items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs text-text-muted hover:bg-bg-surface-2 hover:text-text-secondary transition-colors"
              >
                <LogOut size={12} />
                Sair do sistema
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── BARRA INFERIOR: Atalhos ── */}
      <ShortcutsBar />

      {/* ── MODAL de remoção ── */}
      <ModalRemocaoItem
        open={modalRemocaoAberto}
        item={itemSelecionado}
        onConfirm={async () => {
          if (itemSelecionadoId) {
            await removerItemVenda(itemSelecionadoId)
            setModalRemocaoAberto(false)
          }
        }}
        onCancel={() => setModalRemocaoAberto(false)}
        loading={loadingAcao}
      />
    </div>
  )
}

// Barra inferior com hints de atalhos
function ShortcutsBar({ minimal = false }: { minimal?: boolean }) {
  const shortcuts = minimal
    ? [{ kbd: 'F4', label: 'Venda Fiscal' }]
    : [
        { kbd: 'F2', label: 'Pedido / Gerencial' },
        { kbd: 'F4', label: 'Venda Fiscal' },
        { kbd: 'F6', label: 'Nova Venda' },
        { kbd: 'F8', label: 'Remover Item' },
        { kbd: 'Esc', label: 'Cancelar' },
      ]

  return (
    <div className="flex items-center gap-4 border-t border-border bg-bg-surface px-4 py-1.5">
      {shortcuts.map((s) => (
        <div key={s.kbd} className="flex items-center gap-1.5 text-xs text-text-muted">
          <kbd className="rounded border border-border bg-bg-surface-2 px-1.5 py-0.5 font-mono">
            {s.kbd}
          </kbd>
          <span>{s.label}</span>
        </div>
      ))}
    </div>
  )
}
