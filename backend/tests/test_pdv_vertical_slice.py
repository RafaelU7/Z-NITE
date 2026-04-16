from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.caixa import SessaoCaixa
from app.infrastructure.database.models.enums import FormaPagamento, StatusDocumentoFiscal, StatusSessaoCaixa, StatusVenda
from app.infrastructure.database.models.estoque import Estoque, MovimentacaoEstoque
from app.infrastructure.database.models.fiscal import DocumentoFiscal
from app.infrastructure.database.models.venda import ItemVenda, PagamentoVenda, Venda


pytestmark = pytest.mark.asyncio


async def _login_email(client: AsyncClient, seed_data: dict[str, Any]) -> str:
    response = await client.post(
        "/v1/auth/login",
        json={
            "empresa_id": str(seed_data["empresa_id"]),
            "email": seed_data["operador"]["email"],
            "senha": seed_data["operador"]["senha"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def _login_pin(client: AsyncClient, seed_data: dict[str, Any]) -> str:
    response = await client.post(
        "/v1/auth/pin-login",
        json={
            "empresa_id": str(seed_data["empresa_id"]),
            "codigo_operador": seed_data["operador"]["codigo_operador"],
            "pin": seed_data["operador"]["pin"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _abrir_sessao(
    client: AsyncClient,
    seed_data: dict[str, Any],
    token: str,
    saldo_abertura: str = "20.00",
) -> dict[str, Any]:
    response = await client.post(
        "/v1/caixa/sessoes",
        headers=_auth_headers(token),
        json={
            "caixa_id": str(seed_data["caixa_id"]),
            "saldo_abertura": saldo_abertura,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _iniciar_venda(
    client: AsyncClient,
    token: str,
    sessao_id: str,
    chave_idempotencia: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"sessao_caixa_id": sessao_id}
    if chave_idempotencia:
        payload["chave_idempotencia"] = chave_idempotencia
    response = await client.post("/v1/vendas/", headers=_auth_headers(token), json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _adicionar_item(
    client: AsyncClient,
    token: str,
    venda_id: str,
    produto_id: str,
    quantidade: str = "2.000",
    preco_unitario: str | None = None,
) -> Any:
    payload: dict[str, Any] = {
        "produto_id": produto_id,
        "quantidade": quantidade,
        "desconto_unitario": "0",
    }
    if preco_unitario is not None:
        payload["preco_unitario"] = preco_unitario
    return await client.post(
        f"/v1/vendas/{venda_id}/itens",
        headers=_auth_headers(token),
        json=payload,
    )


async def _adicionar_pagamento(
    client: AsyncClient,
    token: str,
    venda_id: str,
    forma_pagamento: str,
    valor: str,
    troco: str = "0",
) -> Any:
    return await client.post(
        f"/v1/vendas/{venda_id}/pagamentos",
        headers=_auth_headers(token),
        json={
            "forma_pagamento": forma_pagamento,
            "valor": valor,
            "troco": troco,
        },
    )


async def test_login_por_email(client: AsyncClient, seed_data: dict[str, Any]) -> None:
    response = await client.post(
        "/v1/auth/login",
        json={
            "empresa_id": str(seed_data["empresa_id"]),
            "email": seed_data["gerente"]["email"],
            "senha": seed_data["gerente"]["senha"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_por_pin(client: AsyncClient, seed_data: dict[str, Any]) -> None:
    response = await client.post(
        "/v1/auth/pin-login",
        json={
            "empresa_id": str(seed_data["empresa_id"]),
            "codigo_operador": seed_data["operador"]["codigo_operador"],
            "pin": seed_data["operador"]["pin"],
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_abrir_caixa_e_impedir_duas_sessoes_no_mesmo_caixa(
    client: AsyncClient,
    seed_data: dict[str, Any],
) -> None:
    token = await _login_email(client, seed_data)

    primeira = await _abrir_sessao(client, seed_data, token, saldo_abertura="20.00")
    segunda = await client.post(
        "/v1/caixa/sessoes",
        headers=_auth_headers(token),
        json={
            "caixa_id": str(seed_data["caixa_id"]),
            "saldo_abertura": "10.00",
        },
    )

    assert primeira["status"] == StatusSessaoCaixa.ABERTA.value
    assert segunda.status_code == 409


async def test_buscar_produto_por_ean(client: AsyncClient, seed_data: dict[str, Any]) -> None:
    token = await _login_email(client, seed_data)

    response = await client.get(
        f"/v1/produtos/ean/{seed_data['produto_ean']}",
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(seed_data["produto_id"])
    assert body["codigo_barras_principal"] == seed_data["produto_ean"]


async def test_iniciar_venda_com_idempotencia(
    client: AsyncClient,
    seed_data: dict[str, Any],
    db_session: AsyncSession,
) -> None:
    token = await _login_pin(client, seed_data)
    sessao = await _abrir_sessao(client, seed_data, token)
    chave_idempotencia = str(uuid.uuid4())

    venda_1 = await _iniciar_venda(client, token, sessao["id"], chave_idempotencia)
    venda_2 = await _iniciar_venda(client, token, sessao["id"], chave_idempotencia)

    assert venda_1["id"] == venda_2["id"]
    count = await db_session.scalar(select(func.count(Venda.id)))
    assert count == 1


async def test_adicionar_item_e_remover_item_recompem_estoque(
    client: AsyncClient,
    seed_data: dict[str, Any],
    db_session: AsyncSession,
) -> None:
    token = await _login_pin(client, seed_data)
    sessao = await _abrir_sessao(client, seed_data, token)
    venda = await _iniciar_venda(client, token, sessao["id"])

    add_response = await _adicionar_item(
        client,
        token,
        venda["id"],
        str(seed_data["produto_id"]),
        quantidade="2.000",
    )
    assert add_response.status_code == 201
    body = add_response.json()
    assert body["total_liquido"] == "20.0000"
    assert len(body["itens"]) == 1

    estoque_apos_add = await db_session.get(
        Estoque,
        (seed_data["produto_id"], seed_data["local_estoque_id"]),
    )
    assert estoque_apos_add is not None
    assert Decimal(str(estoque_apos_add.saldo_atual)) == Decimal("8.000")

    item_id = body["itens"][0]["id"]
    remove_response = await client.delete(
        f"/v1/vendas/{venda['id']}/itens/{item_id}",
        headers=_auth_headers(token),
    )

    assert remove_response.status_code == 200
    remove_body = remove_response.json()
    assert remove_body["total_liquido"] == "0.0000"
    assert remove_body["itens"][0]["cancelado"] is True

    estoque_final = await db_session.get(
        Estoque,
        (seed_data["produto_id"], seed_data["local_estoque_id"]),
    )
    assert estoque_final is not None
    assert Decimal(str(estoque_final.saldo_atual)) == Decimal("10.000")


async def test_registrar_pagamento_e_impedir_finalizacao_com_pagamento_insuficiente(
    client: AsyncClient,
    seed_data: dict[str, Any],
) -> None:
    token = await _login_pin(client, seed_data)
    sessao = await _abrir_sessao(client, seed_data, token)
    venda = await _iniciar_venda(client, token, sessao["id"])

    add_item = await _adicionar_item(client, token, venda["id"], str(seed_data["produto_id"]), quantidade="2.000")
    assert add_item.status_code == 201

    pagamento = await _adicionar_pagamento(
        client,
        token,
        venda["id"],
        FormaPagamento.DINHEIRO.value,
        "10.00",
    )
    assert pagamento.status_code == 201

    finalize = await client.post(
        f"/v1/vendas/{venda['id']}/finalizar",
        headers=_auth_headers(token),
    )
    assert finalize.status_code == 422


async def test_fluxo_completo_finaliza_cria_documento_e_fecha_caixa_com_totais_corretos(
    client: AsyncClient,
    seed_data: dict[str, Any],
    db_session: AsyncSession,
) -> None:
    token = await _login_pin(client, seed_data)
    sessao = await _abrir_sessao(client, seed_data, token, saldo_abertura="20.00")

    produto_response = await client.get(
        f"/v1/produtos/ean/{seed_data['produto_ean']}",
        headers=_auth_headers(token),
    )
    assert produto_response.status_code == 200

    venda = await _iniciar_venda(client, token, sessao["id"], str(uuid.uuid4()))
    add_item = await _adicionar_item(client, token, venda["id"], str(seed_data["produto_id"]), quantidade="1.000")
    assert add_item.status_code == 201

    pagamento_dinheiro = await _adicionar_pagamento(
        client,
        token,
        venda["id"],
        FormaPagamento.DINHEIRO.value,
        "7.00",
    )
    pagamento_pix = await _adicionar_pagamento(
        client,
        token,
        venda["id"],
        FormaPagamento.PIX.value,
        "3.00",
    )
    assert pagamento_dinheiro.status_code == 201
    assert pagamento_pix.status_code == 201

    finalize = await client.post(
        f"/v1/vendas/{venda['id']}/finalizar",
        headers=_auth_headers(token),
    )
    assert finalize.status_code == 200
    assert finalize.json()["status"] == StatusVenda.CONCLUIDA.value

    estoque = await db_session.get(Estoque, (seed_data["produto_id"], seed_data["local_estoque_id"]))
    assert estoque is not None
    assert Decimal(str(estoque.saldo_atual)) == Decimal("9.000")

    documentos = (
        await db_session.execute(select(DocumentoFiscal).where(DocumentoFiscal.venda_id == uuid.UUID(venda["id"])))
    ).scalars().all()
    assert len(documentos) == 1
    assert documentos[0].status == StatusDocumentoFiscal.PENDENTE.value

    fechamento = await client.post(
        f"/v1/caixa/sessoes/{sessao['id']}/fechar",
        headers=_auth_headers(token),
        json={
            "saldo_informado_fechamento": "27.00",
            "observacao": "Fechamento de teste",
        },
    )
    assert fechamento.status_code == 200
    fechamento_body = fechamento.json()
    assert fechamento_body["status"] == StatusSessaoCaixa.FECHADA.value
    assert fechamento_body["total_vendas_bruto"] == "10.0000"
    assert fechamento_body["total_liquido"] == "10.0000"
    assert fechamento_body["total_dinheiro"] == "7.0000"
    assert fechamento_body["total_pix"] == "3.0000"
    assert fechamento_body["saldo_sistema_fechamento"] == "27.0000"
    assert fechamento_body["diferenca_fechamento"] == "0.0000"

    vendas_count = await db_session.scalar(select(func.count(Venda.id)))
    itens_count = await db_session.scalar(select(func.count(ItemVenda.id)))
    pagamentos_count = await db_session.scalar(select(func.count(PagamentoVenda.id)))
    movimentos_count = await db_session.scalar(select(func.count(MovimentacaoEstoque.id)))
    docs_count = await db_session.scalar(select(func.count(DocumentoFiscal.id)))
    sessoes_count = await db_session.scalar(select(func.count(SessaoCaixa.id)))

    assert vendas_count == 1
    assert itens_count == 1
    assert pagamentos_count == 2
    assert movimentos_count == 1
    assert docs_count == 1
    assert sessoes_count == 1


async def test_impede_alterar_venda_concluida(
    client: AsyncClient,
    seed_data: dict[str, Any],
) -> None:
    token = await _login_pin(client, seed_data)
    sessao = await _abrir_sessao(client, seed_data, token)
    venda = await _iniciar_venda(client, token, sessao["id"])

    add_item = await _adicionar_item(client, token, venda["id"], str(seed_data["produto_id"]), quantidade="1.000")
    assert add_item.status_code == 201
    item_id = add_item.json()["itens"][0]["id"]

    pagamento = await _adicionar_pagamento(client, token, venda["id"], FormaPagamento.DINHEIRO.value, "10.00")
    assert pagamento.status_code == 201
    finalize = await client.post(f"/v1/vendas/{venda['id']}/finalizar", headers=_auth_headers(token))
    assert finalize.status_code == 200

    novo_item = await _adicionar_item(client, token, venda["id"], str(seed_data["produto_id"]), quantidade="1.000")
    novo_pagamento = await _adicionar_pagamento(client, token, venda["id"], FormaPagamento.PIX.value, "1.00")
    remover_item = await client.delete(
        f"/v1/vendas/{venda['id']}/itens/{item_id}",
        headers=_auth_headers(token),
    )

    assert novo_item.status_code == 422
    assert novo_pagamento.status_code == 422
    assert remover_item.status_code == 422


async def test_bordas_produto_inativo_e_sem_tributacao_valida(
    client: AsyncClient,
    seed_data: dict[str, Any],
) -> None:
    token = await _login_pin(client, seed_data)
    sessao = await _abrir_sessao(client, seed_data, token)
    venda = await _iniciar_venda(client, token, sessao["id"])

    produto_inativo = await client.get(
        f"/v1/produtos/ean/{seed_data['produto_inativo_ean']}",
        headers=_auth_headers(token),
    )
    assert produto_inativo.status_code == 404

    sem_fiscal = await _adicionar_item(
        client,
        token,
        venda["id"],
        str(seed_data["produto_sem_fiscal_valido_id"]),
        quantidade="1.000",
    )
    assert sem_fiscal.status_code == 422


async def test_bordas_estoque_insuficiente_venda_item_e_sessao_inexistentes(
    client: AsyncClient,
    seed_data: dict[str, Any],
) -> None:
    token = await _login_pin(client, seed_data)
    sessao = await _abrir_sessao(client, seed_data, token)
    venda = await _iniciar_venda(client, token, sessao["id"])

    estoque_insuficiente = await _adicionar_item(
        client,
        token,
        venda["id"],
        str(seed_data["produto_id"]),
        quantidade="999.000",
    )
    venda_inexistente = await client.get(
        f"/v1/vendas/{uuid.uuid4()}",
        headers=_auth_headers(token),
    )
    item_inexistente = await client.delete(
        f"/v1/vendas/{venda['id']}/itens/{uuid.uuid4()}",
        headers=_auth_headers(token),
    )
    sessao_inexistente = await client.post(
        "/v1/vendas/",
        headers=_auth_headers(token),
        json={"sessao_caixa_id": str(uuid.uuid4())},
    )

    assert estoque_insuficiente.status_code == 422
    assert venda_inexistente.status_code == 404
    assert item_inexistente.status_code == 404
    assert sessao_inexistente.status_code == 404


async def test_token_invalido_retorna_401(client: AsyncClient, seed_data: dict[str, Any]) -> None:
    response = await client.get(
        f"/v1/produtos/ean/{seed_data['produto_ean']}",
        headers={"Authorization": "Bearer token-invalido"},
    )

    assert response.status_code == 401