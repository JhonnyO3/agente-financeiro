# Contrato: Agent LLM (LangChain Chains)

**Status: Congelado**

## Chain de Classificação de Intenção

**Entrada:**
```python
{"mensagem": str}
```

**Saída:**
```python
class IntencaoResult(BaseModel):
    intencao: Literal["CADASTRAR", "ALTERAR", "EXCLUIR", "CONSULTAR", "FORA_DE_ESCOPO"]
    confianca: Literal["alta", "media", "baixa"]
```

Usa `prompts/intencao.md` como system prompt.

---

## Chain de Extração de Transação

**Entrada:**
```python
{"mensagem": str, "data_atual": str}
```

**Saída:**
```python
class ExtracaoResult(BaseModel):
    tipo: Literal["GASTO", "INVESTIMENTO"]
    valor_total: Decimal          # valor bruto informado pelo usuário
    valor_por_parcela: Decimal | None  # None se usuário informou por parcela
    parcela_total: int            # 1 se não mencionado
    descricao: str | None
    data_referencia: date         # data da 1ª parcela
    menciona_cartao: bool         # True dispara pergunta de parcelas
```

Usa `prompts/categorizacao.md` para classificar categoria após extração.

---

## Chain de Categorização

**Entrada:**
```python
{"tipo": str, "descricao": str, "valor": float}
```

**Saída:**
```python
class CategorizacaoResult(BaseModel):
    categoria: Literal["ALIMENTACAO", "TRANSPORTE", "LAZER", "INVESTIMENTO", "GASTOS_FIXOS", "COMPRAS"]
```

---

## Chain de Extração de Filtros (Consulta)

**Entrada:**
```python
{"mensagem": str, "data_atual": str}
```

**Saída:**
```python
class FiltroConsultaResult(BaseModel):
    tipo_consulta: Literal["mensal", "semanal", "geral", "grupo_parcela", "dinamico"]
    mes: int | None
    ano: int | None
    categoria: str | None
    descricao_grupo: str | None   # para busca semântica do grupo
    periodo_inicio: date | None
    periodo_fim: date | None
```

---

## Chain de Extração de Alteração (fix #2)

Extrai apenas os campos que o usuário quer **modificar** — não cria uma transação nova.

**Entrada:**
```python
{"mensagem": str, "data_atual": str}
```

**Saída:**
```python
class ExtracaoAlteracaoResult(BaseModel):
    novo_valor: Decimal | None
    nova_descricao: str | None
    nova_categoria: str | None
    nova_data: date | None
    # Apenas campos mencionados são preenchidos; os demais ficam None
    # "muda para 80 reais" → novo_valor=80, resto=None
    # "renomeia para academia" → nova_descricao="academia", resto=None
```

Converte diretamente para `TransacaoUpdate` descartando os campos `None`.

---

## Chain de Interpretação de Confirmação (fix #5)

Interpreta a resposta livre do usuário a um pedido de confirmação.

**Entrada:**
```python
{"mensagem": str, "contexto": Literal["sim_nao", "escopo_parcela"]}
# contexto="sim_nao"        → usado para ALTERAR e EXCLUIR simples
# contexto="escopo_parcela" → usado para EXCLUIR parcelado (pergunta_grupo=True)
```

**Saída:**
```python
class ConfirmacaoResposta(BaseModel):
    tipo: Literal["sim", "nao", "parcela", "grupo"]
    # contexto="sim_nao":        apenas "sim" ou "nao" são válidos
    # contexto="escopo_parcela": apenas "parcela" ou "grupo" são válidos
```

---

## Chain de Extração de Parcelas (fix #1)

Extrai número de parcelas da resposta do usuário ao fluxo de cartão.

**Entrada:**
```python
{"mensagem": str}
```

**Saída:**
```python
class ExtratorParcelasResult(BaseModel):
    parcela_total: int  # "3 vezes" → 3 | "à vista" → 1 | "6x" → 6
```

---

## Regras gerais

| Chain                        | Módulo                        | Modelo         | Temperatura |
|------------------------------|-------------------------------|----------------|-------------|
| Classificação de intenção    | `agents/classificador.py`     | `gpt-4o-mini`  | 0           |
| Extração de transação        | `agents/extrator.py`          | `gpt-4o-mini`  | 0           |
| Extração de alteração        | `agents/extrator_alteracao.py`| `gpt-4o-mini`  | 0           |
| Extração de parcelas         | `agents/extrator_parcelas.py` | `gpt-4o-mini`  | 0           |
| Categorização                | `agents/categorizador.py`     | `gpt-4o-mini`  | 0           |
| Filtro de consulta           | `agents/filtro_consulta.py`   | `gpt-4o-mini`  | 0           |
| Interpretação de confirmação | `agents/confirmacao_chain.py` | `gpt-4o-mini`  | 0           |
| Formatação de resposta       | `services/formatador.py`      | `gpt-4o`       | 0.3         |
| Embedding                    | `agents/embedder.py`          | `text-embedding-3-small` | — |

- Output estruturado sempre via `with_structured_output(PydanticModel)`
- Nunca pedir ao LLM para somar, dividir ou calcular — apenas extrair e formatar
- Usar `langchain_openai.ChatOpenAI` e `langchain_openai.OpenAIEmbeddings`
