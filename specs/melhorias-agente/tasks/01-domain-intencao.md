# Tarefa 01 — Domínio: Intencao + ParametrosPorAcao + ResultadoTool

**Stack:** python
**Depende de:** 00
**Contrato:** `intencao-schema.md`, `resultado-tools.md`

## Objetivo
Criar os modelos de domínio compartilhados: a `Intencao` (union discriminada) e o `ResultadoTool`.

## Arquivos (posse exclusiva)
- `agent/domain/__init__.py`
- `agent/domain/intencao.py`
- `agent/domain/resultado.py`
- `tests/test_domain_intencao.py`

## Escopo
1. `intencao.py`: `Acao`, `Intencao`, `ItemCadastro`, `ParamsCadastrar/Listar/Atualizar/Excluir/Selecionar/Complementar/Vazio`, `ParametrosPorAcao` exatamente como no contrato `intencao-schema.md`.
2. `resultado.py`: `ResultadoTool` (acao/status/dados) conforme `resultado-tools.md`.
3. Valores monetários como `Decimal`; union discriminada por `acao`.

## Critérios de aceite
- [ ] Reproduz os 17 exemplos de `classificador.md` como instâncias válidas de `Intencao`.
- [ ] Parâmetros do tipo errado para uma `acao` falham validação.
- [ ] `ResultadoTool` aceita todos os pares (acao, status) do contrato.

## Verificação
```bash
uv run pytest tests/test_domain_intencao.py -v
```
