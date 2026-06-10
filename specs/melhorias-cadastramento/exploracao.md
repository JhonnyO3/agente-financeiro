# Exploração — melhorias-cadastramento

## Estrutura tocada pela feature

| Camada | Arquivo | Papel | Mudança prevista |
|---|---|---|---|
| Model | `app/models/enums.py` | enums `Forma`/`Categoria`/`Tipo`/`Status` | RF-01, RF-04 |
| Model | `app/models/transacao.py` | ORM `transacoes` | + coluna `recorrente`; default forma |
| DTO | `app/repositories/dtos.py` | `TransacaoCreate`/`Update` | default forma; campo `recorrente` |
| Migration | `migrations/versions/` | Alembic (`0001`, `0002` existentes) | `0003` schema, `0004` dados |
| Agente | `app/agents/extrator.py` | extrai `forma_pagamento` (Literal) | novos valores + default |
| Agente | `app/agents/categorizador.py` | Literal de categorias | +EDUCACAO, −OUTROS |
| Serviço | `app/services/cadastrar.py` | `_processar` força `PARCELAMENTOS`; default forma | RF-02/03/05/06/07 |
| Serviço | `app/services/parcelas.py` | `adicionar_meses`, `status_por_data` | data de fatura (reuso de `adicionar_meses`) |
| Serviço | `app/services/confirmacao_state.py` | máquina de estados | novo estado `AGUARDAR_RECORRENCIA` |
| Serviço | `app/services/pipeline.py` | roteia estados/intenções | tratar `AGUARDAR_RECORRENCIA` |
| Prompts | `prompts/categorizacao.md`, `sistema.md` | guiam LLM | refletir categorias/formas novas |
| Dashboard | `dashboard/blueprints/api_transacoes.py` | default `OUTRO`, PIX→PAGO | refletir enums |
| Dashboard | `dashboard/templates/index.html` | `<option>` CARTAO/OUTRO hardcoded | atualizar selects |
| Dashboard | `dashboard/static/charts.js` | mapa de cores por categoria | +EDUCACAO, −OUTROS |

## Convenções reais observadas

- Migrations em `migrations/versions/NNNN_*.py`, colunas como `String` (enum não-nativo), com
  `server_default` e `op.execute("UPDATE …")` para dados existentes. `down_revision` encadeado.
- Enums herdam `str, enum.Enum`; agentes repetem os valores em `Literal[...]` do Pydantic.
- `adicionar_meses` já preserva o dia e clampa fim de mês — reusar para a data de fatura
  (RF-03 = `adicionar_meses(data, 1)`).
- `_valores_das_parcelas` já divide com resto na última parcela (RF-07 já atendido; só validar).
- Estados de confirmação são roteados em `pipeline.py` por `estado.acao`; novos estados exigem
  um ramo novo em `_rotear_estado` + persistência via `ConfirmacaoState.salvar`.

## Riscos / pontos de atenção

- **`forma_pagamento = OUTRO` é o default de coluna (migration 0002) e de DTO.** Trocar o default
  sem migrar dados existentes deixaria `OUTRO` órfão — a migração 0004 precisa zerar todos.
- **Coluna `data` é NOT NULL.** Recorrentes mantêm `data` (data-base), não nullable — evita
  migration destrutiva e preserva integridade (decisão da spec, RF-06).
- **Enums são contrato compartilhado** entre model, agentes (Literal) e dashboard (HTML/JS). Mudar
  em um lugar sem os outros quebra cadastro ou exibição → congelar contrato antes de paralelizar.
- **Sanitização tem alvo textual** (`dados-corrigidos.txt`) com ruídos já decididos: `zara` reusa
  grupo do batman (gerar UUID novo); `Spotify`/`uber` ainda `OUTRO` (resolver por regra).
