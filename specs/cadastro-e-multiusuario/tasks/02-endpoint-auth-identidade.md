# Tarefa B (02) — Endpoint GET /auth/identidade/por-telefone/{telefone}

**Stack:** python
**Depende de:** A
**Contratos:** `resolucao-identidade.md` (seção B), `usuario-repository.md`

## Objetivo

Endpoint REST de resolução de identidade por telefone sob **`/auth`** (não `/admin`), isolando as regras de identidade das de gestão. Reusa `buscar_por_telefone`. O webhook NÃO depende deste endpoint.

## Arquivos (posse exclusiva)

- `backend/controllers/auth.py` (adicionar rota; arquivo já tem o router `/auth`)
- `tests/test_auth_identidade.py`

## Escopo

1. Nova rota `@router.get("/identidade/por-telefone/{telefone}")` em `auth.py`.
2. Proteção: exige Bearer válido via `get_usuario_atual` (importar de `backend.auth.dependencies`). 401 sem token válido. **Não** usar `get_admin`.
3. Abre sessão (`_abrir_sessao`), chama `UsuarioRepository.buscar_por_telefone`.
4. Encontrado → `200` com `UsuarioResponse.de_modelo(u).model_dump()`. Não encontrado/inativo → `204` sem corpo.

## Critérios de aceite → teste

- [ ] Telefone de usuário ativo → 200 com corpo UsuarioResponse
- [ ] Telefone de usuário inativo → 204 sem corpo
- [ ] Telefone inexistente → 204 sem corpo
- [ ] Sem Authorization → 401
- [ ] Inativo e inexistente são indistinguíveis (ambos 204)

> Reusar o padrão de teste de `auth.py` (mock de sessionmaker em `app.state`, repo mockado).

## Verificação local

```bash
uv run pytest tests/test_auth_identidade.py -v
```
