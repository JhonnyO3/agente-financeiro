# Tarefa 08 — Tool Cadastrar + helpers de parcelas

**Stack:** python
**Depende de:** 01, 02, 03, 05
**Contrato:** `resultado-tools.md`, `relogio-contexto.md`, `prompts-injection.md`

## Objetivo
Tool determinística que monta registro(s) (sem persistir) conforme `fluxo-atendimento-cadastro.md`.

## Arquivos (posse exclusiva)
- `agent/tools/__init__.py`
- `agent/tools/cadastrar.py`
- `agent/tools/_parcelas.py`   # reuso de agent/services/parcelas.py + valores_das_parcelas extraído de cadastrar.py
- `tests/test_tool_cadastrar.py`

## Escopo
1. `_parcelas.py`: portar `adicionar_meses`, `status_por_data`, `data_status_por_forma`, `datas_do_grupo` + extrair `valores_das_parcelas` (Decimal, resto na última) do `cadastrar.py` atual.
2. `cadastrar.py`: `ToolCadastrar.executar(itens, contexto) -> ResultadoTool`:
   - Regras de inferência (forma ausente→PIX; parcela/cartão→CARTAO_CREDITO; PIX/débito→PAGO; crédito/boleto→PENDENTE por vencimento). `DINHEIRO`→PIX (plan D3).
   - Parcelado: só atual + futuras, mesmo `grupo_parcela_id`, valor repetido, dia avançando o mês.
   - Categorização (regra ou extração especializada via `02-extracao-cadastrar.md` — 1 chamada quando necessário).
   - `responsavel` preenchido com `Settings.RESPONSAVEL_PADRAO` (nunca o default do DTO).
   - Datas coeridas via `Relogio`.
   - Campos faltantes → `status="aguardando_complemento"`; completo → `aguardando_confirmacao`. **Nunca persiste.**

## Critérios de aceite
- [ ] PIX simples → 1 registro PAGO hoje, `aguardando_confirmacao`.
- [ ] Parcelado 3/5 → 3 registros (atual+2 futuras), mesmo grupo, status da atual por vencimento.
- [ ] Valor ausente → `aguardando_complemento` com `campos_faltantes=["valor"]`.
- [ ] `responsavel` == `RESPONSAVEL_PADRAO`. Matemática em `Decimal`.

## Verificação
```bash
uv run pytest tests/test_tool_cadastrar.py -v
```
