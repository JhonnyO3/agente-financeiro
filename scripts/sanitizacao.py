"""Regras puras da migração de sanitização 0004 (RF-08).

Este módulo concentra, em funções puras e testáveis sem banco, a derivação dos
comandos SQL aplicados pela migração ``migrations/versions/0004_sanitizacao_dados.py``.

A migração apenas importa ``sql_sanitizacao()`` e executa cada statement via
``op.execute``. Toda a regra de negócio (recategorização, recorrência, resolução
de ``OUTRO``, valores corrigidos, remoções, inserções e isolamento do ``zara``)
vive aqui para permitir verificação por ``pytest`` sem conexão Postgres.

Idempotência: cada statement carrega guardas (``WHERE`` por valor-alvo ou
``NOT EXISTS`` por ``descricao``) de modo que reaplicar a sequência completa não
duplica nem corrompe registros.
"""

GRUPO_BATMAN = "44da4151-66eb-4c6e-9941-e47f66258a2b"
GRUPO_ZARA = "0a7a0a7a-0a7a-4a7a-8a7a-0a7a0a7a0a7a"

CATEGORIA_POR_DESCRICAO = {
    "EDUCACAO": ("asimov academy", "curso claude code", "curso de ingles"),
    "COMPRAS": (
        "jogo batman play 5",
        "pandora do Morumbi",
        "parcela do carro no Kadu",
        "parcela do celular",
        "Nubank",
    ),
    "GASTOS_PONTUAIS": ("parcela do aquecedor",),
}

GASTO_POR_DESCRICAO = (
    "asimov academy",
    "curso claude code",
    "curso de ingles",
    "parcela do aquecedor",
)

RECORRENTES = ("academia", "LinkedIn", "Spotify")

VALOR_FIXO_POR_DESCRICAO = {
    "parcela do aquecedor": "633",
    "parcela do carro no Kadu": "1200",
    "Nubank": "922",
    "cuecas": "174",
}

VALOR_BATMAN_POR_PARCELA = {1: "74.90", 2: "74.91", 3: "74.92", 4: "74.93"}

REMOVER = ("Coxinha", "Sorvete do Mac", "tokens open ai")

INSERIR_RECORRENTES = (
    ("Google Drive", "14.90"),
    ("Claude code Max", "500"),
)


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _in_list(valores) -> str:
    return ", ".join(_quote(v) for v in valores)


def sql_forma_cartao_legado() -> list[str]:
    return [
        "UPDATE transacoes SET forma_pagamento='CARTAO_CREDITO' "
        "WHERE forma_pagamento='CARTAO'"
    ]


def sql_recategorizacao() -> list[str]:
    statements = []
    for categoria, descricoes in CATEGORIA_POR_DESCRICAO.items():
        statements.append(
            f"UPDATE transacoes SET categoria={_quote(categoria)} "
            f"WHERE descricao IN ({_in_list(descricoes)})"
        )
    statements.append(
        "UPDATE transacoes SET tipo='GASTO' "
        f"WHERE descricao IN ({_in_list(GASTO_POR_DESCRICAO)})"
    )
    return statements


def sql_recorrentes() -> list[str]:
    return [
        "UPDATE transacoes SET recorrente=TRUE, parcela_numero=1, parcela_total=1 "
        f"WHERE descricao IN ({_in_list(RECORRENTES)})"
    ]


def sql_valores_corrigidos() -> list[str]:
    statements = []
    for descricao, valor in VALOR_FIXO_POR_DESCRICAO.items():
        statements.append(
            f"UPDATE transacoes SET valor={valor} WHERE descricao={_quote(descricao)}"
        )
    casos = " ".join(
        f"WHEN parcela_numero={numero} THEN {valor}"
        for numero, valor in VALOR_BATMAN_POR_PARCELA.items()
    )
    statements.append(
        f"UPDATE transacoes SET valor=CASE {casos} ELSE valor END "
        "WHERE descricao='jogo batman play 5'"
    )
    statements.append(
        "UPDATE transacoes SET valor=228 + (parcela_numero - 5) * 0.01 "
        "WHERE descricao='parcela do celular'"
    )
    return statements


def sql_remocoes() -> list[str]:
    statements = [
        f"DELETE FROM transacoes WHERE descricao IN ({_in_list(REMOVER)})"
    ]
    statements.append(
        "DELETE FROM transacoes "
        "WHERE descricao='Claude code' AND valor=472 AND categoria='OUTROS'"
    )
    return statements


def sql_inserir_recorrentes() -> list[str]:
    statements = []
    for descricao, valor in INSERIR_RECORRENTES:
        statements.append(
            "INSERT INTO transacoes "
            "(tipo, valor, descricao, categoria, data, parcela_numero, parcela_total, "
            "grupo_parcela_id, status, forma_pagamento, responsavel, recorrente, criado_em) "
            f"SELECT 'GASTO', {valor}, {_quote(descricao)}, 'GASTOS_FIXOS', CURRENT_DATE, "
            "1, 1, gen_random_uuid(), 'PENDENTE', 'CARTAO_CREDITO', 'Jhonatas', TRUE, now() "
            "WHERE NOT EXISTS "
            f"(SELECT 1 FROM transacoes WHERE descricao={_quote(descricao)})"
        )
    return statements


def sql_isolar_zara() -> list[str]:
    return [
        f"UPDATE transacoes SET grupo_parcela_id={_quote(GRUPO_ZARA)}::uuid "
        f"WHERE descricao='zara' AND grupo_parcela_id={_quote(GRUPO_BATMAN)}::uuid"
    ]


def sql_resolver_outro() -> list[str]:
    return [
        "UPDATE transacoes SET forma_pagamento='CARTAO_CREDITO' "
        "WHERE forma_pagamento='OUTRO' AND (parcela_total > 1 OR recorrente = TRUE)",
        "UPDATE transacoes SET forma_pagamento='PIX' WHERE forma_pagamento='OUTRO'",
    ]


def sql_sanitizacao() -> list[str]:
    statements: list[str] = []
    statements += sql_forma_cartao_legado()
    statements += sql_recategorizacao()
    statements += sql_recorrentes()
    statements += sql_valores_corrigidos()
    statements += sql_remocoes()
    statements += sql_inserir_recorrentes()
    statements += sql_isolar_zara()
    statements += sql_resolver_outro()
    return statements
