"""
QA Completo â€” ZÃŠNITE PDV Staging
Roda contra Railway API e reporta achados por categoria.
"""
from __future__ import annotations
import json, sys, time
import urllib.request, urllib.error
from typing import Any

BASE = "https://zenite-pdv-api-production.up.railway.app/v1"
EMPRESA_ID = "ccec5ae6-385e-4f26-8bd9-830b8ce5c3ab"
CAIXA_ID   = "6d7b005d-0a40-4267-aac8-8c51635f9918"
PRODUTO_EAN = "7891234567890"
PRODUTO_ID  = "7251fac0-7bff-41df-805b-6c737ff63c4b"

MGR_EMAIL  = "admin@zenite.dev"
MGR_PASS   = "Admin@123"
MGR_CODE   = "900"
MGR_PIN    = "9999"
OP_CODE    = "001"
OP_PIN     = "1234"

# â”€ State variables (all pre-initialized to avoid NameErrors) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
mgr_token: str | None = None
mgr_refresh: str | None = None
op_token: str | None = None
op_refresh: str | None = None
mgr_pin_token: str | None = None
sessao_id: str | None = None
venda_id: str | None = None
venda_fiscal_id: str | None = None

_PASS = "\033[92mâœ“\033[0m"
_FAIL = "\033[91mâœ—\033[0m"
_WARN = "\033[93m!\033[0m"

results: list[dict] = []

# â”€â”€â”€ HTTP helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _req(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict | str]:
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            status = resp.status
            try:
                return status, json.loads(raw)
            except Exception:
                return status, raw.decode(errors="replace")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode(errors="replace")
    except Exception as exc:
        return 0, str(exc)


def check(name: str, status: int, body: Any, expected: list[int], tag: str,
          note: str = "", severity: str = ""):
    ok = status in expected
    icon = _PASS if ok else _FAIL
    msg = f"{icon} [{tag}] {name} â†’ HTTP {status}"
    if note:
        msg += f" | {note}"
    print(msg)
    results.append({
        "ok": ok, "tag": tag, "name": name,
        "status": status, "expected": expected,
        "body": body, "severity": severity, "note": note,
    })
    return ok, body


# â”€â”€â”€ 1. AUTH â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\nâ•â•â• 1. AUTENTICAÃ‡ÃƒO â•â•â•")

# 1a. Login gerente via email+senha  (empresa_id OBRIGATÃ“RIO no body)
s, b = _req("POST", "/auth/login", {"empresa_id": EMPRESA_ID, "email": MGR_EMAIL, "senha": MGR_PASS})
ok, _ = check("Login gerente (email+senha)", s, b, [200], "AUTH", severity="CRÃTICO")
mgr_token = b.get("access_token") if ok else None
mgr_refresh = b.get("refresh_token") if ok else None

# 1b. Login operador via PIN
s, b = _req("POST", "/auth/pin-login", {"empresa_id": EMPRESA_ID, "codigo_operador": OP_CODE, "pin": OP_PIN})
ok, _ = check("Login operador (PIN)", s, b, [200], "AUTH", severity="CRÃTICO")
op_token = b.get("access_token") if ok else None
op_refresh = b.get("refresh_token") if ok else None

# 1c. Login gerente via PIN
s, b = _req("POST", "/auth/pin-login", {"empresa_id": EMPRESA_ID, "codigo_operador": MGR_CODE, "pin": MGR_PIN})
ok, _ = check("Login gerente (PIN)", s, b, [200], "AUTH", severity="MÃ‰DIO")
mgr_pin_token = b.get("access_token") if ok else None

# 1d. /me com token gerente
if mgr_token:
    s, b = _req("GET", "/auth/me", token=mgr_token)
    perfil_mgr = b.get("perfil") if isinstance(b, dict) else ""
    check("GET /me gerente", s, b, [200], "AUTH",
          note=f"perfil={perfil_mgr}", severity="CRÃTICO")
    # Enum values are lowercase: "gerente", "admin", "super_admin"
    check("Gerente tem perfil >= gerente", 200 if perfil_mgr in ("gerente","admin","super_admin") else 422, {},
          [200], "AUTH", note=f"perfil={perfil_mgr}", severity="CRÃTICO")

