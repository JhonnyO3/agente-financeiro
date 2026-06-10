# Tarefa 05 — Agent: Classificação e Extração (LangChain Chains)

**Stack:** python  
**Depende de:** 01-setup-projeto  
**Arquivos próprios:** `app/agents/base.py`, `app/agents/embedder.py`, `app/agents/classificador.py`, `app/agents/extrator.py`, `app/agents/extrator_alteracao.py`, `app/agents/extrator_parcelas.py`, `app/agents/categorizador.py`, `app/agents/filtro_consulta.py`, `app/agents/confirmacao_chain.py`

## Objetivo

Implementar os chains LangChain para: classificar intenção, extrair dados de transação e categorizar. Sem acesso ao banco — apenas LLM I/O.

## Contrato de referência

`contracts/agent-llm.md` — inputs, outputs e Pydantic models de cada chain.

## Entregáveis

### `app/agents/base.py`

```python
from langchain_openai import ChatOpenAI
from pathlib import Path

def carregar_prompt(nome: str) -> str:
    return (Path(__file__).parents[2] / "prompts" / nome).read_text(encoding="utf-8")

def criar_llm(temperatura: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o", temperature=temperatura)

def criar_llm_mini(temperatura: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o-mini", temperature=temperatura)
```

> Usar `gpt-4o-mini` para classificação e extração (custo menor, latência menor).  
> Usar `gpt-4o` para formatação de respostas ao usuário.

### `app/agents/classificador.py`

Chain que usa `prompts/intencao.md`.  
Output: `IntencaoResult` (ver contrato).

### `app/agents/extrator.py`

Chain que usa `prompts/sistema.md` + instrução de extração.  
Output: `ExtracaoResult` com `menciona_cartao: bool`.

### `app/agents/categorizador.py`

Chain que usa `prompts/categorizacao.md`.  
Output: `CategorizacaoResult`.  
Regra: se `tipo == INVESTIMENTO` → retorna `INVESTIMENTO` sem chamar o LLM.

### `app/agents/filtro_consulta.py`

Chain para extrair filtros de consulta.  
Output: `FiltroConsultaResult` (ver contrato).

### `app/agents/extrator_alteracao.py`

Chain que extrai apenas os campos a modificar. Output: `ExtracaoAlteracaoResult` (ver contrato).  
Exemplo: "muda para 80 reais" → `{novo_valor: 80, resto: None}`.

### `app/agents/extrator_parcelas.py`

Chain que extrai número inteiro de parcelas de uma resposta livre. Output: `ExtratorParcelasResult`.  
Exemplo: "3 vezes" → `{parcela_total: 3}` · "à vista" → `{parcela_total: 1}`.

### `app/agents/confirmacao_chain.py`

Chain que interpreta confirmação ambígua do usuário. Output: `ConfirmacaoResposta`.  
Ver contrato — recebe `contexto: "sim_nao" | "escopo_parcela"` para limitar opções válidas.

### `app/agents/embedder.py`

Wrapper sobre `OpenAIEmbeddings`. Ver **`contracts/embedding.md`** para interface, texto composto e regras.

## Critério de aceite

- [ ] "gastei 50 no mercado" → `IntencaoResult(intencao="CADASTRAR", confianca="alta")`
- [ ] "comprei PETR4 por 300" → `ExtracaoResult(tipo="INVESTIMENTO", ...)`
- [ ] `categorizador` com `tipo=INVESTIMENTO` → retorna `INVESTIMENTO` sem chamar LLM
- [ ] "resumo de junho" → `FiltroConsultaResult(tipo_consulta="mensal", mes=6)`
- [ ] "muda para 80 reais" → `ExtracaoAlteracaoResult(novo_valor=80, resto=None)`
- [ ] "3 vezes" → `ExtratorParcelasResult(parcela_total=3)`
- [ ] "pode ser" com `contexto="sim_nao"` → `ConfirmacaoResposta(tipo="sim")`
- [ ] "só essa" com `contexto="escopo_parcela"` → `ConfirmacaoResposta(tipo="parcela")`
- [ ] Temperatura 0 em todos os chains de classificação/extração
