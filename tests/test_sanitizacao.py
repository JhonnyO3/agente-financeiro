"""Testes das regras puras da migração de sanitização 0004 (RF-08).

Verificam que `sql_sanitizacao()` gera os comandos corretos e idempotentes, sem
banco. A própria migração apenas executa esses statements via `op.execute`.
"""


def _todos():
    from scripts.sanitizacao import sql_sanitizacao

    return sql_sanitizacao()


def test_cartao_legado_vira_cartao_credito():
    stmts = _todos()
    assert any(
        "forma_pagamento='CARTAO_CREDITO'" in s and "forma_pagamento='CARTAO'" in s
        for s in stmts
    )


def test_nenhum_outro_remanescente():
    stmts = _todos()
    parcelado = next(
        s for s in stmts if "forma_pagamento='OUTRO'" in s and "parcela_total > 1" in s
    )
    avista = next(
        s
        for s in stmts
        if "SET forma_pagamento='PIX'" in s and "WHERE forma_pagamento='OUTRO'" in s
    )
    assert "recorrente = TRUE" in parcelado
    assert "CARTAO_CREDITO" in parcelado
    assert stmts.index(parcelado) < stmts.index(avista)


def test_resolucao_outro_ocorre_apos_marcar_recorrentes():
    stmts = _todos()
    recorrente = next(
        s for s in stmts if "recorrente=TRUE" in s and "Spotify" in s
    )
    resolve_outro = next(
        s for s in stmts if "WHERE forma_pagamento='OUTRO'" in s and "parcela_total" in s
    )
    assert stmts.index(recorrente) < stmts.index(resolve_outro)


def test_recategorizacao_educacao():
    stmts = _todos()
    educacao = next(s for s in stmts if "categoria='EDUCACAO'" in s)
    assert "asimov academy" in educacao
    assert "curso claude code" in educacao
    assert "curso de ingles" in educacao


def test_recategorizacao_compras():
    stmts = _todos()
    compras = next(s for s in stmts if "categoria='COMPRAS'" in s)
    for descricao in (
        "jogo batman play 5",
        "pandora do Morumbi",
        "parcela do carro no Kadu",
        "parcela do celular",
        "Nubank",
    ):
        assert descricao in compras


def test_recategorizacao_aquecedor_gastos_pontuais():
    stmts = _todos()
    assert any(
        "categoria='GASTOS_PONTUAIS'" in s and "parcela do aquecedor" in s for s in stmts
    )


def test_tipo_gasto_para_cursos_e_aquecedor():
    stmts = _todos()
    tipo = next(s for s in stmts if "SET tipo='GASTO'" in s)
    for descricao in (
        "asimov academy",
        "curso claude code",
        "curso de ingles",
        "parcela do aquecedor",
    ):
        assert descricao in tipo


def test_recorrentes_sem_parcela():
    stmts = _todos()
    recorrente = next(s for s in stmts if "recorrente=TRUE" in s)
    assert "parcela_numero=1" in recorrente
    assert "parcela_total=1" in recorrente
    for descricao in ("academia", "LinkedIn", "Spotify"):
        assert descricao in recorrente


def test_valores_fixos_corrigidos():
    stmts = _todos()
    esperado = {
        "parcela do aquecedor": "633",
        "parcela do carro no Kadu": "1200",
        "Nubank": "922",
        "cuecas": "174",
    }
    for descricao, valor in esperado.items():
        assert any(
            f"SET valor={valor}" in s and f"descricao='{descricao}'" in s for s in stmts
        )


def test_valores_batman_por_parcela():
    stmts = _todos()
    batman = next(s for s in stmts if "jogo batman play 5" in s and "CASE" in s)
    for numero, valor in {1: "74.90", 2: "74.91", 3: "74.92", 4: "74.93"}.items():
        assert f"WHEN parcela_numero={numero} THEN {valor}" in batman


def test_valor_celular_deterministico():
    stmts = _todos()
    celular = next(s for s in stmts if "parcela do celular" in s and "SET valor=" in s)
    assert "228 + (parcela_numero - 5) * 0.01" in celular


def test_remocoes_itens_de_teste():
    stmts = _todos()
    delete_simples = next(
        s for s in stmts if s.startswith("DELETE") and "Coxinha" in s
    )
    for descricao in ("Coxinha", "Sorvete do Mac", "tokens open ai"):
        assert descricao in delete_simples
    assert any(
        "Claude code" in s and "valor=472" in s and "OUTROS" in s and s.startswith("DELETE")
        for s in stmts
    )


def test_insercao_recorrentes_condicional():
    stmts = _todos()
    google = next(s for s in stmts if "Google Drive" in s and s.startswith("INSERT"))
    claude = next(s for s in stmts if "Claude code Max" in s and s.startswith("INSERT"))
    for s in (google, claude):
        assert "NOT EXISTS" in s
        assert "GASTOS_FIXOS" in s
        assert "TRUE" in s
        assert "CARTAO_CREDITO" in s
    assert "14.90" in google
    assert "500" in claude


def test_zara_isolado_do_grupo_batman():
    from scripts.sanitizacao import GRUPO_BATMAN, GRUPO_ZARA

    stmts = _todos()
    zara = next(s for s in stmts if "descricao='zara'" in s)
    assert GRUPO_ZARA in zara
    assert GRUPO_BATMAN in zara
    assert GRUPO_ZARA != GRUPO_BATMAN


def test_ordem_remocao_antes_da_resolucao_de_outro():
    stmts = _todos()
    delete_claude = next(
        i for i, s in enumerate(stmts) if s.startswith("DELETE") and "Claude code" in s
    )
    resolve_outro = next(
        i for i, s in enumerate(stmts) if "WHERE forma_pagamento='OUTRO'" in s
    )
    assert delete_claude < resolve_outro


def test_uuid_zara_valido():
    from uuid import UUID

    from scripts.sanitizacao import GRUPO_ZARA

    assert UUID(GRUPO_ZARA)