# 1e. /me com token operador
if op_token:
    s, b = _req("GET", "/auth/me", token=op_token)
    perfil_op = b.get("perfil") if isinstance(b, dict) else ""
    check("GET /me operador", s, b, [200], "AUTH",
          note=f"perfil={perfil_op}", severity="CRÃTICO")
    check("Operador tem perfil operador_caixa", 200 if perfil_op == "operador_caixa" else 422, {},
          [200], "AUTH", note=f"perfil={perfil_op}", severity="MÃ‰DIO")

# 1f. /me sem token â†’ 403/401
s, b = _req("GET", "/auth/me")
check("/me sem token â†’ 401/403", s, b, [401, 403], "AUTH", severity="CRÃTICO")

# 1g. /me com token invÃ¡lido
s, b = _req("GET", "/auth/me", token="eyJinvalid.token.here")
check("/me token invÃ¡lido â†’ 401/403", s, b, [401, 403, 422], "AUTH", severity="CRÃTICO")

# 1h. Refresh token gerente
if mgr_refresh:
    s, b = _req("POST", "/auth/refresh", {"refresh_token": mgr_refresh})
    ok, _ = check("Refresh token â†’ novo par", s, b, [200], "AUTH", severity="MÃ‰DIO")
    new_mgr_token = b.get("access_token") if ok else mgr_token
    # Old refresh should now be revoked
    s2, b2 = _req("POST", "/auth/refresh", {"refresh_token": mgr_refresh})
    check("Refresh rotacionado (antigo invÃ¡lido) â†’ 401/403", s2, b2, [401, 403, 422], "AUTH",
          note="token rotation check", severity="BAIXO")
    mgr_token = new_mgr_token  # use fresh token from now on

# 1i. Logout
if op_token:
    s, b = _req("POST", "/auth/logout", token=op_token)
    check("Logout operador â†’ 204", s, b, [204], "AUTH", severity="MÃ‰DIO")
    # Token must be revoked now
    s2, b2 = _req("GET", "/auth/me", token=op_token)
    check("Token pÃ³s-logout revogado â†’ 401/403", s2, b2, [401, 403], "AUTH", severity="CRÃTICO")

# Re-login operador para usar nos testes de venda  (inclui empresa_id no body)
s, b = _req("POST", "/auth/pin-login", {"empresa_id": EMPRESA_ID, "codigo_operador": OP_CODE, "pin": OP_PIN})
ok, _ = check("Re-login operador apÃ³s logout", s, b, [200], "AUTH", severity="CRÃTICO")
op_token = b.get("access_token") if ok else None

# 1j. Senha errada
s, b = _req("POST", "/auth/login", {"empresa_id": EMPRESA_ID, "email": MGR_EMAIL, "senha": "SenhaErrada999!"})
check("Login senha errada â†’ 401", s, b, [401, 403, 422], "AUTH", severity="CRÃTICO")

# 1k. Email nÃ£o existe
s, b = _req("POST", "/auth/login", {"empresa_id": EMPRESA_ID, "email": "naoexiste@zenite.dev", "senha": "Abc123!"})
check("Login email inexistente â†’ 401/404", s, b, [401, 403, 404, 422], "AUTH", severity="MÃ‰DIO")

# â”€â”€â”€ 2. SEPARAÃ‡ÃƒO DE PERFIL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\nâ•â•â• 2. SEPARAÃ‡ÃƒO DE PERFIL â•â•â•")

# 2a. Operador tenta acessar rota gerencial â†’ 403
# NOTE: op_token may be None at this point if logout happened; we use mgr_pin_token as a fallback
_op_test_token = op_token  # fresh from login before logout
if _op_test_token is None and mgr_pin_token:
    # Use a new login to get fresh op token for this test
    s_tmp, b_tmp = _req("POST", "/auth/pin-login", {"empresa_id": EMPRESA_ID, "codigo_operador": OP_CODE, "pin": OP_PIN})
    _op_test_token = b_tmp.get("access_token") if s_tmp == 200 else None

