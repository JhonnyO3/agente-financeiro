# Tarefa 02 — Grupos de parcelas: service e controller (editar + criar)

**Stack:** python
**Depende de:** 01
**Contratos:** `contracts/api-grupos.md`, `contracts/repositorio-grupos.md`, `contracts/datas-parcela.md`

## Objetivo

Implementar `PUT /api/grupos/{grupo_parcela_id}` (editar, RF-01) e `POST /api/grupos`
(criar, RF-02), com atomicidade pela sessão `get_session_begin` e reuso dos helpers de data
e métodos de repositório da T01.

## Arquivos (posse exclusiva)

- `backend/services/grupos.py` (novo)
- `backend/controllers/grupos.py` (novo)
- `backend/main.py`
- `tests/backend/test_grupos.py` (novo)

## Escopo

1. **Service `editar_grupo` (RF-01):** validar body (`descricao`, `valor_parcela`,
   `proxima_data`, `parcela_atual`, `parcela_total`); ID malformado → `IdInvalidoError`;
   `valor_parcela <= 0`, `parcela_total < parcela_atual`, `parcela_total < 1` →
   `ValidacaoError`. Carregar grupo com `buscar_por_grupo_com_embedding`; vazio →
   `GrupoNaoEncontradoError`. Aplicar título (todas), `parcela_total` (todas), status por
   `parcela_atual`, `valor_parcela` (só PENDENTE), datas das PENDENTE via cadeia mensal a
   partir de `proxima_data`. Aumentar total → `criar_lote` (embedding/categoria/forma/
   responsável copiados, datas contínuas, PENDENTE). Diminuir → `excluir_por_grupo_e_numeros`.
   Mutação dos objetos ORM na sessão transacional (sem estender `TransacaoUpdate`).
2. **Service `criar_grupo` (RF-02):** validar (`parcela_total >= 2`, `valor_parcela > 0`,
   `1 <= parcela_atual <= parcela_total`, campos obrigatórios). `uuid4()`, `criar_lote` com
   `valor_parcela` em todas, `tipo=GASTO`, `recorrente=False`, `embedding=None`, datas via
   `datas_do_grupo`, status por `parcela_atual`. Defaults: categoria `COMPRAS`,
   forma `CARTAO_CREDITO`, responsável `"Jhonatas"`.
3. **Controller `grupos.py`:** `router = APIRouter(prefix="/api")`; `PUT /grupos/{id}`
   (`get_session_begin`), `POST /grupos` (`get_session_begin`, 201); mapear
   `IdInvalidoError`/`ValidacaoError` → 400, `GrupoNaoEncontradoError` → 404.
4. **Registro:** acrescentar `"grupos"` à lista `CONTROLLERS` em `backend/main.py`.

## Critérios de aceite

- [ ] Editar título altera `descricao` de todas as linhas
- [ ] Editar valor altera só as PENDENTE; pagas intactas
- [ ] Editar data move a próxima pendente e recalcula as seguintes mês a mês; pagas intactas
- [ ] `parcela_atual = N` marca 1..N-1 PAGO e N..total PENDENTE
- [ ] Aumentar total cria linhas com mesmo `grupo_parcela_id`, embedding copiado, datas contínuas
- [ ] Diminuir total remove linhas finais e atualiza `parcela_total` das restantes
- [ ] `parcela_total < parcela_atual` ou `< 1` → 400; `valor_parcela <= 0` → 400; ID malformado → 400; grupo de outro usuário → 404
- [ ] Criar 12x R$100 → 12 linhas mesmo grupo, valor 100.00; `parcela_atual=4` → 1-3 PAGO, 4-12 PENDENTE
- [ ] `POST` com `parcela_total < 2`, `valor <= 0` ou campo faltando → 400 (201 no sucesso)
- [ ] Testes vermelhos antes (TDD), depois verdes; repositório mockado com `AsyncMock`/`SimpleNamespace`, `dependency_overrides`

## Verificação local

```bash
uv run pytest tests/backend/test_grupos.py -v
```
