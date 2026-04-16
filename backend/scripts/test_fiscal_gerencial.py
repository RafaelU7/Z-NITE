"""
Valida os cenários A (FISCAL), B (GERENCIAL) e C (Offline GERENCIAL sync).
Executa direto contra o servidor em localhost:8000.
"""
import asyncio
import uuid
import httpx

BASE = "http://localhost:8000"
EMPRESA_ID = "13e416c1-6b68-486c-8731-84557ea04ee3"
CAIXA_ID = "92ef21b4-73c2-4d24-900e-bf9b89c63d72"


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        # ── Auth ──────────────────────────────────────────────────────────
        r = await c.post(
            "/v1/auth/login",
            json={"empresa_id": EMPRESA_ID, "email": "admin@zenite.dev", "senha": "Admin@123"},
        )
        assert r.status_code == 200, f"login failed: {r.text}"
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        print("Login OK")

        # ── Sessão de caixa ───────────────────────────────────────────────
        r = await c.post(
            "/v1/caixa/sessoes",
            json={"caixa_id": CAIXA_ID, "saldo_abertura": 0},
            headers=h,
        )
        if r.status_code == 409:
            r2 = await c.get("/v1/caixa/sessao-ativa", params={"caixa_id": CAIXA_ID}, headers=h)
            assert r2.status_code == 200, f"sessao-ativa failed: {r2.text}"
            sessao_id = r2.json()["id"]
            print(f"Sessao existente: {sessao_id}")
        else:
            assert r.status_code == 201, f"sessao failed: {r.text}"
            sessao_id = r.json()["id"]
            print(f"Sessao criada: {sessao_id}")

        # ── Busca produto ─────────────────────────────────────────────────
        r = await c.get("/v1/produtos/ean/7891234567890", headers=h)
        assert r.status_code == 200, f"produto failed: {r.text}"
        produto = r.json()
        produto_id = produto["id"]
        print(f"Produto: {produto['descricao']} (id={produto_id})")

        # ═══════════════════════════════════════════════════════════════════
        # CENÁRIO A — Finalizar como FISCAL → deve criar DocumentoFiscal
        # ═══════════════════════════════════════════════════════════════════
        print("\n--- Cenário A: FISCAL ---")
        r = await c.post(
            "/v1/vendas/",
            json={"sessao_caixa_id": sessao_id, "chave_idempotencia": str(uuid.uuid4())},
            headers=h,
        )
        assert r.status_code == 201, f"criar venda A failed: {r.text}"
        venda_id_a = r.json()["id"]

        r = await c.post(
            f"/v1/vendas/{venda_id_a}/itens",
            json={"produto_id": produto_id, "quantidade": 1},
            headers=h,
        )
        assert r.status_code == 201, f"add item A failed: {r.text}"
        total_a = float(r.json()["total_liquido"])

        r = await c.post(
            f"/v1/vendas/{venda_id_a}/pagamentos",
            json={"forma_pagamento": "01", "valor": total_a},
            headers=h,
        )
        assert r.status_code == 201, f"pagamento A failed: {r.text}"

        r = await c.post(
            f"/v1/vendas/{venda_id_a}/finalizar",
            json={"tipo_emissao": "FISCAL"},
            headers=h,
        )
        assert r.status_code == 200, f"finalizar FISCAL failed: {r.text}"
        fa = r.json()
        print(f"  status={fa['status']}, tipo_emissao={fa['tipo_emissao']}, documento_fiscal_id={fa.get('documento_fiscal_id')}")
        assert fa["status"] == "concluida"
        assert fa["tipo_emissao"] == "FISCAL"
        assert fa.get("documento_fiscal_id") is not None, "documento_fiscal_id deveria ter sido criado"
        print("  [A] FISCAL OK: documento fiscal criado!")

        # ═══════════════════════════════════════════════════════════════════
        # CENÁRIO B — Finalizar como GERENCIAL → sem DocumentoFiscal
        # ═══════════════════════════════════════════════════════════════════
        print("\n--- Cenário B: GERENCIAL ---")
        r = await c.post(
            "/v1/vendas/",
            json={"sessao_caixa_id": sessao_id, "chave_idempotencia": str(uuid.uuid4())},
            headers=h,
        )
        assert r.status_code == 201, f"criar venda B failed: {r.text}"
        venda_id_b = r.json()["id"]

        r = await c.post(
            f"/v1/vendas/{venda_id_b}/itens",
            json={"produto_id": produto_id, "quantidade": 1},
            headers=h,
        )
        assert r.status_code == 201, f"add item B failed: {r.text}"
        total_b = float(r.json()["total_liquido"])

        r = await c.post(
            f"/v1/vendas/{venda_id_b}/pagamentos",
            json={"forma_pagamento": "17", "valor": total_b},
            headers=h,
        )
        assert r.status_code == 201

        r = await c.post(
            f"/v1/vendas/{venda_id_b}/finalizar",
            json={"tipo_emissao": "GERENCIAL"},
            headers=h,
        )
        assert r.status_code == 200, f"finalizar GERENCIAL failed: {r.text}"
        fb = r.json()
        print(f"  status={fb['status']}, tipo_emissao={fb['tipo_emissao']}, documento_fiscal_id={fb.get('documento_fiscal_id')}")
        assert fb["status"] == "concluida"
        assert fb["tipo_emissao"] == "GERENCIAL"
        assert fb.get("documento_fiscal_id") is None, "documento_fiscal_id deveria ser None para GERENCIAL"
        print("  [B] GERENCIAL OK: sem documento fiscal!")

        # ═══════════════════════════════════════════════════════════════════
        # CENÁRIO C — Sync offline com tipo_emissao GERENCIAL
        # ═══════════════════════════════════════════════════════════════════
        print("\n--- Cenário C: Sync offline GERENCIAL ---")
        chave = str(uuid.uuid4())
        payload = {
            "vendas": [
                {
                    "chave_idempotencia": chave,
                    "sessao_caixa_id": sessao_id,
                    "origem_pdv": "PDV-OFFLINE-TEST",
                    "data_venda": "2026-04-16T10:00:00",
                    "tipo_emissao": "GERENCIAL",
                    "itens": [
                        {
                            "produto_id": produto_id,
                            "descricao_produto": produto["descricao"],
                            "codigo_barras": produto["codigo_barras_principal"],
                            "unidade": produto["unidade_codigo"],
                            "sequencia": 1,
                            "quantidade": "1.000",
                            "preco_unitario": produto["preco_venda"],
                            "desconto_unitario": "0.0000",
                            "snapshot_fiscal": None,
                        }
                    ],
                    "pagamentos": [
                        {
                            "forma_pagamento": "01",
                            "valor": produto["preco_venda"],
                            "troco": "0.00",
                            "nsu": None,
                            "bandeira_cartao": None,
                        }
                    ],
                }
            ]
        }
        r = await c.post("/v1/sync/vendas", json=payload, headers=h)
        assert r.status_code == 200, f"sync failed: {r.text}"
        result = r.json()
        print(f"  aceitas={len(result['aceitas'])}, duplicadas={len(result['duplicadas'])}, rejeitadas={len(result['rejeitadas'])}")
        assert len(result["aceitas"]) == 1
        aceita = result["aceitas"][0]
        assert aceita["chave_idempotencia"] == chave
        doc_id = aceita.get("documento_fiscal_id")
        assert doc_id is None, f"GERENCIAL sync nao deveria criar documento fiscal, mas criou: {doc_id}"
        print(f"  venda_id={aceita['venda_id']}, documento_fiscal_id={doc_id}")
        print("  [C] Sync GERENCIAL OK: venda aceita, sem documento fiscal!")

        print("\n=== TODOS OS CENÁRIOS VALIDADOS COM SUCESSO ===")


if __name__ == "__main__":
    asyncio.run(main())
