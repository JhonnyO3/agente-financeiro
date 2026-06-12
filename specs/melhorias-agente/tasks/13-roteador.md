# Tarefa 13 — Roteador (match + guarda de pendência)

**Stack:** python
**Depende de:** 06, 08, 09, 10, 11, 12
**Contrato:** `resultado-tools.md`, `estado-store.md`, `intencao-schema.md`

## Objetivo
Código Python puro que mapeia `Intencao` → Tool, com guarda de pendência e `confirmar` sem LLM.

## Arquivos (posse exclusiva)
- `agent/services/roteador.py`
- `tests/test_roteador.py`

## Escopo
1. `Roteador.rotear(intencao, estado, contexto) -> ResultadoTool`:
   - `confirmar/cancelar/selecionar/complementar` sem estado → `menu` (guarda).
   - Intenção operacional nova com pendência ativa → **cancela** pendência (`limpar_pendencia`) e processa a nova.
   - `confirmar` → persiste `payload_pendente` **sem LLM** (chama repository.criar_lote/atualizar/excluir conforme `acao_pendente`).
   - `selecionar` → resolve `opcoes`; `complementar` → completa `payload_pendente`/`campos_faltantes` (Python, sem re-extração).
   - `cadastrar/listar/atualizar/excluir/conversar` → Tool correspondente.
2. Após Tool com status pendente, grava estado (`payload_pendente`/`opcoes`/`campos_faltantes`/`acao_pendente`/`expira_em`).

## Critérios de aceite
- [ ] Intenção nova durante pendência cancela a pendência (sem "sim" forçado).
- [ ] `confirmar` persiste sem chamar LLM (mock de LLM não é invocado).
- [ ] `selecionar`/`complementar`/`confirmar`/`cancelar` sem estado → menu.

## Verificação
```bash
uv run pytest tests/test_roteador.py -v
```
