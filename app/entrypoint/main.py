from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.entrypoint.webhook import router as webhook_router
from app.entrypoint.debounce import MessageDebouncer
from app.integrations.evolution_client import EvolutionApiClient
from app.repositories.transacao_repository import TransacaoRepository
from app.agents.embedder import Embedder
from app.agents.classificador import Classificador
from app.agents.extrator import Extrator
from app.agents.extrator_alteracao import ExtratorAlteracao
from app.agents.extrator_parcelas import ExtratorParcelas
from app.agents.categorizador import Categorizador
from app.agents.filtro_consulta import FiltroConsulta
from app.agents.confirmacao_chain import ConfirmacaoChain
from app.agents.extrator_exclusao_lote import ExtratorExclusaoLote
from app.agents.extrator_lista import ExtratorLista
from app.services.confirmacao_state import ConfirmacaoState
from app.services.cadastrar import CadastrarService
from app.services.alterar import AlterarService
from app.services.excluir import ExcluirService
from app.services.consultar import ConsultarService
from app.services.formatador import Formatador
from app.services.pipeline import Pipeline


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

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
