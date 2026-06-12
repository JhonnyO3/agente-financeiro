# Tarefa 04 — Repository: múltiplos candidatos com distância (aditivo)

**Stack:** python
**Depende de:** 00
**Contrato:** `rag-busca.md`

## Objetivo
Adicionar método **aditivo** que devolve N candidatos com distância (corrige o `.first()`), sem quebrar o contrato existente. Única exceção permitida ao "backend intocado" (ver plan D2).

## Arquivos (posse exclusiva)
- `backend/repositories/transacao_repository.py`
- `agent/entrypoint/_adapter_repo.py`  # passthrough extraído do _SessionFactoryRepository
- `tests/test_repo_multiplos_candidatos.py`

> Nota anti-colisão: o passthrough sai para `_adapter_repo.py` (novo, posse desta task) para não colidir com T16, que edita `main.py`. T16 importa daqui.

## Escopo
1. `buscar_semantico_multiplos_com_distancia(embedding, limite=5, usuario_id=None) -> list[tuple[Transacao, float]]`, ordenado por distância L2 crescente, respeitando `limite` e filtro `usuario_id`.
2. **Não** alterar `buscar_semantico_com_distancia` (permanece `.first()`).
3. `_adapter_repo.py`: classe/adapter que envolve o repository com `usuario_id` fixo e expõe o método novo (mesmo padrão de `_SessionFactoryRepository`).

## Critérios de aceite
- [ ] Respeita `limite` e ordena por distância.
- [ ] Filtra por `usuario_id` quando fornecido.
- [ ] Assinaturas existentes inalteradas.

## Verificação
```bash
uv run pytest tests/test_repo_multiplos_candidatos.py -v
```
