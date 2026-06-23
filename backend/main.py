import importlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.auth.dependencies import instalar_handlers
from backend.auth.refresh_store import RefreshStore
from backend.config import settings
from backend.db import criar_engine, criar_sessionmaker

logger = logging.getLogger(__name__)

CONTROLLERS = [
    "transacoes",
    "resumo",
    "parcelas",
    "graficos",
    "projecao",
    "auth",
    "admin",
]


def _registrar_controllers(app: FastAPI) -> None:
    for nome in CONTROLLERS:
        try:
            modulo = importlib.import_module(f"backend.controllers.{nome}")
        except ImportError:
            continue
        app.include_router(modulo.router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Backend startup: gargalo anterior era reconexao por request via NullPool "
        "(engine-por-request, ~2.8s de handshake medidos, contorno do loop-por-request "
        "do asgiref no Flask). Correcao: AsyncEngine pooled (QueuePool) criado uma vez e "
        "reusado no event loop unico e persistente do uvicorn (~0.4s)."
    )
    engine = criar_engine(settings.DATABASE_URL)
    app.state.engine = engine
    app.state.sessionmaker = criar_sessionmaker(engine)
    app.state.refresh_store = RefreshStore()
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

instalar_handlers(app)
_registrar_controllers(app)


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}
