"""
Wiring da nova arquitetura (Task 16).

Invariante: EXATAMENTE 1 processo Uvicorn/Gunicorn deve executar este app.
A fila asyncio e o estado Redis são locais ao processo; múltiplos workers
divergiriam na fila in-process e teriam filas separadas por processo.
"""

import asyncio
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent.agents_llm import Embedder
from agent.config import settings
from agent.entrypoint.webhook import router as webhook_router
from agent.entrypoint.worker import Worker
from agent.integrations.evolution_client import EvolutionApiClient
from agent.services.classificador import Classificador
from agent.services.estado_store import EstadoStoreRedis
from agent.services.formatador import Formatador
from agent.services.rag import BuscaRAG
from agent.services.relogio import Relogio
from agent.services.roteador import Roteador
from agent.tools.atualizar import ToolAtualizar
from agent.tools.cadastrar import ToolCadastrar
from agent.tools.conversar import ToolConversar
from agent.tools.excluir import ToolExcluir
from agent.tools.listar import ToolListar
from backend.repositories.transacao_repository import TransacaoRepository
from backend.repositories.usuario_repository import UsuarioRepository


# ---------------------------------------------------------------------------
# Adapter: envolve session_factory com usuario_id fixo para o repo de transações
# ---------------------------------------------------------------------------

class _SessionFactoryRepository:
    def __init__(self, session_factory, usuario_id: int) -> None:
        self._session_factory = session_factory
        self._usuario_id = usuario_id

    def _repo(self, session):
        return TransacaoRepository(session)

    async def criar(self, transacao):
        async with self._session_factory.begin() as session:
            return await self._repo(session).criar(transacao)

    async def criar_lote(self, transacoes):
        async with self._session_factory.begin() as session:
            return await self._repo(session).criar_lote(transacoes)

    async def buscar_por_id(self, id):
        async with self._session_factory() as session:
            return await self._repo(session).buscar_por_id(id, usuario_id=self._usuario_id)

    async def buscar_por_grupo(self, grupo_parcela_id):
        async with self._session_factory() as session:
            return await self._repo(session).buscar_por_grupo(
                grupo_parcela_id, usuario_id=self._usuario_id
            )

    async def buscar_semantico(self, embedding, limite=5):
        async with self._session_factory() as session:
            return await self._repo(session).buscar_semantico(
                embedding, limite, usuario_id=self._usuario_id
            )

    async def buscar_semantico_com_distancia(self, embedding, limite=1):
        async with self._session_factory() as session:
            return await self._repo(session).buscar_semantico_com_distancia(
                embedding, limite, usuario_id=self._usuario_id
            )

    async def buscar_semantico_multiplos_com_distancia(self, embedding, limite=5):
        async with self._session_factory() as session:
            return await self._repo(session).buscar_semantico_multiplos_com_distancia(
                embedding, limite=limite, usuario_id=self._usuario_id
            )

    async def atualizar(self, id, dados):
        async with self._session_factory.begin() as session:
            return await self._repo(session).atualizar(id, dados, usuario_id=self._usuario_id)

    async def excluir(self, id):
        async with self._session_factory.begin() as session:
            return await self._repo(session).excluir(id, usuario_id=self._usuario_id)

    async def excluir_grupo(self, grupo_parcela_id):
        async with self._session_factory.begin() as session:
            return await self._repo(session).excluir_grupo(
                grupo_parcela_id, usuario_id=self._usuario_id
            )

    async def excluir_por_filtros(self, inicio, fim, categoria=None):
        async with self._session_factory.begin() as session:
            return await self._repo(session).excluir_por_filtros(
                inicio, fim, categoria, usuario_id=self._usuario_id
            )

    async def contar_por_filtros(self, inicio, fim, categoria=None):
        async with self._session_factory() as session:
            return await self._repo(session).contar_por_filtros(
                inicio, fim, categoria, usuario_id=self._usuario_id
            )

    async def listar_por_periodo(self, inicio, fim):
        async with self._session_factory() as session:
            return await self._repo(session).listar_por_periodo(
                inicio, fim, usuario_id=self._usuario_id
            )

    async def listar_por_periodo_com_embedding(self, inicio, fim):
        async with self._session_factory() as session:
            return await self._repo(session).listar_por_periodo_com_embedding(
                inicio, fim, usuario_id=self._usuario_id
            )

    async def agregar_por_categoria(self, inicio, fim):
        async with self._session_factory() as session:
            return await self._repo(session).agregar_por_categoria(
                inicio, fim, usuario_id=self._usuario_id
            )


