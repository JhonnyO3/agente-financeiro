import httpx
from flask import Blueprint, Response, current_app, request

bp = Blueprint("api_proxy", __name__, url_prefix="/api")

_BACKEND_INDISPONIVEL = ({"erro": "backend indisponível"}, 502)


def _cliente():
    return current_app.config["BACKEND_CLIENT"]


def _repassar(resposta: httpx.Response):
    return Response(
        resposta.content,
        status=resposta.status_code,
        content_type=resposta.headers.get("content-type", "application/json"),
    )


@bp.get("/resumo")
def resumo():
    try:
        resposta = _cliente().resumo(dict(request.args))
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.get("/grafico/categorias")
def grafico_categorias():
    try:
        resposta = _cliente().grafico_categorias(dict(request.args))
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.get("/grafico/mensal")
def grafico_mensal():
    try:
        resposta = _cliente().grafico_mensal(dict(request.args))
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.get("/grafico/evolucao")
def grafico_evolucao():
    try:
        resposta = _cliente().grafico_evolucao(dict(request.args))
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.get("/parcelas-ativas")
def parcelas_ativas():
    try:
        resposta = _cliente().parcelas_ativas(dict(request.args))
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.delete("/grupos/<grupo>")
def excluir_grupo(grupo: str):
    try:
        resposta = _cliente().excluir_grupo(grupo)
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.get("/projecao")
def projecao():
    try:
        resposta = _cliente().projecao(dict(request.args))
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.get("/transacoes")
def listar_transacoes():
    try:
        resposta = _cliente().listar_transacoes(dict(request.args))
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.post("/transacoes")
def criar_transacao():
    try:
        resposta = _cliente().criar_transacao(request.get_json(silent=True) or {})
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.put("/transacoes/<int:id>")
def atualizar_transacao(id: int):
    try:
        resposta = _cliente().atualizar_transacao(
            id, request.get_json(silent=True) or {}
        )
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.delete("/transacoes/<int:id>")
def excluir_transacao(id: int):
    try:
        resposta = _cliente().excluir_transacao(id)
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.put("/grupos/<grupo>")
def atualizar_grupo(grupo: str):
    try:
        resposta = _cliente().atualizar_grupo(
            grupo, request.get_json(silent=True) or {}
        )
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.post("/grupos")
def criar_grupo():
    try:
        resposta = _cliente().criar_grupo(request.get_json(silent=True) or {})
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.get("/gastos-fixos")
def listar_gastos_fixos():
    try:
        resposta = _cliente().listar_gastos_fixos()
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.post("/gastos-fixos")
def criar_gasto_fixo():
    try:
        resposta = _cliente().criar_gasto_fixo(request.get_json(silent=True) or {})
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.put("/gastos-fixos/<int:id>")
def atualizar_gasto_fixo(id: int):
    try:
        resposta = _cliente().atualizar_gasto_fixo(
            id, request.get_json(silent=True) or {}
        )
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)


@bp.delete("/gastos-fixos/<int:id>")
def excluir_gasto_fixo(id: int):
    try:
        resposta = _cliente().excluir_gasto_fixo(id)
    except httpx.HTTPError:
        return _BACKEND_INDISPONIVEL
    return _repassar(resposta)
