# STATUS — multiusuario-auth

| ID | Tarefa | Stack | Estado | Worktree/Branch | Nota |
|----|--------|-------|--------|-----------------|------|
| 01 | Separação de módulos: app/models+repositories → backend/, resto → agent/ (imports, alembic, start, pyproject, testes, docs) | python | doing | feat/multiusuario-auth | bloqueante |
| 02 | Schema usuarios + usuario_id (migration 3 fases) | python | todo | — | depende 01 |
| 03 | Repository com usuario_id + UsuarioRepository | python | todo | — | depende 02 |
| 04 | Auth backend (JWT, guard, hashing) | python | todo | — | depende 02 |
| 05 | Endpoints protegidos + filtro usuario_id | python | todo | — | depende 03,04 |
| 06 | Admin CRUD (usuários + transações de qualquer dono) | python | todo | — | depende 03,04 |
| 07 | Script criar_usuario.py | python | todo | — | depende 02 |
| 08 | Agente grava usuario_id | python | todo | — | depende 03 |
| 09 | Frontend auth (modal, sessão, Bearer, refresh, logout) | python | todo | — | depende 04 (contrato) |
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