if _op_test_token:
    s, b = _req("GET", "/gerencial/dashboard", token=_op_test_token)
    check("Operador â†’ /gerencial/dashboard bloqueado â†’ 403", s, b, [403, 401], "PERFIL",
          severity="CRÃTICO")
else:
    print(f"{_WARN} [PERFIL] Sem token operador para teste de bloqueio")
    results.append({"ok": False, "tag": "PERFIL", "name": "Operador â†’ /gerencial/dashboard bloqueado â†’ 403",
                    "status": 0, "expected": [403,401], "body": "token unavailable",
                    "severity": "CRÃTICO", "note": "op_token indisponÃ­vel"})

# 2b. Gerente pode acessar dashboard
if mgr_token:
    s, b = _req("GET", "/gerencial/dashboard", token=mgr_token)
    check("Gerente â†’ /gerencial/dashboard â†’ 200", s, b, [200], "PERFIL", severity="CRÃTICO")

# 2c. Gerente â†’ lista produtos gerencial
if mgr_token:
    s, b = _req("GET", "/gerencial/produtos", token=mgr_token)
    check("Gerente â†’ /gerencial/produtos â†’ 200", s, b, [200], "PERFIL", severity="MÃ‰DIO")

# 2d. Gerente â†’ lista usuÃ¡rios
if mgr_token:
    s, b = _req("GET", "/gerencial/usuarios", token=mgr_token)
    check("Gerente â†’ /gerencial/usuarios â†’ 200", s, b, [200], "PERFIL", severity="MÃ‰DIO")

# 2e. Gerente â†’ lista sessÃµes
if mgr_token:
    s, b = _req("GET", "/gerencial/sessoes", token=mgr_token)
    check("Gerente â†’ /gerencial/sessoes â†’ 200", s, b, [200], "PERFIL", severity="MÃ‰DIO")

# 2f. Operador tenta criar produto
if _op_test_token:
    s, b = _req("POST", "/gerencial/produtos", {
        "descricao": "HACK", "ean": "0000000000001", "preco_venda": 1.00,
        "unidade_medida": "UN", "perfil_tributario_id": "00000000-0000-0000-0000-000000000001"
    }, token=_op_test_token)
    check("Operador â†’ POST /gerencial/produtos bloqueado â†’ 403", s, b, [403, 401], "PERFIL",
          severity="CRÃTICO")

# â”€â”€â”€ 3. CAIXA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\nâ•â•â• 3. CAIXA â•â•â•")

# 3a. SessÃ£o ativa existente
sessao_status: str | None = None
if mgr_token:
    s, b = _req("GET", f"/caixa/sessao-ativa?caixa_id={CAIXA_ID}", token=mgr_token)
    ok_sessao, _ = check("GET sessao-ativa â†’ 200 ou 404", s, b, [200, 404], "CAIXA", severity="CRÃTICO")
    sessao_id = b.get("id") if s == 200 else None
    sessao_status = b.get("status") if s == 200 else None
    print(f"  â””â”€ sessao_id={sessao_id}, status={sessao_status}")

# 3b. Tentar abrir caixa com sessÃ£o jÃ¡ aberta â†’ 409
if mgr_token and sessao_id and sessao_status == "aberta":
    s, b = _req("POST", "/caixa/sessoes", {
        "caixa_id": CAIXA_ID, "saldo_abertura": "0.00"
    }, token=mgr_token)
    check("Abrir caixa com sessÃ£o aberta â†’ 409", s, b, [409], "CAIXA", severity="MÃ‰DIO")

# 3c. Fechar sessÃ£o atual e abrir nova (fluxo limpo)
if mgr_token and sessao_id and sessao_status == "aberta":
    s, b = _req("POST", f"/caixa/sessoes/{sessao_id}/fechar",
                {"saldo_informado_fechamento": "0.00", "observacao": "QA test close"},
                token=mgr_token)
    check("Fechar sessÃ£o existente â†’ 200", s, b, [200], "CAIXA", severity="CRÃTICO")
    # Validate totals in response
    if s == 200:
        for field in ("total_vendas_bruto","total_dinheiro","total_pix","quantidade_vendas"):
            has = field in b
            check(f"Fechar sessÃ£o: campo {field} presente", 200 if has else 422, {},
                  [200], "CAIXA", note=f"val={b.get(field)}", severity="BAIXO")

