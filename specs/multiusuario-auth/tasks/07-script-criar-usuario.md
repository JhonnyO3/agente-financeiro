# Tarefa 07 — Script criar_usuario.py

**Stack:** python
**Depende de:** 02
**Contrato:** `schema-usuarios.md`, `auth-jwt.md` (reusa `hashing`)

## Objetivo
CLI que cria/atualiza usuário com senha bcrypt (idempotente por email), incluindo o admin padrão.

## Arquivos (posse exclusiva)
- `scripts/criar_usuario.py`
- `tests/test_criar_usuario.py`

## Escopo
1. Args: `nome`, `username`, `email`, `senha`, `telefone?`, `role` (default USER).
2. Hash bcrypt reusando `backend.auth.hashing`; persiste via `backend.repositories.UsuarioRepository`.
3. Email duplicado → atualiza `senha_hash`/dados (idempotente) com mensagem clara; saída informa credenciais.
4. Permite `role=ADMIN` (Jhonatas).

## Critérios de aceite
- [ ] Cria usuário com senha bcrypt; `role=ADMIN` possível.
- [ ] Email existente → mensagem clara (idempotente), senha não recuperável.

## Verificação
```bash
uv run pytest tests/test_criar_usuario.py -v
```
