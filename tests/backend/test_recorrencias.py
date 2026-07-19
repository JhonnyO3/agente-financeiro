import os

for var, valor in {
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/test",
}.items():
    os.environ.setdefault(var, valor)

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.dtos.recorrencia import RecorrenciaCreate, RecorrenciaUpdate
from backend.services import recorrencias as service
from backend.services.janela import janela_meses


class _Store:
    def __init__(self) -> None:
        self.recorrencias: dict[int, SimpleNamespace] = {}
        self.lancamentos: list[tuple[int, date, int | None]] = []
        self.transacoes: dict[int, object] = {}
        self.seq_rec = 0
        self.seq_trans = 0


class _FakeRecRepo:
    def __init__(self, session) -> None:
        self.s: _Store = session.store

    async def criar(
        self, usuario_id, descricao, tipo, categoria, valor,
        dia_vencimento=None, forma_pagamento=None, ativo=True,
    ):
        self.s.seq_rec += 1
        obj = SimpleNamespace(
            id=self.s.seq_rec,
            usuario_id=usuario_id,
            descricao=descricao,
            tipo=tipo,
            categoria=categoria,
            valor=valor,
            dia_vencimento=dia_vencimento,
            forma_pagamento=forma_pagamento,
            ativo=ativo,
            criado_em=None,
            encerrado_em=None,
        )
        self.s.recorrencias[obj.id] = obj
        return obj

    async def listar(self, usuario_id, ativo=None):
        return [
            r for r in self.s.recorrencias.values()
            if r.usuario_id == usuario_id and (ativo is None or r.ativo == ativo)
        ]

    async def listar_ativas(self, usuario_id):
        return await self.listar(usuario_id, ativo=True)

    async def buscar_por_id(self, id, usuario_id=None):
        obj = self.s.recorrencias.get(id)
        if obj is None:
            return None
        if usuario_id is not None and obj.usuario_id != usuario_id:
            return None
        return obj

    async def atualizar(self, id, dados, usuario_id=None):
        obj = await self.buscar_por_id(id, usuario_id=usuario_id)
        for campo, valor in dados.items():
            setattr(obj, campo, valor)
        return obj

    async def excluir(self, id, usuario_id=None):
        obj = await self.buscar_por_id(id, usuario_id=usuario_id)
        if obj is not None:
            self.s.recorrencias.pop(id, None)

    async def existe_lancamento(self, recorrencia_id, competencia):
        return any(
            rid == recorrencia_id and comp == competencia
            for rid, comp, _ in self.s.lancamentos
        )

    async def registrar_lancamento(self, recorrencia_id, competencia, transacao_id=None):
        self.s.lancamentos.append((recorrencia_id, competencia, transacao_id))


class _FakeTransRepo:
    def __init__(self, session) -> None:
        self.s: _Store = session.store

    async def criar(self, transacao):
        self.s.seq_trans += 1
        obj = SimpleNamespace(id=self.s.seq_trans, dados=transacao)
        self.s.transacoes[obj.id] = obj
        return obj


@pytest.fixture(autouse=True)
def _patch_repos(monkeypatch):
    monkeypatch.setattr(service, "RecorrenciaRepository", _FakeRecRepo)
    monkeypatch.setattr(service, "TransacaoRepository", _FakeTransRepo)


def _session():
    return SimpleNamespace(store=_Store())


# --- CRUD + isolamento -------------------------------------------------------

@pytest.mark.asyncio
async def test_criar_e_listar():
    sess = _session()
    await service.criar(sess, 1, RecorrenciaCreate(descricao="Spotify", valor=Decimal("23.00")))
    itens = await service.listar(sess, 1)
    assert len(itens) == 1
    assert itens[0]["descricao"] == "Spotify"
    assert itens[0]["valor"] == "23.00"
    assert itens[0]["ativo"] is True


@pytest.mark.asyncio
async def test_isolamento_por_usuario():
    sess = _session()
    await service.criar(sess, 1, RecorrenciaCreate(descricao="Netflix", valor=Decimal("40")))
    assert await service.listar(sess, 2) == []
    assert len(await service.listar(sess, 1)) == 1


