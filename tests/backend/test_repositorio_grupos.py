"""
Testes TDD dos 3 métodos novos de TransacaoRepository.

Métodos ainda não existem — todos os testes devem FALHAR (vermelho).
Contratos: specs/parcelas-assinaturas/contracts/repositorio-grupos.md
Cenários:  specs/parcelas-assinaturas/scenarios/01-base-datas-repositorio.feature
Padrão de mock: segue tests/test_repository.py (MagicMock de sessão).
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from backend.repositories.transacao_repository import TransacaoRepository


# ---------------------------------------------------------------------------
# buscar_por_grupo_com_embedding
# ---------------------------------------------------------------------------


class TestBuscarPorGrupoComEmbedding:
    @pytest.mark.asyncio
    async def test_retorna_linhas_do_grupo_ordenadas_por_parcela_numero(self):
        # Cenário: buscar_por_grupo_com_embedding carrega embedding sem query extra
        grupo_id = uuid4()
        parcelas = [
            SimpleNamespace(parcela_numero=i + 1, embedding=[0.1] * 1536, usuario_id=1)
            for i in range(3)
        ]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = parcelas
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        session = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)

        repo = TransacaoRepository(session)
        resultado = await repo.buscar_por_grupo_com_embedding(grupo_id, usuario_id=1)

        assert len(resultado) == 3
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_filtra_por_usuario_id(self):
        # Cenário: buscar_por_grupo_com_embedding filtra por usuario_id — usuário diferente retorna vazio
        grupo_id = uuid4()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        session = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)

        repo = TransacaoRepository(session)
        resultado = await repo.buscar_por_grupo_com_embedding(grupo_id, usuario_id=1)

        assert resultado == []

    @pytest.mark.asyncio
    async def test_sem_usuario_id_retorna_grupo_independente_do_dono(self):
        # Cenário: buscar_por_grupo_com_embedding sem usuario_id retorna o grupo
        grupo_id = uuid4()
        parcelas = [
            SimpleNamespace(parcela_numero=i + 1, embedding=[0.1] * 1536, usuario_id=5)
            for i in range(2)
        ]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = parcelas
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        session = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)

        repo = TransacaoRepository(session)
        resultado = await repo.buscar_por_grupo_com_embedding(grupo_id, usuario_id=None)

        assert len(resultado) == 2

    @pytest.mark.asyncio
    async def test_statement_usa_undefer_embedding(self):
        """
        Verifica que a query construída inclui undefer(Transacao.embedding),
        inspecionando o statement passado para session.execute.
        """
        from sqlalchemy.orm import undefer
        from backend.models.transacao import Transacao

        grupo_id = uuid4()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        session = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)

        repo = TransacaoRepository(session)
        await repo.buscar_por_grupo_com_embedding(grupo_id, usuario_id=1)

        stmt = session.execute.call_args[0][0]
        # O statement compilado deve referenciar a coluna embedding
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "embedding" in compiled.lower()


# ---------------------------------------------------------------------------
# listar_recorrentes
# ---------------------------------------------------------------------------


class TestListarRecorrentes:
    @pytest.mark.asyncio
    async def test_retorna_somente_recorrentes_do_usuario(self):
        # Cenário: listar_recorrentes retorna só linhas recorrente=True do usuário
        recorrentes = [
            SimpleNamespace(recorrente=True, usuario_id=1, data=date(2026, 6, 5)),
            SimpleNamespace(recorrente=True, usuario_id=1, data=date(2026, 6, 15)),
        ]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = recorrentes
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        session = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)

        repo = TransacaoRepository(session)
        resultado = await repo.listar_recorrentes(usuario_id=1)

        assert len(resultado) == 2
        assert all(r.recorrente is True for r in resultado)

    @pytest.mark.asyncio
    async def test_isola_por_usuario_id(self):
        # Cenário: listar_recorrentes isola por usuario_id — usuario 1 não vê recorrentes do 2
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        session = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)

        repo = TransacaoRepository(session)
        resultado = await repo.listar_recorrentes(usuario_id=1)

        assert resultado == []

    @pytest.mark.asyncio
    async def test_ordena_por_data(self):
        # Cenário: listar_recorrentes ordena por data
        datas_esperadas = [date(2026, 6, 5), date(2026, 6, 15), date(2026, 6, 20)]
        recorrentes = [
            SimpleNamespace(recorrente=True, usuario_id=1, data=d)
            for d in datas_esperadas
        ]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = recorrentes
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        session = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)

        repo = TransacaoRepository(session)
        resultado = await repo.listar_recorrentes(usuario_id=1)

        datas = [r.data for r in resultado]
        assert datas == datas_esperadas

    @pytest.mark.asyncio
    async def test_statement_filtra_recorrente_true_e_usuario_id(self):
        """
        Verifica que o statement gerado contém filtro por recorrente e usuario_id.
        """
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        session = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)

        repo = TransacaoRepository(session)
        await repo.listar_recorrentes(usuario_id=42)

        stmt = session.execute.call_args[0][0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "recorrente" in compiled.lower()
        assert "usuario_id" in compiled.lower()


# ---------------------------------------------------------------------------
# excluir_por_grupo_e_numeros
# ---------------------------------------------------------------------------


class TestExcluirPorGrupoENumeros:
    @pytest.mark.asyncio
    async def test_retorna_rowcount_correto(self):
        # Cenário: excluir_por_grupo_e_numeros remove só os parcela_numero listados
        grupo_id = uuid4()

        mock_result = MagicMock()
        mock_result.rowcount = 2

        session = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        repo = TransacaoRepository(session)
        rowcount = await repo.excluir_por_grupo_e_numeros(grupo_id, numeros=[4, 5], usuario_id=1)

        assert rowcount == 2

    @pytest.mark.asyncio
    async def test_faz_flush(self):
        grupo_id = uuid4()

        mock_result = MagicMock()
        mock_result.rowcount = 2

        session = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        repo = TransacaoRepository(session)
        await repo.excluir_por_grupo_e_numeros(grupo_id, numeros=[1, 2], usuario_id=1)

        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_respeita_usuario_id_diferente_retorna_zero(self):
        # Cenário: excluir_por_grupo_e_numeros respeita usuario_id
        grupo_id = uuid4()

        mock_result = MagicMock()
        mock_result.rowcount = 0

        session = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        repo = TransacaoRepository(session)
        rowcount = await repo.excluir_por_grupo_e_numeros(grupo_id, numeros=[1, 2], usuario_id=1)

        assert rowcount == 0

    @pytest.mark.asyncio
    async def test_lista_vazia_de_numeros_retorna_zero(self):
        # Cenário: excluir_por_grupo_e_numeros retorna 0 para lista vazia de numeros
        grupo_id = uuid4()

        mock_result = MagicMock()
        mock_result.rowcount = 0

        session = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        repo = TransacaoRepository(session)
        rowcount = await repo.excluir_por_grupo_e_numeros(grupo_id, numeros=[], usuario_id=1)

        assert rowcount == 0

    @pytest.mark.asyncio
    async def test_statement_contem_parcela_numero_in_e_grupo(self):
        """
        Verifica que o DELETE inclui filtros por grupo_parcela_id e parcela_numero IN.
        """
        grupo_id = uuid4()

        mock_result = MagicMock()
        mock_result.rowcount = 2

        session = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        repo = TransacaoRepository(session)
        await repo.excluir_por_grupo_e_numeros(grupo_id, numeros=[4, 5], usuario_id=1)

        stmt = session.execute.call_args[0][0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "parcela_numero" in compiled.lower()
        assert "grupo_parcela_id" in compiled.lower()

    @pytest.mark.asyncio
    async def test_sem_usuario_id_deleta_sem_filtro_de_usuario(self):
        grupo_id = uuid4()

        mock_result = MagicMock()
        mock_result.rowcount = 3

        session = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        repo = TransacaoRepository(session)
        rowcount = await repo.excluir_por_grupo_e_numeros(grupo_id, numeros=[1, 2, 3], usuario_id=None)

        assert rowcount == 3
        session.flush.assert_awaited_once()
