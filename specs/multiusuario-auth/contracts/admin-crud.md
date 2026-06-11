# Contrato: CRUD administrativo (só API)

**Status:** Congelado
**Fronteira:** controller/services admin ↔ guard `get_admin` ↔ repositories

Todas as rotas abaixo exigem `Depends(get_admin)` (role ADMIN + allowlist `ADMIN_EMAILS` + revalidação no
banco, ver `auth-jwt.md`). Negadas a USER → **403**. Sem tela no frontend (RF-09).

## Usuários — `/admin/usuarios`

| Rota | Método | Corpo / efeito |
|---|---|---|
| `/admin/usuarios` | GET | lista usuários `[{id,nome,username,email,telefone,role,ativo,criado_em}]` (sem `senha_hash`) |
| `/admin/usuarios/{id}` | GET | um usuário (sem `senha_hash`); 404 se não existe |
| `/admin/usuarios` | POST | `{nome,username,email,senha,telefone?,role?}` → cria (hash bcrypt); email duplicado → 409; 201 |
| `/admin/usuarios/{id}` | PUT | edição parcial: `nome,username,telefone,email,role,ativo` e `senha` (reset → novo hash); 404/409 |
| `/admin/usuarios/{id}` | DELETE | exclui usuário; **cascade** apaga as transações dele (FK ON DELETE CASCADE); 404 se não existe |

`senha_hash` nunca aparece em resposta. `role` ∈ {ADMIN, USER}. Reset de senha usa `hashing.hash_senha`.

## Transações de qualquer usuário — `/admin/transacoes`

O ADMIN informa o usuário-alvo; os services chamam o repository com `usuario_id` do alvo
(ou `None` quando a rota for cross-user explícita).

| Rota | Método | Efeito |
|---|---|---|
| `/admin/usuarios/{usuario_id}/transacoes` | GET | lista transações do alvo (mesmo shape de `/api/transacoes`) |
| `/admin/usuarios/{usuario_id}/transacoes` | POST | cria transação para o alvo (`TransacaoCreate.usuario_id = alvo`) |
| `/admin/transacoes/{id}` | GET | obtém qualquer transação (sem filtro de dono) |
| `/admin/transacoes/{id}` | PUT | edita qualquer transação |
| `/admin/transacoes/{id}` | DELETE | exclui qualquer transação |

## Services

- `admin_usuarios.{listar,obter,criar,atualizar,excluir}` (usa `UsuarioRepository`).
- `admin_transacoes.*` reusa o service/repository de transações com `usuario_id` explícito (ou `None`).

## Critérios de aceitação

- ADMIN cria/lista/edita/exclui usuários; trocar `role`/`ativo`; reset de senha gera novo hash.
- ADMIN lê/altera transações de outro usuário informando o alvo.
- Excluir usuário faz cascade nas transações (sem órfãos).
- Todas as rotas negadas a USER → 403; token ADMIN fora do allowlist → 403.
- Respostas de usuário nunca incluem `senha_hash`.
