# Contrato: Endpoints de dados protegidos e filtrados por usuario_id

**Status:** Congelado
**Fronteira:** controllers/services do backend ↔ repository ↔ guard JWT

## Regra geral

Todos os endpoints de dados existentes ganham `usuario = Depends(get_usuario_atual)` e passam
`usuario.usuario_id` ao service. **O JSON de resposta permanece byte-idêntico ao atual** (mesmas chaves,
strings de dinheiro `"123.45"`, datas `"Jun/26"`). A única mudança observável: dados de outro usuário
não aparecem; 401 sem token válido.

## Rotas afetadas (path/método inalterados)

| Rota | Método | Mudança |
|---|---|---|
| `/api/resumo?periodo=` | GET | filtra por `usuario_id` |
| `/api/grafico/categorias?periodo=` | GET | filtra por `usuario_id` |
| `/api/grafico/mensal` | GET | filtra por `usuario_id` |
| `/api/grafico/evolucao` | GET | filtra por `usuario_id` |
| `/api/parcelas-ativas` | GET | filtra por `usuario_id` |
| `/api/grupos/{grupo}` | DELETE | só remove se o grupo pertencer ao `usuario_id`; senão **404** (não vaza existência) |
| `/api/projecao` | GET | filtra por `usuario_id` |
| `/api/transacoes` | GET | lista só do `usuario_id` |
| `/api/transacoes` | POST | cria com `usuario_id` do token (ignora qualquer `usuario_id` no body) |
| `/api/transacoes/{id}` | PUT | edita só se a transação for do `usuario_id`; senão **404** |
| `/api/transacoes/{id}` | DELETE | exclui só se for do `usuario_id`; senão **404** |
| `/health` | GET | permanece **público** |

> Acesso a `id`/`grupo` alheio retorna **404** (não 403) para não vazar existência ao USER (RF-08).

## Assinaturas (services do backend recebem `usuario_id`)

- `transacoes.listar(session, usuario_id, periodo, tipo, ...)`
- `transacoes.criar(session, usuario_id, body)` — injeta `usuario_id` no `TransacaoCreate`, ignora body.
- `transacoes.atualizar(session, usuario_id, id, body)` — 404 se não-dono.
- `transacoes.excluir(session, usuario_id, id)` — 404 se não-dono.
- `resumo.calcular_resumo(session, usuario_id, periodo)`, `resumo.categorias_gasto(session, usuario_id, periodo)`
- `parcelas.listar_ativas(session, usuario_id)`, `parcelas.excluir_grupo(session, usuario_id, grupo)`
- `graficos.*`, `projecao.*` recebem `usuario_id`.

## Assinaturas (repository — `backend/repositories/transacao_repository.py`)

Métodos de leitura/escrita/agregação ganham `usuario_id: int | None` (param `None` ⇒ sem filtro,
para ADMIN-master em `admin-crud.md`):
`listar_por_periodo`, `agregar_por_categoria`, `buscar_por_id`, `buscar_por_grupo`, `atualizar`,
`excluir`, `excluir_grupo`, `excluir_por_filtros`, `contar_por_filtros`, `listar_*`. `criar`/`criar_lote`
recebem `usuario_id` via `TransacaoCreate` (já obrigatório por `schema-usuarios.md`).

## Critérios de aceitação

- Endpoint sem Bearer válido → 401.
- Dois usuários distintos veem apenas as próprias transações no mesmo endpoint (shape JSON idêntico).
- PUT/DELETE/`grupos` de id alheio → 404.
- POST ignora `usuario_id` do body e usa o do token.