# ---------------------------------------------------------------------------
# Fail-fast: resolve usuario_id pelo email ou levanta RuntimeError
# ---------------------------------------------------------------------------

async def resolver_usuario_id(usuario_repository, email: str) -> int:
    usuario = await usuario_repository.buscar_por_email(email)
    if usuario is None:
        raise RuntimeError(
            f"Usuário dono do agente não encontrado para AGENTE_USUARIO_EMAIL={email!r}. "
            "Crie o usuário (scripts/criar_usuario.py) antes de iniciar o agente."
        )
    return usuario.id


# ---------------------------------------------------------------------------
# Lifespan: wiring completo (1 worker — invariante documentada acima)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Banco de dados
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        usuario_id = await resolver_usuario_id(
            UsuarioRepository(session), settings.AGENTE_USUARIO_EMAIL
        )

    # Repository com usuario_id fixo
    repository = _SessionFactoryRepository(session_factory, usuario_id)

    # Infraestrutura
    relogio = Relogio(settings.TIMEZONE_USUARIO)
    embedder = Embedder()

    # Redis + EstadoStore de produção
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    estado_store = EstadoStoreRedis(redis_client)

    # RAG
    rag = BuscaRAG(embedder=embedder, adapter=repository)

    # 5 Tools
    tool_cadastrar = ToolCadastrar(relogio=relogio, repository=repository)
    tool_listar = ToolListar(repo=repository, relogio=relogio, usuario_id=usuario_id)
    tool_atualizar = ToolAtualizar(rag=rag, repository=repository, relogio=relogio)
    tool_excluir = ToolExcluir(rag=rag, repository=repository, relogio=relogio)
    tool_conversar = ToolConversar()

    # Serviços
    formatador = Formatador()
    classificador = Classificador()
    roteador = Roteador(
        tool_cadastrar=tool_cadastrar,
        tool_listar=tool_listar,
        tool_atualizar=tool_atualizar,
        tool_excluir=tool_excluir,
        tool_conversar=tool_conversar,
        estado_store=estado_store,
        repository=repository,
    )

    # Evolution API client
    evolution_client = EvolutionApiClient(
        base_url=settings.EVOLUTION_API_URL,
        instance=settings.EVOLUTION_INSTANCE,
        api_key=settings.EVOLUTION_API_KEY,
    )

    # Fila asyncio (1 worker — invariante: não distribuída)
    fila: asyncio.Queue = asyncio.Queue()

    # Worker
    worker = Worker(
        classificador=classificador,
        roteador=roteador,
        formatador=formatador,
        evolution_client=evolution_client,
        estado_store=estado_store,
        debounce_segundos=settings.DEBOUNCE_SEGUNDOS,
    )

    # Expõe em app.state conforme webhook.py e worker.py esperam
    app.state.fila = fila
    app.state.worker = worker
    app.state.estado_store = estado_store
    app.state.evolution_client = evolution_client
    app.state.usuario_id = usuario_id

    # Loop de consumo da fila em background
    async def _consumidor():
        while True:
            numero, texto = await fila.get()
            await worker.receber(numero, texto)
            asyncio.create_task(worker.processar_pendentes())
            fila.task_done()

    task_consumidor = asyncio.create_task(_consumidor())

    yield

    task_consumidor.cancel()
    await evolution_client.fechar()
    await redis_client.aclose()
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(webhook_router, prefix="/webhook")
