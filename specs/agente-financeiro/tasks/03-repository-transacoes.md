# Tarefa 03 — TransacaoRepository

**Stack:** python  
**Depende de:** 02-modelos-db  
**Arquivos próprios:** `app/repositories/transacao_repository.py`, `app/repositories/database.py`

## Objetivo

Implementar a camada de acesso ao banco, expondo exatamente a interface do contrato.

## Contrato de referência

`contracts/transacao-repository.md` — interface completa com DTOs.

## Entregáveis

### `app/repositories/database.py`

Engine async SQLAlchemy + `get_session` como dependency FastAPI.

### `app/repositories/transacao_repository.py`

Implementar todos os métodos do contrato:

| Método               | Detalhe de implementação                                                        |
|----------------------|---------------------------------------------------------------------------------|
| `criar`              | Insert + flush + refresh                                                        |
| `criar_lote`         | `session.add_all(lista)` em única transação                                     |
| `buscar_por_id`      | `SELECT WHERE id = ?`                                                           |
| `buscar_por_grupo`   | `SELECT WHERE grupo_parcela_id = ? ORDER BY parcela_numero`                     |
| `buscar_semantico`   | `ORDER BY embedding <-> :vetor LIMIT :limite` via pgvector                      |
| `atualizar`          | `UPDATE SET ... WHERE id = ?`; apenas campos não-None do DTO                   |
| `excluir`            | `DELETE WHERE id = ?` (hard delete)                                             |
| `excluir_grupo`      | `DELETE WHERE grupo_parcela_id = ?`; retorna rowcount                           |
| `listar_por_periodo` | `SELECT WHERE data BETWEEN inicio AND fim ORDER BY data`                        |
| `agregar_por_categoria` | `SELECT categoria, SUM(valor), COUNT(*) GROUP BY categoria`                  |

## Critério de aceite

- [ ] `criar` + `buscar_por_id` retorna o mesmo objeto
- [ ] `criar_lote` com 6 itens → 6 registros no banco com mesmo `grupo_parcela_id`
- [ ] `buscar_semantico` retorna resultado com menor distância primeiro
- [ ] `excluir_grupo` remove todos os registros do grupo e retorna contagem correta
- [ ] `agregar_por_categoria` retorna `Decimal` nos totais (não float)
