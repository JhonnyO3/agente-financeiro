"""Recuperacao dos dados a partir do snapshot HTML do dashboard (perda de banco).

Local-only (NAO versionar — contem dados financeiros pessoais).

Conexao via variaveis de ambiente (evita encoding de senha na URL):
  DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, ADMIN_EMAIL

Uso:
  DB_HOST=2.25.184.39 DB_PORT=5432 DB_USER=FinanceiroAgent1 \
  DB_PASSWORD='...' DB_NAME=agente_financeiro_db \
  ADMIN_EMAIL=jhonatas2004@gmail.com \
  uv run python scripts/seed_recuperacao.py [--force]
"""

import asyncio
import os
import sys
import uuid
from datetime import date
from decimal import Decimal

import asyncpg

HOJE = date(2026, 6, 11)  # "hoje" do sistema no momento do snapshot

# --- 20 transacoes avulsas (pagina 1 da tabela, sem parcela) -------------------
# (data, descricao, categoria, valor, tipo, forma_pagamento, status, detalhes)
AVULSAS = [
    (date(2026, 6, 18), "Nubank", "COMPRAS", "922.00", "GASTO", "PIX", "PENDENTE", None),
    (date(2026, 6, 10), "ações bradesco bbdc3", "INVESTIMENTO", "1807.00", "INVESTIMENTO", "PIX", "PAGO", None),
    (date(2026, 6, 10), "bitcoin", "INVESTIMENTO", "3202.00", "INVESTIMENTO", "PIX", "PAGO", "Investimento realizado no mês passado."),
    (date(2026, 6, 10), "Investimento em renda fixa", "INVESTIMENTO", "25786.00", "INVESTIMENTO", "PIX", "PENDENTE", None),
    (date(2026, 6, 10), "Décimo terceiro", "RECEITA", "4644.00", "RECEITA", "PIX", "PAGO", None),
    (date(2026, 6, 10), "Salário do Bradesco", "RECEITA", "7463.00", "RECEITA", "PIX", "PAGO", None),
    (date(2026, 6, 10), "Sass", "RECEITA", "820.00", "RECEITA", "PIX", "PAGO", None),
    (date(2026, 6, 10), "Aquecedor quebrado (pago pela Roseli)", "RECEITA", "3800.00", "RECEITA", "PIX", "PAGO", None),
    (date(2026, 6, 10), "Recisão do Bradesco", "RECEITA", "22053.07", "RECEITA", "PIX", "PAGO", None),
    (date(2026, 6, 10), "Claude code Max", "GASTOS_FIXOS", "500.00", "GASTO", "CARTAO_CREDITO", "PENDENTE", None),
    (date(2026, 6, 10), "Google Drive", "GASTOS_FIXOS", "14.90", "GASTO", "CARTAO_CREDITO", "PENDENTE", None),
    (date(2026, 6, 10), "gasolina", "TRANSPORTE", "100.00", "GASTO", "PIX", "PENDENTE", None),
    (date(2026, 6, 10), "LinkedIn", "GASTOS_FIXOS", "70.00", "GASTO", "CARTAO_CREDITO", "PENDENTE", None),
    (date(2026, 6, 10), "Spotify", "GASTOS_FIXOS", "23.00", "GASTO", "CARTAO_CREDITO", "PENDENTE", None),
    (date(2026, 6, 10), "camiseta do brasil", "COMPRAS", "100.00", "GASTO", "PIX", "PENDENTE", None),
    (date(2026, 6, 10), "estacionamento", "TRANSPORTE", "60.00", "GASTO", "PIX", "PENDENTE", None),
    (date(2026, 6, 10), "capinha, garrafa e películas", "COMPRAS", "150.00", "GASTO", "PIX", "PENDENTE", None),
    (date(2026, 6, 9), "uber", "TRANSPORTE", "50.00", "GASTO", "PIX", "PAGO", None),
    (date(2026, 6, 9), "flores Natasha", "COMPRAS", "140.00", "GASTO", "PIX", "PAGO", None),
    (date(2026, 6, 6), "Investimento em bitcoin", "INVESTIMENTO", "2500.00", "INVESTIMENTO", "PIX", "PAGO", None),
]