@pytest.mark.asyncio
async def test_atualizar_de_outro_usuario_falha():
    sess = _session()
    criada = await service.criar(sess, 1, RecorrenciaCreate(descricao="X", valor=Decimal("10")))
    with pytest.raises(service.NaoEncontradaError):
        await service.atualizar(sess, 2, criada["id"], RecorrenciaUpdate(valor=Decimal("99")))


@pytest.mark.asyncio
async def test_excluir_de_outro_usuario_falha():
    sess = _session()
    criada = await service.criar(sess, 1, RecorrenciaCreate(descricao="X", valor=Decimal("10")))
    with pytest.raises(service.NaoEncontradaError):
        await service.excluir(sess, 2, criada["id"])
    assert len(await service.listar(sess, 1)) == 1


@pytest.mark.asyncio
async def test_atualizar_ativo_false_marca_encerrado():
    sess = _session()
    criada = await service.criar(sess, 1, RecorrenciaCreate(descricao="X", valor=Decimal("10")))
    atualizada = await service.atualizar(sess, 1, criada["id"], RecorrenciaUpdate(ativo=False))
    assert atualizada["ativo"] is False
    assert atualizada["encerrado_em"] is not None


# --- garantir_janela ---------------------------------------------------------

@pytest.mark.asyncio
async def test_garantir_janela_cria_uma_por_mes():
    sess = _session()
    await service.criar(sess, 1, RecorrenciaCreate(descricao="Aluguel", valor=Decimal("1200")))
    hoje = date(2026, 7, 18)
    meses = len(janela_meses(hoje)[6:])

    gerados = await service.garantir_janela(sess, 1, hoje)
    assert gerados == meses
    assert len(sess.store.transacoes) == meses
    assert len(sess.store.lancamentos) == meses


@pytest.mark.asyncio
async def test_garantir_janela_idempotente():
    sess = _session()
    await service.criar(sess, 1, RecorrenciaCreate(descricao="Aluguel", valor=Decimal("1200")))
    hoje = date(2026, 7, 18)

    primeiro = await service.garantir_janela(sess, 1, hoje)
    segundo = await service.garantir_janela(sess, 1, hoje)
    assert segundo == 0
    assert len(sess.store.transacoes) == primeiro


@pytest.mark.asyncio
async def test_log_impede_recriar_transacao_apagada():
    sess = _session()
    await service.criar(sess, 1, RecorrenciaCreate(descricao="Aluguel", valor=Decimal("1200")))
    hoje = date(2026, 7, 18)

    gerados = await service.garantir_janela(sess, 1, hoje)
    assert gerados > 0
    sess.store.transacoes.clear()

    regerados = await service.garantir_janela(sess, 1, hoje)
    assert regerados == 0
    assert sess.store.transacoes == {}


@pytest.mark.asyncio
async def test_garantir_janela_respeita_ativo_false():
    sess = _session()
    criada = await service.criar(sess, 1, RecorrenciaCreate(descricao="Aluguel", valor=Decimal("1200")))
    await service.atualizar(sess, 1, criada["id"], RecorrenciaUpdate(ativo=False))
    hoje = date(2026, 7, 18)

    gerados = await service.garantir_janela(sess, 1, hoje)
    assert gerados == 0
    assert sess.store.transacoes == {}


@pytest.mark.asyncio
async def test_garantir_janela_aplica_dia_vencimento():
    sess = _session()
    await service.criar(
        sess, 1,
        RecorrenciaCreate(descricao="Aluguel", valor=Decimal("1200"), dia_vencimento=15),
    )
    hoje = date(2026, 7, 18)
    await service.garantir_janela(sess, 1, hoje)

    datas = [t.dados.data for t in sess.store.transacoes.values()]
    assert all(d.day == 15 for d in datas)


@pytest.mark.asyncio
async def test_garantir_janela_dia_vencimento_clamp_fevereiro():
    sess = _session()
    await service.criar(
        sess, 1,
        RecorrenciaCreate(descricao="Aluguel", valor=Decimal("1200"), dia_vencimento=31),
    )
    hoje = date(2026, 1, 5)
    await service.garantir_janela(sess, 1, hoje)

    por_mes = {(t.dados.data.year, t.dados.data.month): t.dados.data for t in sess.store.transacoes.values()}
    assert por_mes[(2026, 2)].day == 28
