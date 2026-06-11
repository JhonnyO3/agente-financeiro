# STATUS — multiusuario-auth

| ID | Tarefa | Stack | Estado | Worktree/Branch | Nota |
|----|--------|-------|--------|-----------------|------|
| 01 | Separação de módulos: app/models+repositories → backend/, resto → agent/ (imports, alembic, start, pyproject, testes, docs) | python | done | feat/multiusuario-auth | commit 539dcfa (213 testes) |
| 02 | Schema usuarios + usuario_id (migration 3 fases) | python | done | feat/multiusuario-auth | commit 1bbab5b (238 testes) |
| 03 | Repository com usuario_id + UsuarioRepository | python | done | feat/multiusuario-auth | merge batch3 (TransacaoCreate.usuario_id obrigatório) |
| 04 | Auth backend (JWT, guard, hashing) | python | done | feat/multiusuario-auth | merge batch3 (bcrypt pin <4.1) |
| 05 | Endpoints protegidos + filtro usuario_id | python | doing | sq/05 | worktree t05; corrige test_transacoes |
| 06 | Admin CRUD (usuários + transações de qualquer dono) | python | doing | sq/06 | worktree t06 |
| 07 | Script criar_usuario.py | python | doing | sq/07 | worktree t07 |
| 08 | Agente grava usuario_id | python | doing | sq/08 | worktree t08; corrige test_service_cadastrar |
| 09 | Frontend auth (modal, sessão, Bearer, refresh, logout) | python | done | feat/multiusuario-auth | merge batch3 |
| 10 | Config final + start.py + .env.example + docs | python | todo | — | depende 05,06,07,08,09 |

Contratos: `reorg-agent.md`, `schema-usuarios.md`, `auth-jwt.md`, `api-endpoints-protegidos.md`,
`admin-crud.md`, `frontend-auth.md` — **todos Congelados**.

DAG:
```
contratos → 01 → 02 → { 03, 04, 07 }
03 → 08
{03,04} → 05
{03,04} → 06
04(contrato) → 09   (paralelo; só toca frontend/)
{05,06,07,08,09} → 10
```
Anti-colisão: T05 (controllers de dados) e T06 (admin.py) não compartilham arquivos; a entrada `"admin"`
na lista `CONTROLLERS` de `backend/main.py` é adicionada por T04 (junto com `"auth"`) para evitar dois
escritores em `main.py`.
