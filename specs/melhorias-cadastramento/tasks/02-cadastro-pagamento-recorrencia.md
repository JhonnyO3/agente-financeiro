# Tarefa 02 — Regras de pagamento, status/data, fim do PARCELAMENTOS e fluxo de recorrência

**Stack:** python
**Depende de:** 01
**Contratos:** `contracts/enums.md`, `contracts/schema-transacoes.md`

## Objetivo

Aplicar as regras de cadastro: forma de pagamento, status/data por forma, categoria real do
parcelado (fim do `PARCELAMENTOS`), valor por parcela e o novo fluxo de confirmação de recorrência
para `GASTOS_FIXOS`.

## Arquivos (posse exclusiva)

- `app/services/cadastrar.py`
- `app/services/parcelas.py`
- `app/services/confirmacao_state.py`
- `app/services/pipeline.py`
- `app/agents/extrator.py`

## Escopo

1. **Forma (RF-02):** `extrator.py` Literal → novos valores; default de aplicação `PIX` quando
   não informado. `cadastrar.py`: se `parcela_total > 1` ⇒ `CARTAO_CREDITO`.
2. **Status/data (RF-03):** PIX/`CARTAO_DEBITO` ⇒ `PAGO`, data real; `CARTAO_CREDITO`/`BOLETO`
   ⇒ `PENDENTE`, `data = adicionar_meses(data, 1)`. Usar `parcelas.py`.
3. **Fim do PARCELAMENTOS (RF-05):** remover o `if parcela_total > 1: categoria = PARCELAMENTOS`
   em `_processar`; categoria vem do categorizador (Tarefa 03 garante o Literal).
4. **Valor por parcela (RF-07):** validar `_valores_das_parcelas` (resto na última); manter.
5. **Recorrência (RF-06):** novo estado `AGUARDAR_RECORRENCIA` em `confirmacao_state.py`; quando o
   cadastro resultar em `GASTOS_FIXOS`, perguntar ao usuário; ramo novo em `pipeline._rotear_estado`
   que, no "sim", grava `recorrente=True`, `parcela_numero=parcela_total=1`.

## Critérios de aceite

- [ ] Mensagem sem forma → `PIX`; com parcelas → `CARTAO_CREDITO`
- [ ] PIX→PAGO/data real; CARTAO_CREDITO→PENDENTE/data+1 mês
- [ ] Cadastro parcelado não grava `PARCELAMENTOS`
- [ ] Classificar em `GASTOS_FIXOS` dispara pergunta; "sim" grava `recorrente=True` sem parcela
- [ ] Soma das parcelas == total

## Verificação local

```bash
uv run pytest tests/test_pipeline.py tests/ -v
```
