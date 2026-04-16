"""Hash e verificação de senhas e PINs com bcrypt.

Usa a biblioteca bcrypt diretamente (sem passlib) para compatibilidade
com bcrypt >= 4.x que tem API incompatível com passlib 1.7.x.

Custos diferenciados:
  - Senha completa: custo 12 (recomendação OWASP para interativo)
  - PIN (4–6 dígitos): custo 10 — menor latência no PDV sem sacrificar
    a segurança, dado que o PIN é complementado pelo código de operador
    e pela vinculação à empresa.
"""
from __future__ import annotations

import bcrypt

_ROUNDS_PASSWORD = 12
_ROUNDS_PIN = 10


def hash_password(plain: str) -> str:
    """Gera hash bcrypt de senha completa (custo 12). Retorna string UTF-8."""
    hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=_ROUNDS_PASSWORD))
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica senha contra hash bcrypt armazenado."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def hash_pin(plain: str) -> str:
    """Gera hash bcrypt de PIN de operador (custo 10)."""
    hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=_ROUNDS_PIN))
    return hashed.decode("utf-8")


def verify_pin(plain: str, hashed: str) -> bool:
    """Verifica PIN contra hash bcrypt."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False
