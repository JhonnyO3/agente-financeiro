# Tarefa F (06) — Tela de cadastro de usuário (Flask)

**Stack:** python (Flask)
**Depende de:** contratos congelados
**Contratos:** `tela-cadastro.md`

## Objetivo

Tela no dashboard Flask para admin cadastrar usuário (nome, e-mail, telefone, senha), derivando `username` do e-mail e chamando `POST /admin/usuarios` via `BackendClient`. Totalmente independente do agente.

## Arquivos (posse exclusiva)

- `frontend/blueprints/admin_usuarios.py` (novo blueprint)
- `frontend/templates/admin/usuarios_novo.html` (novo template)
- `frontend/services/backend_client.py` (adicionar método `criar_usuario`)
- `frontend/app.py` (registrar o blueprint)
- `tests/test_frontend_cadastro.py`

## Escopo

1. Blueprint com `GET /admin/usuarios/novo` (form) e `POST /admin/usuarios/novo` (submit).
2. Guard de admin: `session.get("role") == "ADMIN"`; senão redirect para login.
3. POST: validar campos obrigatórios (nome, email com `@`, telefone só dígitos 10–15, senha), derivar `username = email.split("@")[0]`, montar body e chamar `BackendClient.criar_usuario`.
4. `criar_usuario(self, body)` em `backend_client.py` → `self._autenticado("POST", "/admin/usuarios", json=body)`.
5. Tratamento: 201 → flash sucesso + **redirect para o dashboard** (decisão do usuário: NÃO criar tela de lista de usuários — fora de escopo); 409 → erro "e-mail já cadastrado" preservando campos (menos senha); 422 → "dados inválidos"; erro httpx → "Backend indisponível.".
6. Registrar o blueprint em `create_app`. Garantir que `/admin/usuarios/novo` não vaze a usuário não-admin.

## Critérios de aceite → teste

- [ ] GET `/admin/usuarios/novo` como admin → 200 com formulário
- [ ] Não-admin acessando → redirect para login
- [ ] POST válido → chama `criar_usuario` com username derivado e telefone só-dígitos; backend 201 → redirect/sucesso
- [ ] Backend 409 → re-renderiza com erro de e-mail duplicado preservando nome/telefone (senha não)
- [ ] Validação client/handler: e-mail sem `@` ou telefone não numérico → erro sem chamar backend
- [ ] `username` enviado = parte antes do `@`

> Usar `app.test_client()` do Flask, mock do `BackendClient` (respostas httpx fake), sessão com role.

## Verificação local

```bash
uv run pytest tests/test_frontend_cadastro.py -v
```
