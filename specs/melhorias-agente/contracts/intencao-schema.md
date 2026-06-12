# Contrato: Schema de Intenção (classificador → roteador)

**Status:** Congelado
**Fronteira:** Classificador (LLM #1) ↔ Roteador ↔ Tools
**Arquivo de posse:** `agent/domain/intencao.py`

## Saída do classificador

```python
from decimal import Decimal
from datetime import date
from typing import Literal
from pydantic import BaseModel

Acao = Literal[
    "cadastrar", "listar", "atualizar", "excluir", "conversar",
    "confirmar", "cancelar", "selecionar", "complementar", "desconhecida",
]

class Intencao(BaseModel):
    acao: Acao
    parametros: ParametrosPorAcao   # union discriminada por `acao`
    confianca: float                # 0.0..1.0
```

- `with_structured_output(Intencao)`. **Nada de `dict` livre.**
- `confianca < Settings.CONFIANCA_MINIMA` (default 0.7) → o classificador retorna `acao="desconhecida"`.
- Plano B documentado (não implementar agora): se o corte oscilar, trocar `confianca: float` por `banda: Literal["alta","media","baixa"]`. **v1 usa float.**

## Parâmetros por ação (campos não mencionados → `None`)

```python
class ItemCadastro(BaseModel):
    descricao: str | None = None
    valor: Decimal | None = None
    forma_pagamento: Literal["PIX","CARTAO_CREDITO","CARTAO_DEBITO","BOLETO","DINHEIRO"] | None = None
    parcela_atual: int | None = None
    total_parcelas: int | None = None
    dia_vencimento: int | None = None
    data: str | None = None            # texto bruto ("ontem","10 de julho"); coerção na Tool via Relogio
    tipo: Literal["GASTO","INVESTIMENTO","RECEITA"] | None = None

class ParamsCadastrar(BaseModel):
    itens: list[ItemCadastro]

class ParamsListar(BaseModel):
    periodo: str | None = None         # "mes_atual","mes_passado","YYYY-MM" ou nome do mês
    categoria: str | None = None
    responsavel: str | None = None
    status: Literal["PAGO","PENDENTE"] | None = None

class ParamsAtualizar(BaseModel):
    referencia: str | None = None      # descricao/data/valor que identifica o registro
    campo: Literal["valor","data","status","categoria","descricao","forma_pagamento"] | None = None
    novo_valor: str | None = None      # bruto; a Tool coage por campo

class ParamsExcluir(BaseModel):
    referencia: str | None = None      # modo individual
    periodo: str | None = None         # modo lote
    categoria: str | None = None       # modo lote

class ParamsSelecionar(BaseModel):
    opcao: int                         # texto da opção já mapeado p/ número pelo classificador

class ParamsComplementar(BaseModel):
    campo: str                         # "valor","parcelas",...
    valor: str                         # bruto

class ParamsVazio(BaseModel):
    pass                               # conversar, confirmar, cancelar, desconhecida

ParametrosPorAcao = (
    ParamsCadastrar | ParamsListar | ParamsAtualizar | ParamsExcluir
    | ParamsSelecionar | ParamsComplementar | ParamsVazio
)
```

## Regras de pendência (responsabilidade do classificador, via prompt)

1. `{estado_pendente}` == "nenhuma" ⇒ **nunca** `confirmar`/`cancelar`/`selecionar`/`complementar`.
2. Pendência ativa + mensagem é intenção operacional nova ⇒ classificar a intenção nova (o roteador cancela a pendência).
3. Ambíguo entre resposta e intenção nova ⇒ preferir resposta à pendência.

## Garantias para o consumidor (roteador)

- `acao` sempre presente; `parametros` é o tipo correspondente à `acao` (o roteador faz `match intencao.acao`).
- Valores monetários chegam como `Decimal` (coerção no structured output); datas chegam como **texto bruto** — a coerção temporal é da Tool via `Relogio` (contrato `relogio-contexto`).
- O classificador **não** calcula nada (totais, divisão de parcela).

## Critérios de aceitação

- Cobre os 17 exemplos de `classificador.md` produzindo a `acao` e os `parametros` esperados.
- Union discriminada por `acao`; tipo errado de parâmetros para uma ação falha validação Pydantic.