# 3d. Abrir nova sessÃ£o
if mgr_token:
    s, b = _req("POST", "/caixa/sessoes", {
        "caixa_id": CAIXA_ID, "saldo_abertura": "100.00"
    }, token=mgr_token)
    ok_open, _ = check("Abrir nova sessÃ£o â†’ 201", s, b, [201], "CAIXA", severity="CRÃTICO")
    sessao_id = b.get("id") if ok_open else sessao_id

# 3e. SessÃ£o ativa apÃ³s abertura
if mgr_token:
    s, b = _req("GET", f"/caixa/sessao-ativa?caixa_id={CAIXA_ID}", token=mgr_token)
    check("GET sessao-ativa apÃ³s abertura â†’ 200", s, b, [200], "CAIXA", severity="CRÃTICO")
    if s == 200:
        check("SessÃ£o status=aberta", 200 if b.get("status") == "aberta" else 422, {},
              [200], "CAIXA", note=f"status={b.get('status')}", severity="MÃ‰DIO")

# 3f. SessÃ£o ativa sem token â†’ 401/403 (auth guard)
s, b = _req("GET", f"/caixa/sessao-ativa?caixa_id={CAIXA_ID}")
check("GET sessao-ativa sem token â†’ 401/403 (requer auth)",
      s, b, [401, 403], "CAIXA",
      note="sessao-ativa usa get_empresa_id que exige auth",
      severity="BAIXO")

# 3g. Fechar sessÃ£o sem token â†’ 401/403
if sessao_id:
    s, b = _req("POST", f"/caixa/sessoes/{sessao_id}/fechar",
                {"saldo_informado_fechamento": "50.00"})
    check("Fechar sessÃ£o sem token â†’ 401/403", s, b, [401, 403], "CAIXA", severity="CRÃTICO")

# â”€â”€â”€ 4. PRODUTO â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\nâ•â•â• 4. PRODUTO â•â•â•")

# NOTE: produto endpoints usam get_empresa_id â†’ get_current_user â†’ requerem auth
# 4a. Busca por EAN vÃ¡lido (autenticado)
s, b = _req("GET", f"/produtos/ean/{PRODUTO_EAN}", token=op_token)
ok_prod, _ = check("GET produto por EAN (autenticado) â†’ 200", s, b, [200], "PRODUTO", severity="CRÃTICO")
if ok_prod:
    for f in ("id","descricao","preco_venda","codigo_barras_principal"):
        check(f"Produto campo {f}", 200 if f in b else 422, {}, [200], "PRODUTO",
              note=f"{f}={b.get(f)}", severity="BAIXO")

# 4a-unauth. EAN sem auth â†’ 401 (por design - precisa estar logado)
s, b = _req("GET", f"/produtos/ean/{PRODUTO_EAN}")
check("GET produto por EAN sem token â†’ 401 (por design)", s, b, [401], "PRODUTO",
      note="produtos requerem auth por design (empresa_id vem do token)", severity="BAIXO")

# 4b. EAN inexistente â†’ 404
s, b = _req("GET", "/produtos/ean/0000000000000", token=op_token)
check("EAN inexistente â†’ 404", s, b, [404], "PRODUTO", severity="MÃ‰DIO")

# 4c. Produto por UUID vÃ¡lido
s, b = _req("GET", f"/produtos/{PRODUTO_ID}", token=op_token)
check("GET produto por UUID â†’ 200", s, b, [200], "PRODUTO", severity="MÃ‰DIO")

# 4d. UUID invÃ¡lido â†’ 404/422
s, b = _req("GET", "/produtos/00000000-0000-0000-0000-000000000000", token=op_token)
check("UUID produto inexistente â†’ 404", s, b, [404, 422], "PRODUTO", severity="BAIXO")

