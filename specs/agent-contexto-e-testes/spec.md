# Spec — Contexto Multi-turno, Extração em 2 Etapas e Harness de Testes

## Diagnóstico técnico (base para os requisitos)

### Problema 1 — Extração morta: `02-extracao-cadastrar.md` nunca é chamado

`ARQUIVO_POR_ACAO` em `prompts.py` registra os prompts de extração ("cadastrar", "atualizar"), mas **nenhum código de produção chama `montar_prompt("cadastrar", ...)`**. A única chamada de LLM é no `Classificador`, que usa só `01-classificador.md`. Resultado: as regras ricas de extração (Mercado Pago → CARTAO_CREDITO quando vence no dia X; distinção valor-total vs valor-parcela; etc.) existem no prompt mas nunca chegam ao LLM.

### Problema 2 — Histórico existe mas o LLM não é instruído a usá-lo para extração

O `worker.py` passa `estado.historico` ao classificador. O `00-base.md` injeta `{historico_recente}` como "## Contexto da conversa" — mas o `01-classificador.md` não tem nenhuma instrução explícita dizendo "use o histórico para resolver ambiguidades de parâmetros". O LLM vê o histórico mas não sabe que deve extrair `forma_pagamento` de uma mensagem anterior.

### Problema 3 — Inferência de forma_pagamento ignora plataformas de pagamento

Regra em `ToolCadastrar._inferir_forma`: "parcela/cartão → CARTAO_CREDITO; senão → PIX". Não existe regra para "Mercado Pago + vencimento no dia X → cartão de crédito". O prompt de extração tem essa regra, mas o prompt de extração nunca é chamado.

### Problema 4 — `complementar` só pede `valor`, nunca `forma_pagamento`

`ToolCadastrar.executar` só verifica `campos_faltantes = ["valor"]`. Nunca pede `forma_pagamento` quando ambígua, nunca pede `dia_vencimento` para cartão sem data. A máquina de estados fica silenciosa sobre ambiguidades que poderia perguntar.

### Problema 5 — Sem harness de testes end-to-end via terminal

Não existe script que simule conversas multi-turno com o pipeline real (LLM real, sem WhatsApp). Testar regressões exige enviar mensagens pelo celular.

---

## Escopo

### Dentro do escopo

1. **Extração em 2 etapas**: separar classificação (etapa 1) de extração detalhada (etapa 2) para `cadastrar` e `atualizar`.
2. **Instrução explícita de uso do histórico**: o prompt de extração deve instruir o LLM a consultar o histórico para resolver ambiguidades de `forma_pagamento`, `dia_vencimento`, plataforma ("Mercado Pago", "iFood"), tipo de compra.
3. **Regra de Mercado Pago / plataformas de pagamento**: adicionar ao prompt de extração regras para inferir forma quando o usuário cita plataforma que é contextualmente cartão.
4. **Campos faltantes expandidos**: `ToolCadastrar` pergunta `forma_pagamento` quando ambígua (cartão ou PIX?) além de `valor`.
5. **Harness CLI de testes**: script `scripts/chat_terminal.py` que simula uma sessão multi-turno contra o pipeline real, sem WhatsApp.
6. **Suite de cenários de teste**: 60 cenários documentados (20 gastos, 20 investimentos/receitas, 20 consultas) rodados pelo harness ou por testes automatizados.

### Fora do escopo

- Mudança de banco de dados, modelos SQLAlchemy ou repositórios.
- Autenticação / multiusuário (já existe, não alterar).
- Dashboard Flask / frontend.
- Migração para Redis (EstadoStoreMemoria segue ok para testes).
- Mudança de LLM ou provider.
- Interface no WhatsApp — o harness substitui para testes, não o WhatsApp em produção.

---

## Requisitos

### RF-01 — Pipeline de extração em 2 etapas para `cadastrar`

**Antes:** `Classificador` retorna `Intencao(acao="cadastrar", parametros=ParamsCadastrar)` com extração parcial feita pelo `01-classificador.md`.

