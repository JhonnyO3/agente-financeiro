# Contrato: Autenticação JWT (backend)

**Status:** Congelado
**Fronteira:** frontend ↔ backend (rotas `/auth/*`) e guard ↔ controllers de dados/admin

## Tokens (HS256, segredo `JWT_SECRET`)

**Access token** (curta duração, `JWT_ACCESS_EXPIRES_MIN`):
```json
{ "sub": "<usuario_id>", "role": "ADMIN|USER", "email": "<email>", "type": "access", "exp": 0 }
```
**Refresh token** (longa duração, `JWT_REFRESH_EXPIRES_DAYS`):
```json
{ "sub": "<usuario_id>", "type": "refresh", "jti": "<uuid>", "exp": 0 }
```
- `sub` é string (id). `role`/`email` viajam só no access. Decisão sempre vem do token validado no
  servidor, nunca de parâmetro do cliente.
- Refresh rotation: a cada `/auth/refresh` emite-se novo refresh (novo `jti`) e invalida-se o anterior.
  `refresh_store` (in-memory keyed por `jti`, TTL = exp) registra refresh ativos; logout revoga o `jti`.

## Rotas

### `POST /auth/login`
Request: `{ "email": "...", "senha": "..." }`
- valida contra `usuarios` (bcrypt, `ativo=true`).
- 200: `{ "access_token": "...", "refresh_token": "...", "token_type": "bearer", "role": "USER|ADMIN" }`
- 401: `{ "erro": "credenciais inválidas" }` (email inexistente, senha errada ou usuário inativo — mensagem
  genérica, não vaza qual falhou).

### `POST /auth/refresh`
Request: `{ "refresh_token": "..." }`
- valida assinatura/exp/type=refresh e `jti` ativo no store.
- 200: `{ "access_token": "...", "refresh_token": "...", "token_type": "bearer" }` (rotaciona refresh).
- 401: `{ "erro": "refresh inválido" }`.

### `POST /auth/logout`
Request: `{ "refresh_token": "..." }`
- revoga o `jti` no store. 200: `{ "ok": true }`. Idempotente (refresh já inválido também retorna 200).

## Dependências (Depends)

### `get_usuario_atual(request) -> UsuarioToken`
- lê `Authorization: Bearer <access>`; decodifica HS256, valida exp/type=access.
- ausente / malformado / expirado / assinatura inválida → **401** `{ "erro": "não autenticado" }`.
- retorna `UsuarioToken(usuario_id: int, role: str, email: str)`.

### `get_admin(usuario = Depends(get_usuario_atual)) -> UsuarioToken`
Check extra (RF-08), todos obrigatórios, falha em qualquer → **403** `{ "erro": "acesso negado" }`:
1. `usuario.role == "ADMIN"` (do token validado);
2. `usuario.email in ADMIN_EMAILS` (allowlist do `.env`);
3. revalidação no banco: existe `usuarios` com esse id, `role == ADMIN` **e** `ativo == true`.

## Config (backend, `pydantic-settings`, obrigatórios)

`JWT_SECRET` (sem default — app não sobe se faltar), `JWT_ACCESS_EXPIRES_MIN` (int),
`JWT_REFRESH_EXPIRES_DAYS` (int), `ADMIN_EMAILS` (CSV → set de emails).

## Hashing (`backend/auth/hashing.py`)

`hash_senha(s) -> str` e `verificar_senha(s, hash) -> bool` via bcrypt (passlib[bcrypt] ou bcrypt).
Mesmo módulo reutilizado pelo `scripts/criar_usuario.py` e pelo admin CRUD (reset de senha).

## Critérios de aceitação

- login válido → access+refresh; inválido/inativo → 401 genérico.
- refresh válido → novo access (e novo refresh); refresh revogado/expirado → 401.
- logout revoga o refresh; novo refresh com mesmo `jti` → 401.
- endpoint protegido sem Bearer válido → 401.
- `get_admin`: role≠ADMIN, ou email fora do allowlist, ou banco inativo/não-ADMIN → 403.
- `JWT_SECRET` ausente → falha de boot explícita.