# â”€â”€â”€ 5. PDV / VENDA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\nâ•â•â• 5. PDV / VENDA â•â•â•")

if not (op_token and sessao_id):
    print(f"{_WARN} Sem op_token ou sessao_id â€” saltando testes de venda")
else:
    # 5a. Iniciar venda gerencial (tipo_emissao vai sÃ³ no FINALIZAR, nÃ£o no iniciar)
    s, b = _req("POST", "/vendas/", {
        "sessao_caixa_id": sessao_id
    }, token=op_token)
    ok_venda, _ = check("Iniciar venda â†’ 201", s, b, [201], "VENDA", severity="CRÃTICO")
    venda_id = b.get("id") if ok_venda else None

    # 5b. Adicionar item
    if venda_id:
        s, b = _req("POST", f"/vendas/{venda_id}/itens", {
            "produto_id": PRODUTO_ID, "quantidade": "2.000"
        }, token=op_token)
        ok_item, _ = check("Adicionar item (qty=2) â†’ 201", s, b, [201], "VENDA", severity="CRÃTICO")
        item_id = None
        if ok_item and b.get("itens"):
            item_id = b["itens"][0]["id"]
            check("Item quantidade=2", 200 if float(b["itens"][0]["quantidade"]) == 2.0 else 422, {},
                  [200], "VENDA", note=f"qty={b['itens'][0]['quantidade']}", severity="MÃ‰DIO")

        # 5c. Remover item
        if item_id:
            s, b = _req("DELETE", f"/vendas/{venda_id}/itens/{item_id}", token=op_token)
            check("Remover item â†’ 200", s, b, [200], "VENDA", severity="MÃ‰DIO")
            if s == 200:
                check("Itens vazios apÃ³s remover", 200 if not [i for i in b.get("itens",[]) if not i.get("cancelado")] else 422, {},
                      [200], "VENDA", note=f"itens_ativos={[i for i in b.get('itens',[]) if not i.get('cancelado')]}", severity="MÃ‰DIO")

        # 5d. Re-adicionar item
        s, b = _req("POST", f"/vendas/{venda_id}/itens", {
            "produto_id": PRODUTO_ID, "quantidade": "1.000"
        }, token=op_token)
        ok_item2, _ = check("Re-adicionar item (qty=1) â†’ 201", s, b, [201], "VENDA", severity="CRÃTICO")
        if ok_item2 and b.get("itens"):
            item_id2 = next((i["id"] for i in b["itens"] if not i.get("cancelado")), None)
        else:
            item_id2 = None

        # 5e. Pagamento com valor insuficiente
        s, b = _req("POST", f"/vendas/{venda_id}/pagamentos", {
            "forma_pagamento": "01", "valor": "0.01"
        }, token=op_token)
        check("Pagamento valor insuficiente parcial â†’ 201 (parcial permitido)", s, b, [201, 422, 400],
              "VENDA", note="sistema aceita pagamento parcial?", severity="MÃ‰DIO")

        # Limpar venda e criar nova para teste de finalizaÃ§Ã£o limpa
        s_venda, b_venda = _req("GET", f"/vendas/{venda_id}", token=op_token)
        valor_total = float(b_venda.get("total_liquido", 0)) if s_venda == 200 else 8.99
        total_pago = sum(float(p["valor"]) for p in b_venda.get("pagamentos", []))
        falta_pagar = round(valor_total - total_pago, 2)

        # 5f. Completar pagamento com DINHEIRO (troco deve ser enviado explicitamente pelo cliente)
        if falta_pagar > 0:
            troco_enviado = round(10.00, 2)
            s, b = _req("POST", f"/vendas/{venda_id}/pagamentos", {
                "forma_pagamento": "01", "valor": str(round(falta_pagar + troco_enviado, 2)),
                "troco": str(troco_enviado),  # troco é declarativo — cliente calcula e informa
            }, token=op_token)
            check("Pagamento com troco → 201", s, b, [201], "VENDA", severity="MÉDIO")
            if s == 201:
                pagamentos = b.get("pagamentos", [])
                troco_total = sum(float(p.get("troco", 0)) for p in pagamentos)
                check("Troco calculado > 0", 200 if troco_total > 0 else 422, {},
                      [200], "VENDA", note=f"troco={troco_total}", severity="MÉDIO")

        # 5g. Finalizar venda gerencial
        s, b = _req("POST", f"/vendas/{venda_id}/finalizar", {
            "tipo_emissao": "GERENCIAL"
        }, token=op_token)
        check("Finalizar venda GERENCIAL â†’ 200", s, b, [200], "VENDA", severity="CRÃTICO")
        if s == 200:
            # Status enum value is lowercase "concluida"
            check("Status=concluida", 200 if b.get("status") == "concluida" else 422, {},
                  [200], "VENDA", note=f"status={b.get('status')}", severity="CRÃTICO")
            check("GERENCIAL: documento_fiscal_id=null", 200 if b.get("documento_fiscal_id") is None else 422, {},
                  [200], "VENDA", note=f"doc_id={b.get('documento_fiscal_id')}", severity="MÃ‰DIO")

    # 5h. Iniciar venda FISCAL (tipo_emissao definido no finalizar)
    s, b = _req("POST", "/vendas/", {
        "sessao_caixa_id": sessao_id
    }, token=op_token)
    ok_fiscal, _ = check("Iniciar venda FISCAL â†’ 201", s, b, [201], "VENDA", severity="CRÃTICO")
    venda_fiscal_id = b.get("id") if ok_fiscal else None

    if venda_fiscal_id:
        # Adicionar item
        s, b = _req("POST", f"/vendas/{venda_fiscal_id}/itens", {
            "produto_id": PRODUTO_ID, "quantidade": "1.000"
        }, token=op_token)
        check("Venda FISCAL: adicionar item â†’ 201", s, b, [201], "VENDA", severity="CRÃTICO")
        valor_item = float(b.get("total_liquido", 8.99)) if s == 201 else 8.99

        # Pagar com PIX
        s, b = _req("POST", f"/vendas/{venda_fiscal_id}/pagamentos", {
            "forma_pagamento": "17", "valor": str(valor_item)
        }, token=op_token)
        check("Venda FISCAL: pagamento PIX â†’ 201", s, b, [201], "VENDA", severity="MÃ‰DIO")

        # Finalizar FISCAL
        s, b = _req("POST", f"/vendas/{venda_fiscal_id}/finalizar", {
            "tipo_emissao": "FISCAL"
        }, token=op_token)
        check("Finalizar venda FISCAL â†’ 200", s, b, [200], "VENDA", severity="CRÃTICO")
        if s == 200:
            check("FISCAL: documento_fiscal_id preenchido", 200 if b.get("documento_fiscal_id") else 422, {},
                  [200], "VENDA", note=f"doc_id={b.get('documento_fiscal_id')}", severity="MÃ‰DIO")

    # 5i. Venda com sessÃ£o inexistente â†’ 4xx
    s, b = _req("POST", "/vendas/", {
        "sessao_caixa_id": "00000000-0000-0000-0000-000000000000"
    }, token=op_token)
    check("Venda sessÃ£o inexistente â†’ 4xx", s, b, [400, 404, 409, 422], "VENDA", severity="MÃ‰DIO")

    # 5j. Sem token â†’ 401/403
    s, b = _req("POST", "/vendas/", {"sessao_caixa_id": sessao_id})
    check("Iniciar venda sem token â†’ 401/403", s, b, [401, 403], "VENDA", severity="CRÃTICO")

