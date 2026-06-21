"""
Wiring da nova arquitetura multi-usuário (Task E — costura final).

Invariante: EXATAMENTE 1 processo Uvicorn/Gunicorn deve executar este app.
A fila asyncio e o estado Redis são locais ao processo; múltiplos workers
divergiriam na fila in-process e teriam filas separadas por processo.
"""

import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent.agents_llm import Embedder, criar_llm
from agent.config import settings
from agent.entrypoint.consumer import Consumer
from agent.entrypoint.webhook import router as webhook_router
from agent.graph.builder import criar_grafo
from agent.integrations.evolution_client import EvolutionApiClient
from agent.services.classificador import Classificador
from agent.services.extrator import Extrator
from agent.services.formatador import Formatador
from agent.services.relogio import Relogio
from backend.repositories.transacao_repository import TransacaoRepository


# ---------------------------------------------------------------------------
# Adapter: envolve session_factory com usuario_id escopado por mensagem
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

    async def criar_lote(self, transacoes, usuario_id: int | None = None):
        async with self._session_factory.begin() as session:
            return await self._repo(session).criar_lote(transacoes)

    async def buscar_por_id(self, id):
        async with self._session_factory() as session:
            return await self._repo(session).buscar_por_id(
                id, usuario_id=self._usuario_id
            )

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

    async def atualizar(self, id, dados, usuario_id: int | None = None):
        uid = usuario_id if usuario_id is not None else self._usuario_id
        async with self._session_factory.begin() as session:
            return await self._repo(session).atualizar(id, dados, usuario_id=uid)

    async def excluir(self, id, usuario_id: int | None = None):
        uid = usuario_id if usuario_id is not None else self._usuario_id
        async with self._session_factory.begin() as session:
            return await self._repo(session).excluir(id, usuario_id=uid)

    async def excluir_grupo(self, grupo_parcela_id, usuario_id: int | None = None):
        uid = usuario_id if usuario_id is not None else self._usuario_id
        async with self._session_factory.begin() as session:
            return await self._repo(session).excluir_grupo(
                grupo_parcela_id, usuario_id=uid
            )

    async def excluir_por_filtros(
        self, inicio, fim, categoria=None, usuario_id: int | None = None, periodo=None
    ):
        uid = usuario_id if usuario_id is not None else self._usuario_id
        # periodo pode vir como kwarg dos testes de roteador
        if periodo is not None and inicio is None:
            inicio = periodo[0] if hasattr(periodo, "__getitem__") else periodo
        async with self._session_factory.begin() as session:
            return await self._repo(session).excluir_por_filtros(
                inicio, fim, categoria, usuario_id=uid
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

    async def buscar_nome_usuario(self) -> str:
        from backend.repositories.usuario_repository import UsuarioRepository
        async with self._session_factory() as session:
            usuario = await UsuarioRepository(session).buscar_por_id(self._usuario_id)
            return usuario.nome if usuario else ""


# ---------------------------------------------------------------------------
# Legado: resolver_usuario_id (não mais usado no lifespan — substituído por
# resolver_usuario_por_telefone in-process no webhook; mantido para não quebrar
# testes existentes que ainda a importam).
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
# Factory: repo escopado por mensagem
# ---------------------------------------------------------------------------


def _criar_repo_factory(session_factory) -> Callable[[int], _SessionFactoryRepository]:
    def factory(usuario_id: int) -> _SessionFactoryRepository:
        return _SessionFactoryRepository(session_factory, usuario_id)

    return factory


# ---------------------------------------------------------------------------
# Factory: roteador + tools montados por mensagem com o repo correto
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Lifespan: wiring completo (1 worker — invariante documentada acima)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Banco de dados
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Infraestrutura
    relogio = Relogio(settings.TIMEZONE_USUARIO)
    embedder = Embedder()

    # Redis (buffer de mensagens do debounce)
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    # Factories por mensagem
    repo_factory = _criar_repo_factory(session_factory)
    extrator = Extrator(llm=criar_llm())

    # Evolution API client
    evolution_client = EvolutionApiClient(
        base_url=settings.EVOLUTION_API_URL,
        instance=settings.EVOLUTION_INSTANCE,
        api_key=settings.EVOLUTION_API_KEY,
    )

    # Serviços
    formatador = Formatador()
    classificador = Classificador()

    # Grafo LangGraph (MemorySaver por padrão — substituir por RedisCheckpointer em prod)
    from langgraph.checkpoint.memory import MemorySaver
    grafo = criar_grafo(
        classificador=classificador,
        formatador=formatador,
        evolution=evolution_client,
        relogio=relogio,
        embedder=embedder,
        extrator=extrator,
        repo_factory=repo_factory,
        checkpointer=MemorySaver(),
    )

    # Fila asyncio (1 worker — invariante: não distribuída)
    fila: asyncio.Queue = asyncio.Queue()

    # Consumer da fila em background
    consumer = Consumer(
        fila=fila,
        graph=grafo,
        redis_client=redis_client,
        debounce_segundos=settings.DEBOUNCE_SEGUNDOS,
    )

    # Expõe em app.state
    app.state.fila = fila
    app.state.evolution_client = evolution_client
    app.state.session_factory = session_factory
    app.state.repo_factory = repo_factory

    consumer.iniciar()

    yield

    consumer.parar()
    await evolution_client.fechar()
    await redis_client.aclose()
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(webhook_router, prefix="/webhook")
