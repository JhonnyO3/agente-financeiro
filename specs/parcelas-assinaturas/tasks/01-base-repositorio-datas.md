# Tarefa 01 — Base: helpers de data, métodos de repositório, ajuste de listar_ativas

**Stack:** python
**Depende de:** —
**Contratos:** `contracts/datas-parcela.md`, `contracts/repositorio-grupos.md`

## Objetivo

Fornecer a base compartilhada por grupos e gastos fixos: helpers de data puros no backend
(sem importar `agent`), os métodos novos de repositório, e o ajuste de `listar_ativas` para
incluir pendentes vencidas (RF-01).

## Arquivos (posse exclusiva)

- `backend/services/datas_parcela.py` (novo)
- `backend/repositories/transacao_repository.py`
- `backend/services/parcelas.py`
- `tests/backend/test_datas_parcela.py` (novo)
- `tests/backend/test_repositorio_grupos.py` (novo)

## Escopo

1. **`datas_parcela.py`:** duplicar do agente as funções puras `adicionar_meses`,
   `status_por_data`, `datas_do_grupo` (assinaturas e semântica do contrato
   `datas-parcela`). Importa só `backend.models.enums`. **Não** importar de `agent`.
2. **Repositório (contrato `repositorio-grupos`):** adicionar
   `buscar_por_grupo_com_embedding` (undefer do embedding, ordenado por `parcela_numero`),
   `listar_recorrentes(usuario_id)` (filtro `recorrente == True`, ordenado por `data`),
   `excluir_por_grupo_e_numeros(grupo, numeros, usuario_id)` (delete `parcela_numero IN`,
   retorna rowcount, faz flush). Não alterar métodos existentes.
3. **`listar_ativas` (RF-01):** trocar o piso da janela de `date.today()` por um piso fixo
   no passado (`date(2000, 1, 1)`), mantendo `_DATA_TETO` e os filtros `parcela_total > 1`
   e "tem pendente". Grupos com pendente vencida passam a aparecer; grupos quitados não.

## Critérios de aceite

- [ ] `adicionar_meses(date(2026,1,31), 1) == date(2026,2,28)` e demais casos do contrato
- [ ] `status_por_data` PAGO para data passada, PENDENTE para hoje/futuro
- [ ] `datas_do_grupo(d, atual, total)` produz a cadeia com a atual ancorada em `d`
- [ ] `buscar_por_grupo_com_embedding` aplica `undefer(embedding)` e filtra por `usuario_id`
- [ ] `listar_recorrentes` filtra `recorrente == True` e isola por `usuario_id`
- [ ] `excluir_por_grupo_e_numeros` deleta só os `parcela_numero` da lista e retorna rowcount
- [ ] `listar_ativas` inclui grupo com pendente vencida; exclui grupo totalmente pago
- [ ] Testes vermelhos escritos antes (TDD), depois verdes; suíte existente intacta

## Verificação local

```bash
uv run pytest tests/backend/test_datas_parcela.py tests/backend/test_repositorio_grupos.py tests/backend/test_parcelas.py -v
```
