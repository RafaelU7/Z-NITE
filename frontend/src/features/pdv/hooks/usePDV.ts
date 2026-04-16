import { useState, useCallback } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { usePDVStore } from '@/store/pdvStore'
import { useAuthStore } from '@/store/authStore'
import { getProdutoByEAN } from '@/services/api/produto'
import {
  iniciarVenda,
  adicionarItem,
  removerItem,
  adicionarPagamento,
  finalizarVenda as finalizarVendaAPI,
} from '@/services/api/venda'
import {
  criarVendaOffline,
  adicionarItemOffline,
  removerItemOffline,
  adicionarPagamentoOffline,
  finalizarVendaOffline,
  getVendaOfflineEmAberto,
  vendaOfflineParaDTO,
  countVendasPendentes,
} from '@/services/offline/vendaOfflineService'
import { cacheProduto, buscarProdutoOffline } from '@/services/offline/catalogoOffline'
import type { FormaPagamento, ProdutoDTO, TipoEmissao } from '@/shared/types/api'

let vendaBootstrapPromise: Promise<void> | null = null

// Hook central do PDV — orquestra todas as operações (online e offline)
export function usePDV() {
  const {
    sessaoCaixa,
    vendaAtual,
    setVendaAtual,
    setUltimoProduto,
    setFlash,
    setVendaFinalizada,
    setPainelPagamentoAberto,
    setItemSelecionadoId,
    isOffline,
    setPendentesSync,
    modoEmissaoSelecionado,
    setModoEmissaoSelecionado,
    scannerPodeFocar,
    setScannerPodeFocar,
  } = usePDVStore()

  const { user } = useAuthStore()
  const [loadingBarcode, setLoadingBarcode] = useState(false)
  const [loadingAcao, setLoadingAcao] = useState(false)

  const hasVendaAberta = useCallback(() => vendaAtual?.status === 'em_aberto', [vendaAtual])

  // ----- Helpers -----
  const flash = useCallback(
    (type: 'success' | 'error' | 'info', message: string, duration = 2500) => {
      setFlash({ type, message })
      setTimeout(() => setFlash(null), duration)
    },
    [setFlash],
  )

  // ----- Nova Venda -----
  const novaVenda = useCallback(async (options?: { silent?: boolean }) => {
    if (!sessaoCaixa) return flash('error', 'Caixa não está aberto.')
    try {
      setLoadingAcao(true)

      if (!isOffline) {
        if (options?.silent) {
          const vendaAtualStore = usePDVStore.getState().vendaAtual
          if (vendaAtualStore?.status === 'em_aberto') {
            return
          }
        }
        // Online: usa backend como de costume
        const venda = await iniciarVenda({
          sessao_caixa_id: sessaoCaixa.id,
          chave_idempotencia: uuidv4(),
          origem_pdv: `PDV-${user?.codigo_operador ?? 'WEB'}`,
        })
        setVendaAtual(venda)
        setModoEmissaoSelecionado(venda.tipo_emissao ?? 'FISCAL')
        if (!options?.silent) {
          flash('success', `Venda #${venda.numero_venda_local} iniciada.`, 1500)
        }
      } else {
        const vendaExistente = await getVendaOfflineEmAberto(sessaoCaixa.id)
        const vendaOffline = vendaExistente ?? await criarVendaOffline(
          sessaoCaixa.id,
          `PDV-${user?.codigo_operador ?? 'WEB'}`,
          sessaoCaixa.empresa_id,
          user?.id ?? '',
        )
        setVendaAtual(vendaOfflineParaDTO(vendaOffline))
        setModoEmissaoSelecionado(vendaOffline.tipo_emissao ?? 'FISCAL')
        if (!options?.silent) {
          flash(
            'info',
            vendaExistente
              ? `Venda #${vendaOffline.numero_venda_local} retomada offline.`
              : `Venda #${vendaOffline.numero_venda_local} criada offline.`,
            1800,
          )
        }
      }

      setVendaFinalizada(null)
      setPainelPagamentoAberto(false)
      setItemSelecionadoId(null)
      setScannerPodeFocar(true)
    } catch (err) {
      flash('error', err instanceof Error ? err.message : 'Erro ao iniciar venda.')
    } finally {
      setLoadingAcao(false)
    }
  }, [sessaoCaixa, user, isOffline, setVendaAtual, setVendaFinalizada, setPainelPagamentoAberto, setItemSelecionadoId, flash])

  const ensureVendaAberta = useCallback(async () => {
    if (hasVendaAberta()) return
    if (!sessaoCaixa) return

    if (!vendaBootstrapPromise) {
      vendaBootstrapPromise = (async () => {
        setVendaAtual(null)
        setVendaFinalizada(null)
        await novaVenda({ silent: true })
      })().finally(() => {
        vendaBootstrapPromise = null
      })
    }

    await vendaBootstrapPromise
  }, [hasVendaAberta, novaVenda, sessaoCaixa, setVendaAtual, setVendaFinalizada])

  // ----- Leitura de Barcode -----
  const lerBarcode = useCallback(
    async (ean: string) => {
      if (!sessaoCaixa) return flash('error', 'Caixa não está aberto.')

      setLoadingBarcode(true)
      try {
        await ensureVendaAberta()

        const vendaAtiva = usePDVStore.getState().vendaAtual
        const vendaId = vendaAtiva?.status === 'em_aberto' ? vendaAtiva.id : null
        if (!vendaId) {
          throw new Error('Não foi possível preparar uma venda ativa para o PDV.')
        }

        if (!isOffline) {
          // Online: busca no backend e faz cache local
          const produto = await getProdutoByEAN(ean)
          await cacheProduto(produto)
          setUltimoProduto(produto)

          const vendaAtualizada = await adicionarItem(vendaId, {
            produto_id: produto.id,
            quantidade: parseFloat(produto.ean_fator_quantidade),
          })
          setVendaAtual(vendaAtualizada)
          flash('success', produto.descricao_pdv ?? produto.descricao, 2000)
        } else {
          // Offline: busca no catálogo local
          const produto = await buscarProdutoOffline(ean)
          if (!produto) {
            throw new Error(
              'Produto não disponível offline. Escaneie-o quando online para disponibilizá-lo.',
            )
          }

          const fator = parseFloat(produto.ean_fator_quantidade)
          const vendaAtualizada = await adicionarItemOffline(vendaId, {
            produto_id: produto.id,
            descricao_produto: produto.descricao_pdv ?? produto.descricao,
            codigo_barras: produto.codigo_barras_principal,
            unidade: produto.unidade_codigo,
            quantidade: fator,
            preco_unitario: produto.preco_venda,
            desconto_unitario: 0,
            total_item: produto.preco_venda * fator,
            cancelado: false,
            snapshot_fiscal: null,
          })
          setVendaAtual(vendaOfflineParaDTO(vendaAtualizada))

          // Monta um ProdutoDTO sintético para o feedback visual do último produto
          const produtoDTO: ProdutoDTO = {
            id: produto.id,
            empresa_id: sessaoCaixa.empresa_id,
            sku: produto.sku,
            codigo_barras_principal: produto.codigo_barras_principal,
            descricao: produto.descricao,
            descricao_pdv: produto.descricao_pdv,
            marca: produto.marca,
            preco_venda: produto.preco_venda.toFixed(4),
            custo_medio: null,
            unidade_codigo: produto.unidade_codigo,
            controla_estoque: produto.controla_estoque,
            pesavel: false,
            perfil_tributario_id: produto.perfil_tributario_id,
            ncm: produto.ncm,
            cfop: produto.cfop,
            csosn: produto.csosn,
            cst_icms: produto.cst_icms,
            ativo: true,
            destaque_pdv: false,
            ean_pesquisado: ean,
            ean_fator_quantidade: produto.ean_fator_quantidade,
          }
          setUltimoProduto(produtoDTO)
          flash('success', produto.descricao_pdv ?? produto.descricao, 2000)
        }
      } catch (err) {
        setUltimoProduto(null)
        flash('error', err instanceof Error ? err.message : 'Produto não encontrado.')
      } finally {
        setLoadingBarcode(false)
      }
    },
    [ensureVendaAberta, flash, isOffline, sessaoCaixa, setUltimoProduto, setVendaAtual],
  )

  // ----- Remover Item -----
  const removerItemVenda = useCallback(
    async (itemId: string) => {
      if (!vendaAtual) return
      setLoadingAcao(true)
      try {
        if (!isOffline) {
          const vendaAtualizada = await removerItem(vendaAtual.id, itemId)
          setVendaAtual(vendaAtualizada)
        } else {
          const vendaAtualizada = await removerItemOffline(vendaAtual.id, itemId)
          setVendaAtual(vendaOfflineParaDTO(vendaAtualizada))
        }
        setItemSelecionadoId(null)
        flash('info', 'Item removido.', 1500)
      } catch (err) {
        flash('error', err instanceof Error ? err.message : 'Erro ao remover item.')
      } finally {
        setLoadingAcao(false)
      }
    },
    [vendaAtual, isOffline, setVendaAtual, setItemSelecionadoId, flash],
  )

  // ----- Registrar Pagamento -----
  const registrarPagamento = useCallback(
    async (forma: FormaPagamento, valor: number) => {
      if (!vendaAtual) return
      setLoadingAcao(true)
      try {
        if (!isOffline) {
          const vendaAtualizada = await adicionarPagamento(vendaAtual.id, {
            forma_pagamento: forma,
            valor,
          })
          setVendaAtual(vendaAtualizada)
        } else {
          const vendaAtualizada = await adicionarPagamentoOffline(
            vendaAtual.id,
            forma,
            valor,
          )
          setVendaAtual(vendaOfflineParaDTO(vendaAtualizada))
        }
      } catch (err) {
        flash('error', err instanceof Error ? err.message : 'Erro ao registrar pagamento.')
        throw err
      } finally {
        setScannerPodeFocar(true)
        setLoadingAcao(false)
      }
    },
    [vendaAtual, isOffline, setScannerPodeFocar, setVendaAtual, flash],
  )

  // ----- Finalizar Venda -----
  const selecionarModoEmissao = useCallback((tipoEmissao: TipoEmissao) => {
    setModoEmissaoSelecionado(tipoEmissao)
  }, [setModoEmissaoSelecionado])

  const finalizarVenda = useCallback(async (tipoEmissao?: TipoEmissao) => {
    if (!vendaAtual) return
    const modoFinal = tipoEmissao ?? modoEmissaoSelecionado
    setModoEmissaoSelecionado(modoFinal)
    setScannerPodeFocar(false)
    setLoadingAcao(true)
    try {
      if (!isOffline) {
        const vendaFinal = await finalizarVendaAPI(vendaAtual.id, modoFinal)
        setVendaAtual(null)
        setVendaFinalizada(null)
        setPainelPagamentoAberto(false)
        if (modoFinal === 'GERENCIAL') {
          flash(
            'success',
            `Pedido #${vendaFinal.numero_venda_local} concluído — documento gerencial (sem emissão fiscal)`,
            5000,
          )
        } else {
          flash('success', `Venda #${vendaFinal.numero_venda_local} finalizada com sucesso!`, 4000)
        }
        await novaVenda({ silent: true })
      } else {
        // Offline: persiste localmente com status pendente_sync
        const vendaFinal = await finalizarVendaOffline(vendaAtual.id, modoFinal)
        setPendentesSync(await countVendasPendentes())
        setVendaAtual(null)
        setVendaFinalizada(null)
        setPainelPagamentoAberto(false)
        if (modoFinal === 'GERENCIAL') {
          flash(
            'info',
            `Pedido #${vendaFinal.numero_venda_local} salvo localmente como gerencial. Será sincronizado em breve.`,
            5000,
          )
        } else {
          flash(
            'info',
            `Venda #${vendaFinal.numero_venda_local} salva localmente. Será sincronizada quando online.`,
            5000,
          )
        }
        await novaVenda({ silent: true })
      }
    } catch (err) {
      flash('error', err instanceof Error ? err.message : 'Erro ao finalizar venda.')
    } finally {
      setScannerPodeFocar(true)
      setLoadingAcao(false)
    }
  }, [flash, isOffline, modoEmissaoSelecionado, novaVenda, setModoEmissaoSelecionado, setPainelPagamentoAberto, setPendentesSync, setScannerPodeFocar, setVendaAtual, setVendaFinalizada, vendaAtual])

  return {
    ensureVendaAberta,
    isOffline,
    loadingBarcode,
    loadingAcao,
    novaVenda,
    lerBarcode,
    removerItemVenda,
    registrarPagamento,
    modoEmissaoSelecionado,
    selecionarModoEmissao,
    scannerPodeFocar,
    setScannerPodeFocar,
    finalizarVenda,
  }
}
