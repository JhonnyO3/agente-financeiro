# Contrato: Schema de usuários e vínculo `usuario_id`

**Status:** Congelado
**Fronteira:** ORM/DB ↔ repository ↔ services ↔ agente ↔ script

## Tabela `usuarios`

| Coluna | Tipo | Constraints |
|---|---|---|
| `id` | INTEGER | PK, autoincrement |
| `nome` | TEXT | NOT NULL |
| `username` | TEXT | NOT NULL |
| `email` | TEXT | NOT NULL, **UNIQUE** (identificador de login) |
| `senha_hash` | TEXT | NOT NULL (bcrypt; nunca texto puro) |
| `telefone` | TEXT | NULL; **UNIQUE quando preenchido** (índice único parcial `WHERE telefone IS NOT NULL`) |
| `role` | TEXT | NOT NULL, default `'USER'` (ADMIN \| USER) |
| `ativo` | BOOLEAN | NOT NULL, default true |
| `criado_em` | TIMESTAMP | NOT NULL, server_default `now()` |

> `telefone` cobre o campo `whatsapp_numero` da spec (um único campo `telefone` com unicidade parcial).

## ORM `backend/models/usuario.py`

- Classe `Usuario(Base)` (mesma `Base` de `backend/models/transacao.py`), `__tablename__ = "usuarios"`.
- `role: Mapped[RoleEnum] = mapped_column(String, ...)`.
- `RoleEnum(str, Enum)` em `backend/models/enums.py`: `ADMIN = "ADMIN"`, `USER = "USER"`.

> A camada de dados vive em `backend/` (ver `reorg-agent.md`). O agente consome estes models/repositories
> in-process via `import backend.models` / `import backend.repositories`.

## FK em `transacoes`

- Nova coluna `transacoes.usuario_id INTEGER` → `usuarios.id`, **NOT NULL** (após backfill),
  `ForeignKey("usuarios.id", ondelete="CASCADE")`.
- ORM `Transacao`: `usuario_id: Mapped[int] = mapped_column(INTEGER, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)`.

## DTOs (T03)

- `TransacaoCreate` ganha `usuario_id: int` (**obrigatório**, sem default — força preenchimento explícito).
- `TransacaoUpdate` **não** ganha `usuario_id` (dono não muda por edição comum; troca de dono é operação admin dedicada, ver `admin-crud.md`).

## Estratégia de backfill (3 fases, ordem fixa)

1. **nullable:** `CREATE TABLE usuarios ...`; `ALTER TABLE transacoes ADD COLUMN usuario_id INTEGER NULL REFERENCES usuarios(id) ON DELETE CASCADE`.
2. **backfill:**
   - inserir usuário padrão se ausente: `INSERT INTO usuarios (nome, username, email, senha_hash, role, ativo) VALUES ('Jhonatas','jhonatas','jhonatas2004@gmail.com','!placeholder-sem-login!','ADMIN',true) ON CONFLICT (email) DO NOTHING;`
   - `UPDATE transacoes SET usuario_id = (SELECT id FROM usuarios WHERE email='jhonatas2004@gmail.com') WHERE usuario_id IS NULL;`
3. **not null:** `ALTER TABLE transacoes ALTER COLUMN usuario_id SET NOT NULL;`

> A migration **nunca** grava uma senha utilizável. O hash placeholder não autentica; a senha real do
> Jhonatas é definida por `scripts/criar_usuario.py` (idempotente por email — atualiza `senha_hash`).

## Critérios de aceitação

- Migration cria `usuarios` com `email` único e `role` (ADMIN/USER); duplicar email falha.
- `telefone` único quando preenchido; nulos múltiplos permitidos.
- Após a migration, nenhuma `transacoes.usuario_id` é nula; coluna é NOT NULL com CASCADE.
- `senha_hash` é a única coluna de senha; sem texto puro.
