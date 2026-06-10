# Tarefa 04 — Marcar pago via WhatsApp

**Stack:** python · **Dependências:** 01
**Contratos:** `contracts/modelo-dados.md`

## Arquivos que esta tarefa possui
- `app/agents/classificador.py` · `prompts/intencao.md`
- `app/services/marcar_pago.py` (novo) · `app/services/pipeline.py`
- `app/entrypoint/main.py` (wiring) · `tests/test_pipeline.py` · `tests/test_marcar_pago.py` (novo)

## O que implementar
1. `IntencaoResult.intencao` ganha `"MARCAR_PAGO"`; `prompts/intencao.md` com exemplos
   ("paguei o jogo do batman", "quita a parcela do celular")
2. `MarcarPagoService` espelhando `AlterarService` (`app/services/alterar.py`):
   - `iniciar(mensagem, numero)`: embedder + `buscar_semantico_com_distancia` (>1.0 →
     não encontrado), salva `EstadoConfirmacao(acao="MARCAR_PAGO", transacao_id=...)`,
     retorna card + "Confirma marcar como PAGO? (sim/não)"
   - `confirmar(numero, confirmado)`: `atualizar(id, TransacaoUpdate(status=PAGO))`
3. Pipeline: rotear intenção `MARCAR_PAGO` → `iniciar`; estado `MARCAR_PAGO` →
   `confirmacao_chain` contexto `"sim_nao"` → `confirmar`
4. Wiring no lifespan de `main.py`; fixture `_make_pipeline` em `test_pipeline.py`
   ganha o novo dep

## Critérios de aceite
- [ ] "paguei X" → busca semântica, card de confirmação, estado salvo
- [ ] "sim" → `atualizar` com `status=PAGO`; "não" → cancela e limpa estado
- [ ] Distância > 1.0 → mensagem de não encontrado, sem estado
- [ ] Testes de pipeline existentes seguem verdes

## Verificação
`uv run pytest tests/test_pipeline.py tests/test_marcar_pago.py -v` e suíte completa.
