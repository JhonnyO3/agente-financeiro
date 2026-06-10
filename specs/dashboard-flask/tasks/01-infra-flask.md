# Tarefa 01 — Infraestrutura Flask

**Stack:** python
**Dependências:** nenhuma
**Contratos:** `contracts/db-session.md`, `contracts/periodo.md`

---

## Objetivo

Criar a base do dashboard Flask: conexão ao banco, helper de período, factory da aplicação e registro de blueprints. Esta tarefa é a fundação; todas as outras dependem dela.

---

## Arquivos que esta tarefa possui

- `dashboard/__init__.py`
- `dashboard/db.py`
- `dashboard/periodo.py`
- `dashboard/app.py`
- `dashboard/blueprints/__init__.py`

---

## O que implementar

### `dashboard/db.py`
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
```

### `dashboard/periodo.py`
- Função `resolver_periodo(periodo: str) -> tuple[date, date]`
- Ver contrato `contracts/periodo.md` para mapeamento completo
- Fallback seguro: `periodo` inválido → `mes_atual`

### `dashboard/app.py`
- Flask factory `create_app() -> Flask`
- Registrar blueprints: `api_resumo`, `api_graficos`, `api_parcelas`, `api_transacoes`
- Rota `GET /` → renderiza `templates/index.html`
- Rota `GET /health` → retorna `{"ok": True}` (validação de startup)
- Servir arquivos estáticos de `dashboard/static/`

### `dashboard/__init__.py` e `dashboard/blueprints/__init__.py`
- Vazios ou com apenas `__all__` se necessário

---

## Dependência de instalação

```bash
uv add "flask[async]>=3.0"
```

Verificar que `pyproject.toml` foi atualizado.

---

## Critérios de aceite

- [ ] `uv run flask --app dashboard.app run --port 5000` sobe sem erro
- [ ] `GET /health` retorna 200 `{"ok": true}`
- [ ] `resolver_periodo("mes_atual")` retorna `(date(ano, mes, 1), date.today())`
- [ ] `resolver_periodo("tudo")` retorna `(date(2000, 1, 1), date.today())`
- [ ] `resolver_periodo("invalido")` não lança exceção, usa fallback

---

## Comando de verificação

```bash
uv run flask --app dashboard.app run --port 5000 &
curl http://localhost:5000/health
# Esperado: {"ok": true}
```