# â”€â”€â”€ 6. ESTOQUE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\nâ•â•â• 6. ESTOQUE (via gerencial) â•â•â•")

if mgr_token:
    # 6a. Verificar saldo apÃ³s vendas via gerencial
    s, b = _req("GET", f"/gerencial/produtos", token=mgr_token)
    check("GET gerencial/produtos â†’ 200", s, b, [200], "ESTOQUE", severity="MÃ‰DIO")
    if s == 200:
        products = b if isinstance(b, list) else b.get("items", b.get("data", []))
        # Find our product
        our_prod = next((p for p in (products if isinstance(products, list) else []) 
                         if p.get("id") == PRODUTO_ID), None)
        if our_prod:
            print(f"  â””â”€ Produto saldo: {our_prod}")
        else:
            print(f"  â””â”€ Produto nÃ£o encontrado na lista gerencial (response type={type(b)})")

# 6b. Test produto sem local de estoque (EAN nÃ£o existente jÃ¡ testado acima)
# The key check is that adding an item to a venda doesn't 500 â€” already covered above

# â”€â”€â”€ 7. GERENCIAL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\nâ•â•â• 7. RETAGUARDA GERENCIAL â•â•â•")

if mgr_token:
    # 7a. Dashboard
    s, b = _req("GET", "/gerencial/dashboard", token=mgr_token)
    ok_dash, _ = check("GET /gerencial/dashboard â†’ 200", s, b, [200], "GERENCIAL", severity="CRÃTICO")
    if ok_dash:
        # Correct field names from DashboardDTO
        for field in ("data_referencia","total_vendas","qtd_vendas","ticket_medio",
                      "sessoes_abertas","total_semana","total_mes"):
            check(f"Dashboard: campo {field}", 200 if field in b else 422, {},
                  [200], "GERENCIAL", note=f"{field}={b.get(field)}", severity="BAIXO")

    # 7b. Produtos gerencial
    s, b = _req("GET", "/gerencial/produtos", token=mgr_token)
    check("GET /gerencial/produtos â†’ 200", s, b, [200], "GERENCIAL", severity="MÃ‰DIO")

    # 7c. Unidades
    s, b = _req("GET", "/gerencial/unidades", token=mgr_token)
    check("GET /gerencial/unidades â†’ 200", s, b, [200], "GERENCIAL", severity="BAIXO")

    # 7d. Perfis tributÃ¡rios
    s, b = _req("GET", "/gerencial/perfis-tributarios", token=mgr_token)
    check("GET /gerencial/perfis-tributarios â†’ 200", s, b, [200], "GERENCIAL", severity="BAIXO")

    # 7e. UsuÃ¡rios
    s, b = _req("GET", "/gerencial/usuarios", token=mgr_token)
    check("GET /gerencial/usuarios â†’ 200", s, b, [200], "GERENCIAL", severity="MÃ‰DIO")

    # 7f. SessÃµes
    s, b = _req("GET", "/gerencial/sessoes", token=mgr_token)
    check("GET /gerencial/sessoes â†’ 200", s, b, [200], "GERENCIAL", severity="MÃ‰DIO")

    # 7g. Criar produto via gerencial  (ProdutoCreateRequest usa unidade_id: UUID)
    import time as _time
    ts = int(_time.time())
    # First need a unidade_id (not just a code string)
    s_un, b_un = _req("GET", "/gerencial/unidades", token=mgr_token)
    unidade_id = None
    if s_un == 200:
        unidades = b_un if isinstance(b_un, list) else []
        if unidades:
            unidade_id = unidades[0].get("id")

    # Also need perfil_tributario_id
    s_pt, b_pt = _req("GET", "/gerencial/perfis-tributarios", token=mgr_token)
    pt_id = None
    if s_pt == 200:
        perfis = b_pt if isinstance(b_pt, list) else []
        if perfis:
            pt_id = perfis[0].get("id")

    if unidade_id and pt_id:
        s, b = _req("POST", "/gerencial/produtos", {
            "descricao": f"PRODUTO QA {ts}",
            "codigo_barras_principal": f"{ts % 10000000000000:013d}",
            "preco_venda": 9.99,
            "unidade_id": unidade_id,
            "perfil_tributario_id": pt_id,
            "controla_estoque": False,
            "ativo": True,
        }, token=mgr_token)
        check("Criar produto gerencial â†’ 201", s, b, [201], "GERENCIAL", severity="MÃ‰DIO")
        new_prod_id = b.get("id") if s == 201 else None

        # 7h. PATCH produto
        if new_prod_id:
            s, b = _req("PATCH", f"/gerencial/produtos/{new_prod_id}", {
                "preco_venda": 12.99
            }, token=mgr_token)
            check("PATCH produto â†’ 200", s, b, [200], "GERENCIAL", severity="MÃ‰DIO")
    else:
        print(f"{_WARN} [GERENCIAL] Sem unidade_id ou pt_id â€” saltando criar produto")
        results.append({"ok": False, "tag": "GERENCIAL", "name": "Criar produto gerencial â†’ 201",
                        "status": 0, "expected": [201], "body": "sem unidade_id",
                        "severity": "MÃ‰DIO", "note": f"unidade_id={unidade_id}, pt_id={pt_id}"})

    # 7i. Criar usuÃ¡rio  (UsuarioCreateRequest requires senha)
    ts2 = int(_time.time())
    s, b = _req("POST", "/gerencial/usuarios", {
        "nome": f"Operador QA {ts2}",
        "email": f"opqa{ts2}@zenite.dev",
        "senha": "Senha@123",
        "codigo_operador": f"QA{ts2 % 10000:04d}",
        "pin": "5678",
        "perfil": "operador_caixa"
    }, token=mgr_token)
    check("Criar usuÃ¡rio operador â†’ 201", s, b, [201], "GERENCIAL", severity="MÃ‰DIO")
    new_user_id = b.get("id") if s == 201 else None

    # 7j. PATCH status usuário  (ativo é query param, não body)
    if new_user_id:
        s, b = _req("PATCH", f"/gerencial/usuarios/{new_user_id}/status?ativo=false", token=mgr_token)
        check("PATCH status usuário (desativar) → 200", s, b, [200], "GERENCIAL", severity="MÉDIO")

