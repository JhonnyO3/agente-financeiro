# Contrato: Autenticação no frontend Flask

**Status:** Congelado
**Fronteira:** browser ↔ Flask (sessão) ↔ BackendClient ↔ backend `/auth/*` e `/api/*`

## Sessão

- `frontend/config.py` ganha `SECRET_KEY` (obrigatório, sem default — app não sobe se faltar).
- Cookie de sessão Flask assinado, `HttpOnly`, `SameSite=Lax`.
- Guarda na sessão: `session["access_token"]`, `session["refresh_token"]`, `session["role"]`, `session["email"]`.

## Rotas (`frontend/blueprints/auth.py`)

| Rota | Método | Efeito |
|---|---|---|
| `/login` | GET | renderiza modal/página de login (sem cadastro) |
| `/login` | POST | chama `POST /auth/login` do backend; sucesso → grava tokens na sessão, redireciona `/`; falha → re-renderiza com erro |
| `/logout` | POST (ou GET) | chama `POST /auth/logout` (best-effort com o refresh da sessão), `session.clear()`, redireciona `/login` |

## Proteção de rotas (`before_request`)

- Aplica-se às rotas do dashboard e ao proxy `/api/*`. **Isenta:** `/login`, `/logout`, estáticos, `/health`.
- Sem `access_token` na sessão → redireciona `/login` (HTML) ou 401 JSON (para `/api/*`).

## BackendClient (envio do Bearer + refresh)

- `BackendClient` passa a receber o `access_token` por chamada (lido da sessão pelo proxy/serviço) e
  injeta `Authorization: Bearer <access>` em toda requisição.
- Em resposta **401** do backend numa chamada de dados: o frontend tenta **uma vez** `POST /auth/refresh`
  com `session["refresh_token"]`:
  - sucesso → regrava `access_token` **e** `refresh_token` na sessão e refaz a chamada original;
  - falha → `session.clear()` e redireciona/responde login (sem laço — só 1 retry).

## Critérios de aceitação

- Dashboard sem login → modal/login.
- Login com credenciais do script → painel do usuário; chamadas levam o Bearer.
- 401 transitório com refresh válido → renova e continua transparente; refresh inválido → exige login.
- Logout encerra a sessão; painel volta a exigir login.
- Dashboard mostra só os dados do usuário logado. Sem modal de cadastro.
- `SECRET_KEY` ausente → falha de boot explícita.
