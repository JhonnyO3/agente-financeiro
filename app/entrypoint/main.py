from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.entrypoint.webhook import router as webhook_router
from app.entrypoint.debounce import MessageDebouncer

debouncer = MessageDebouncer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(webhook_router, prefix="/webhook")