# â”€â”€â”€ 8. HEALTH / INFRA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\nâ•â•â• 8. HEALTH / INFRA â•â•â•")

import urllib.request as _urq
try:
    with _urq.urlopen("https://zenite-pdv-api-production.up.railway.app/health", timeout=10) as r:
        raw_h = r.read()
        s_h = r.status
        try:
            body_h = json.loads(raw_h)
        except:
            body_h = raw_h.decode()
    check("GET /health â†’ 200", s_h, body_h, [200], "INFRA", severity="CRÃTICO")
    if isinstance(body_h, dict):
        check("health: campo 'status'", 200 if "status" in body_h else 422, {}, [200], "INFRA",
              note=f"status={body_h.get('status')}", severity="BAIXO")
        # NOTE: /health nÃ£o verifica Redis/DB â€” Ã© apenas um ping de processo
        has_redis = "redis" in str(body_h).lower()
        print(f"  â””â”€ /health body={body_h} | redis_no_health={has_redis} (design: health nÃ£o checa dependÃªncias)")
        results.append({"ok": True, "tag": "INFRA", "name": "health: redis ausente (por design)",
                        "status": 200, "expected": [200], "body": body_h,
                        "severity": "BAIXO", "note": "health nÃ£o checa Redis/DB â€” gap de observabilidade"})
except Exception as e:
    check("/health erro de conexÃ£o", 0, str(e), [200], "INFRA", severity="CRÃTICO")

# â”€â”€â”€ RELATÃ“RIO â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n" + "â•"*70)
print("RELATÃ“RIO FINAL DE QA")
print("â•"*70)

passed = [r for r in results if r["ok"]]
failed = [r for r in results if not r["ok"]]

print(f"\nâœ“ Passou:  {len(passed)}/{len(results)}")
print(f"âœ— Falhou:  {len(failed)}/{len(results)}")

if failed:
    print("\nâ”€â”€â”€ FALHAS â”€â”€â”€")
    for r in failed:
        sev = r.get("severity","?")
        print(f"  [{sev}] [{r['tag']}] {r['name']}")
        print(f"         HTTP {r['status']} (esperado {r['expected']}) | {r['note']}")
        body_str = str(r['body'])
        if len(body_str) > 200:
            body_str = body_str[:200] + "..."
        print(f"         body: {body_str}")

# Save JSON results
with open("qa_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, default=str, indent=2)
print("\nResultados salvos em qa_results.json")