**Depois:** quando `acao == "cadastrar"`, o `Roteador` ou a `ToolCadastrar` faz uma segunda chamada LLM usando `montar_prompt("cadastrar", ctx)` onde `ctx` inclui a mensagem original e `historico_recente`. O `ParamsCadastrar` retornado pelo classificador pode ter campos `None`; a segunda etapa preenche os campos com as regras completas de `02-extracao-cadastrar.md`.

**Critério verificável:** dado `mensagem="comprei no Mercado Pago, vence dia 10"`, a segunda etapa LLM retorna `forma_pagamento=CARTAO_CREDITO` e `dia_vencimento=10`. O `01-classificador.md` pode retornar `forma_pagamento=None` — isso é aceitável para ele.

### RF-02 — Instrução explícita de uso de histórico no prompt de extração

`02-extracao-cadastrar.md` deve ter seção "## Contexto da conversa" instruindo: "Se `forma_pagamento`, `dia_vencimento` ou `parcelas` foram mencionados em mensagens anteriores, use esses valores — não peça de novo."

**Critério verificável:** turno 1 = "comprei roupa"; turno 2 = "no crédito, foi 350". A segunda extração retorna `forma_pagamento=CARTAO_CREDITO, valor=350`, não `forma_pagamento=None`.

### RF-03 — Extrator é agnóstico a plataformas

O prompt de extração (`02-extracao-cadastrar.md`) **não deve ter listas de plataformas, apps ou bancos**. O LLM deve entender o contexto pelo que o usuário efetivamente comunicou sobre a forma de pagamento — "vence dia 10", "em 3x", "no crédito" são sinais de intenção que o modelo resolve naturalmente com linguagem.

O único mapeamento permitido é o que reflete a intenção real de pagamento:
- Menção a parcelas, vencimento futuro, "no crédito" → `CARTAO_CREDITO`
- Pagamento imediato, "pix", "à vista no débito" → `PIX` / `CARTAO_DEBITO`
- Nenhum contexto claro → `forma_pagamento=None` (vai para campo faltante, RF-04)

**Critério verificável:** `mensagem="gastei 200 que vence dia 10"` → extrator retorna `forma_pagamento=CARTAO_CREDITO, dia_vencimento=10` usando raciocínio natural do LLM, sem hardcode de plataforma.

### RF-04 — `ToolCadastrar` pede `forma_pagamento` quando ambígua

Se após a extração em 2 etapas `forma_pagamento is None` E a mensagem não tem nenhuma pista clara de forma, `ToolCadastrar` adiciona `"forma_pagamento"` a `campos_faltantes` e retorna `status="aguardando_complemento"`.

**Critério verificável:** `mensagem="gastei 50 no açougue"` → classificador classifica, extrator não consegue inferir forma → resposta pergunta "Foi no PIX, cartão de crédito ou débito?".

**Exceção:** se há regra que claramente infere (ex: parcelado → cartão), não pergunta.

### RF-05 — Harness CLI multi-turno (`scripts/chat_terminal.py`)

Script executável via `uv run python scripts/chat_terminal.py` que:

- Inicializa o pipeline completo (EstadoStoreMemoria, LLM real, repo mockado ou real via env).
- Aceita entrada de texto pelo terminal e exibe resposta do agente.
- Suporta modo interativo (digitar mensagens uma a uma) E modo batch (arquivo JSONL de turnos).
- No modo batch, registra resultado de cada turno e ao final exibe: `[OK]` ou `[FALHOU]` por cenário.
- Modo batch: formato de entrada = `{"turno": 1, "msg": "...", "espera": "CARTAO_CREDITO"}` onde `espera` é string buscada na resposta (case-insensitive).

**Critério verificável:** `uv run python scripts/chat_terminal.py --batch scripts/cenarios_teste.jsonl` termina com código de saída 0 se todos passam, 1 se algum falha.

### RF-06 — Suite de 60 cenários de teste documentados

Arquivo `scripts/cenarios_teste.jsonl` com 60 conversas divididas em:

