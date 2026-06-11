from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from agent.config import settings
from agent.entrypoint.webhook import router as webhook_router
from agent.entrypoint.debounce import MessageDebouncer
from agent.integrations.evolution_client import EvolutionApiClient
from backend.repositories.transacao_repository import TransacaoRepository
from backend.repositories.usuario_repository import UsuarioRepository
from agent.agents.embedder import Embedder
from agent.agents.classificador import Classificador
from agent.agents.extrator import Extrator
from agent.agents.extrator_alteracao import ExtratorAlteracao
from agent.agents.extrator_parcelas import ExtratorParcelas
from agent.agents.categorizador import Categorizador
from agent.agents.filtro_consulta import FiltroConsulta
from agent.agents.confirmacao_chain import ConfirmacaoChain
from agent.agents.extrator_exclusao_lote import ExtratorExclusaoLote
from agent.agents.extrator_lista import ExtratorLista
from agent.services.confirmacao_state import ConfirmacaoState
from agent.services.cadastrar import CadastrarService
from agent.services.alterar import AlterarService
from agent.services.excluir import ExcluirService
from agent.services.marcar_pago import MarcarPagoService
from agent.services.consultar import ConsultarService
from agent.services.formatador import Formatador
from agent.services.pipeline import Pipeline


class _SessionFactoryRepository:
    def __init__(self, session_factory):
        self._session_factory = session_factory

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
            return await self._repo(session).buscar_por_id(id)

    async def buscar_por_grupo(self, grupo_parcela_id):
        async with self._session_factory() as session:
            return await self._repo(session).buscar_por_grupo(grupo_parcela_id)

    async def buscar_semantico(self, embedding, limite=5):
        async with self._session_factory() as session:
            return await self._repo(session).buscar_semantico(embedding, limite)

    async def buscar_semantico_com_distancia(self, embedding, limite=1):
        async with self._session_factory() as session:
            return await self._repo(session).buscar_semantico_com_distancia(embedding, limite)

    async def atualizar(self, id, dados):
        async with self._session_factory.begin() as session:
            return await self._repo(session).atualizar(id, dados)

    async def excluir(self, id):
        async with self._session_factory.begin() as session:
            return await self._repo(session).excluir(id)

    async def excluir_grupo(self, grupo_parcela_id):
        async with self._session_factory.begin() as session:
            return await self._repo(session).excluir_grupo(grupo_parcela_id)

    async def excluir_por_filtros(self, inicio, fim, categoria=None):
        async with self._session_factory.begin() as session:
            return await self._repo(session).excluir_por_filtros(inicio, fim, categoria)

    async def contar_por_filtros(self, inicio, fim, categoria=None):
        async with self._session_factory() as session:
            return await self._repo(session).contar_por_filtros(inicio, fim, categoria)

    async def listar_por_periodo(self, inicio, fim):
        async with self._session_factory() as session:
            return await self._repo(session).listar_por_periodo(inicio, fim)

    async def agregar_por_categoria(self, inicio, fim):
        async with self._session_factory() as session:
            return await self._repo(session).agregar_por_categoria(inicio, fim)


async def resolver_usuario_id(usuario_repository, email: str) -> int:
    usuario = await usuario_repository.buscar_por_email(email)
    if usuario is None:
        raise RuntimeError(
            f"Usuário dono do agente não encontrado para AGENTE_USUARIO_EMAIL={email!r}. "
            "Crie o usuário (scripts/criar_usuario.py) antes de iniciar o agente."
        )
    return usuario.id


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        usuario_id = await resolver_usuario_id(
            UsuarioRepository(session), settings.AGENTE_USUARIO_EMAIL
        )

    evolution_client = EvolutionApiClient(
        base_url=settings.EVOLUTION_API_URL,
        instance=settings.EVOLUTION_INSTANCE,
        api_key=settings.EVOLUTION_API_KEY,
    )

    embedder = Embedder()
    confirmacao_state = ConfirmacaoState()
    repository = _SessionFactoryRepository(session_factory)

    cadastrar = CadastrarService(
        repository=repository,
        embedder=embedder,
        extrator=Extrator(),
        categorizador=Categorizador(),
        confirmacao_state=confirmacao_state,
        usuario_id=usuario_id,
    )
    alterar = AlterarService(
        repository=repository,
        embedder=embedder,
        extrator_alteracao=ExtratorAlteracao(),
        confirmacao_state=confirmacao_state,
    )
    excluir = ExcluirService(
        repository=repository,
        embedder=embedder,
        confirmacao_state=confirmacao_state,
    )
    marcar_pago = MarcarPagoService(
        repository=repository,
        embedder=embedder,
        confirmacao_state=confirmacao_state,
    )
    consultar = ConsultarService(
        repository=repository,
        filtro_chain=FiltroConsulta(),
        embedder=embedder,
    )
    formatador = Formatador()
    pipeline = Pipeline(
        classificador=Classificador(),
        cadastrar=cadastrar,
        alterar=alterar,
        excluir=excluir,
        marcar_pago=marcar_pago,
        consultar=consultar,
        formatador=formatador,
        confirmacao_state=confirmacao_state,
        confirmacao_chain=ConfirmacaoChain(),
        extrator_parcelas=ExtratorParcelas(),
        extrator_exclusao_lote=ExtratorExclusaoLote(),
        extrator_lista=ExtratorLista(),
    )

    async def _processar_e_responder(numero: str, texto: str) -> None:
        import logging
        try:
            logging.info("processando numero=%s texto=%s", numero, texto)
            resposta = await pipeline.processar(numero, texto)
            logging.info("resposta gerada: %s", resposta)
            await evolution_client.enviar_mensagem(numero, resposta)
        except Exception as exc:
            logging.exception("erro ao processar mensagem: %s", exc)

    debouncer = MessageDebouncer()

    app.state.pipeline = pipeline
    app.state.evolution_client = evolution_client
    app.state.debouncer = debouncer
    app.state.processar_e_responder = _processar_e_responder

    yield

    await evolution_client.fechar()
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(webhook_router, prefix="/webhook")