# --- 9 parcelamentos ativos (reconstruidos por inteiro) ------------------------
# (descricao, categoria, n_total, valor_parcela, prox_data, prox_num)
# prox_data = data da proxima parcela pendente; prox_num = numero dela.
PARCELAS = [
    ("parcela do aquecedor", "COMPRAS", 6, "633.00", date(2026, 7, 6), 1),
    ("cuecas", "COMPRAS", 3, "174.00", date(2026, 7, 10), 1),
    ("jogo batman play 5", "COMPRAS", 4, "74.91", date(2026, 7, 10), 2),
    ("asimov academy", "EDUCACAO", 5, "200.00", date(2026, 7, 10), 2),
    ("parcela do carro no Kadu", "COMPRAS", 12, "1200.00", date(2026, 7, 10), 12),
    ("pandora do Morumbi", "COMPRAS", 4, "200.00", date(2026, 7, 10), 1),
    ("parcela do celular", "COMPRAS", 12, "228.00", date(2026, 7, 10), 5),
    ("curso claude code", "EDUCACAO", 12, "49.33", date(2026, 7, 10), 1),
    ("asimov academy", "EDUCACAO", 12, "167.00", date(2026, 7, 10), 8),
]

RESPONSAVEL = "Jhonatas"


def adicionar_meses(d: date, meses: int) -> date:
    total = d.month - 1 + meses
    ano = d.year + total // 12
    mes = total % 12 + 1
    return date(ano, mes, d.day)


def montar_linhas(usuario_id: int):
    linhas = []
    # avulsas
    for data, desc, cat, valor, tipo, forma, status, det in AVULSAS:
        linhas.append((
            tipo, Decimal(valor), desc, cat, data, 1, 1, str(uuid.uuid4()),
            status, forma, False, RESPONSAVEL, det, usuario_id,
        ))
    # parcelamentos
    for desc, cat, n, valor, prox_data, prox_num in PARCELAS:
        grupo = str(uuid.uuid4())
        for k in range(1, n + 1):
            data_k = adicionar_meses(prox_data, k - prox_num)
            status = "PAGO" if data_k <= HOJE else "PENDENTE"
            linhas.append((
                "GASTO", Decimal(valor), desc, cat, data_k, k, n, grupo,
                status, "CARTAO_CREDITO", False, RESPONSAVEL, None, usuario_id,
            ))
    return linhas


async def main() -> None:
    forcar = "--force" in sys.argv
    conn = await asyncpg.connect(
        host=os.environ["DB_HOST"], port=int(os.environ.get("DB_PORT", "5432")),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], timeout=15,
    )
    try:
        email = os.environ.get("ADMIN_EMAIL", "jhonatas2004@gmail.com").strip().lower()
        usuario_id = await conn.fetchval("SELECT id FROM usuarios WHERE lower(email)=$1", email)
        if usuario_id is None:
            print(f"ERRO: usuario {email} nao existe. Rode criar_usuario.py antes.")
            return
        existentes = await conn.fetchval(
            "SELECT count(*) FROM transacoes WHERE usuario_id=$1", usuario_id
        )
        if existentes and not forcar:
            print(f"ABORTADO: ja existem {existentes} transacoes para {email}. Use --force para inserir mesmo assim.")
            return
        linhas = montar_linhas(usuario_id)
        await conn.executemany(
            """
            INSERT INTO transacoes
              (tipo, valor, descricao, categoria, data, parcela_numero, parcela_total,
               grupo_parcela_id, status, forma_pagamento, recorrente, responsavel, detalhes, usuario_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
            """,
            linhas,
        )
        total = await conn.fetchval("SELECT count(*) FROM transacoes WHERE usuario_id=$1", usuario_id)
        print(f"OK: inseridas {len(linhas)} linhas. Total agora para {email}: {total}.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