- **20 gastos** — variações de forma de pagamento, parcelamento, plataforma, ambiguidade, multi-turno.
- **20 investimentos/receitas** — aportes em fundos, CDB, poupança, salário, renda variável.
- **20 consultas** — "quanto gastei esse mês?", "me mostra os parcelamentos", "estou no azul?", filtros por categoria, semana, dia específico.

Cada cenário pode ter N turnos. O campo `espera` é opcional; sem ele, o turno só verifica que não houve exception.

**Critério verificável:** ao rodar o harness em modo batch com os 60 cenários, pelo menos 55/60 passam (margem de 5 para LLM não-determinístico).

### RF-07 — Modo `--seed` no harness para replay sem LLM

Para CI: o harness aceita `--seed caminho/respostas_llm.json` que injeta respostas LLM mockadas fixas, eliminando chamadas reais à OpenAI. Isso permite rodar os 60 cenários em CI sem custo.

**Critério verificável:** `uv run python scripts/chat_terminal.py --batch scripts/cenarios_teste.jsonl --seed scripts/seed_respostas.json` roda sem chamar OpenAI (verificável mockando a API e confirmando zero chamadas).

---

## Contratos de API (a congelar no planejamento)

### Contrato — segunda etapa de extração

```python
class Extrator:
    async def extrair_cadastro(
        self,
        itens_parciais: list[ItemCadastro],  # saída do classificador (pode ter None)
        mensagem_original: str,
        historico: list[str],  # ["usuario: ...", "assistente: ..."]
    ) -> list[ItemCadastro]:  # campos preenchidos ao máximo
        ...
```

Chamado pelo `Roteador` antes de repassar à `ToolCadastrar`.

### Contrato — harness

```python
class HarnessAgente:
    async def enviar(self, usuario_id: int, texto: str) -> str:
        """Roda o pipeline completo e retorna a resposta formatada."""
        ...

    async def resetar(self, usuario_id: int) -> None:
        """Limpa estado de conversação (para novo cenário)."""
        ...
```

---

## Como verificar (requisito → teste)

| Requisito | Como verificar |
|---|---|
| RF-01 | Teste unitário: mock do `Extrator` verifica que é chamado quando acao=cadastrar; teste de integração LLM verifica campos preenchidos. |
| RF-02 | Teste de prompt: `montar_prompt("cadastrar", ctx_com_historico)` inclui instrução de usar histórico; teste LLM multi-turno verifica extração cross-turno. |
| RF-03 | Teste do extrator com `mensagem="gastei X que vence dia 10"` → `forma_pagamento=CARTAO_CREDITO` sem nenhuma regra de plataforma no código. |
| RF-04 | Teste unitário `ToolCadastrar` com item sem forma_pagamento inferível → `campos_faltantes=["forma_pagamento"]`. |
| RF-05 | `uv run python scripts/chat_terminal.py --help` sem erro; modo batch com 1 cenário simples passa. |
| RF-06 | `uv run python scripts/chat_terminal.py --batch scripts/cenarios_teste.jsonl` passa ≥55/60. |
| RF-07 | Teste CI: harness com `--seed` + mock OpenAI → 0 chamadas reais. |

---

## Critérios de aceitação (checklist)

- [ ] `uv run pytest tests/ -v` verde antes e depois das mudanças.
- [ ] `montar_prompt("cadastrar", ctx)` é chamado no pipeline real quando acao=cadastrar (verificável por log ou teste).
- [ ] Cenário "Mercado Pago + vence dia 10" → resposta inclui "cartão" ou "CARTAO_CREDITO" ou "crédito".
- [ ] Cenário multi-turno: turno 1 cadastra sem forma, turno 2 informa "no crédito" → confirmação menciona cartão.
- [ ] `scripts/chat_terminal.py --batch` existe e roda sem ImportError.
- [ ] `scripts/cenarios_teste.jsonl` tem ≥60 cenários divididos conforme RF-06.
- [ ] ≥55/60 cenários passam com LLM real (rodar manualmente 1x, documentar resultado).
- [ ] `--seed` mode roda sem chamar OpenAI.
