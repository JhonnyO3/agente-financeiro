# Contrato: Resultado das Tools (Tools → Formatador / Roteador)

**Status:** Congelado
**Fronteira:** 5 Tools ↔ Formatador (templates) ↔ Roteador (persistência da pendência)
**Arquivos de posse:** modelos em `agent/domain/intencao.py`? → **não**: ficam em `agent/services/roteador.py`? → **não**.
> Os modelos `ResultadoTool` vivem em `agent/domain/resultado.py` (posse da T01, junto do schema de intenção — mesmo dono de domínio, sem colisão de outras tasks).

## Modelo base

```python
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel

class ResultadoTool(BaseModel):
    acao: Literal["cadastrar","listar","atualizar","excluir","conversar","menu","erro"]
    status: Literal[
        "aguardando_confirmacao",  # escrita pendente; payload guardado no estado
        "aguardando_selecao",      # RAG ambíguo; opcoes guardadas no estado
        "aguardando_escopo",       # exclusão de parcelado; opcoes numeradas
        "aguardando_complemento",  # falta campo (ex: valor)
        "concluido",               # listar / conversar / persistência feita
        "nao_encontrado",          # RAG abaixo do piso
        "vazio",                   # listar sem registros
    ]
    dados: dict                    # payload tipado por (acao,status) — ver abaixo
```

- O **Formatador** faz `match (resultado.acao, resultado.status)` e aplica o template Python correspondente (de `fluxo-atendimento-*.md`). **Nunca** recalcula nem decide negócio.
- Quando `status` ∈ {`aguardando_confirmacao`,`aguardando_selecao`,`aguardando_escopo`,`aguardando_complemento`}, o **Roteador** guarda `resultado` (serializado) em `EstadoConversa.payload_pendente`/`opcoes`/`campos_faltantes` e seta `acao_pendente`.

## `dados` por (acao, status)

### cadastrar
- `aguardando_confirmacao` / `aguardando_complemento`:
  ```python
  {
    "registros": [ {descricao, valor: Decimal, data: date, categoria, forma_pagamento,
                    responsavel, status, parcela_numero, parcela_total,
                    grupo_parcela_id: str|None, detalhes: str|None} ],
    "campos_faltantes": ["valor", ...],     # vazio quando completo
    "parcelas_futuras": ["Jul/26","Ago/26"] # rótulos p/ exibição; [] se à vista
  }
  ```
- `concluido` (pós-persistência): `{ "registros_salvos": [...], "qtd": int }`

### listar  (sempre `concluido` ou `vazio`; nunca pendência)
```python
{
  "periodo_label": "Jun/2026",
  "grupos": [ {"titulo": "GASTOS_FIXOS", "itens": [...], "subtotal": Decimal} ],  # PARCELAMENTOS é um grupo
  "total": Decimal, "pago": Decimal, "pendente": Decimal
}
```
Item: `{descricao, valor: Decimal, data: date, status, parcela_numero, parcela_total}`.

### atualizar
- `aguardando_selecao`: `{ "opcoes": [OpcaoPendente...] }`
- `aguardando_confirmacao`: `{ "registro": {...}, "diff": {"campo": str, "antigo": str, "novo": str}, "parcelas_afetadas": ["Jul/26",...] }`
- `nao_encontrado`: `{ "referencia": str }`
- `concluido`: `{ "descricao": str, "propagou_parcelas": bool }`

### excluir
- `aguardando_selecao`: `{ "opcoes": [...], "modo": "individual" }`
- `aguardando_escopo`: `{ "registro": {...}, "parcelas_futuras": ["Jul/26",...] }`  (opções 1=somente este, 2=todos)
- `aguardando_confirmacao`: `{ "registro": {...} }`  (individual sem parcelas) **ou** `{ "modo": "lote", "qtd": int, "periodo_label": str }`
- `nao_encontrado`: `{ "referencia": str }`
- `concluido`: `{ "descricao": str, "valor": Decimal, "parcelas_removidas": int }`

### conversar  (sempre `concluido`)
```python
{ "resposta": "texto livre já em português/WhatsApp" }   # única saída de Tool em linguagem natural
```

### menu / erro  (gerados pelo roteador, não por Tool)
- `menu` + `concluido`: `{}`  → Formatador imprime o menu de capacidades.
- `erro` + `concluido`: `{ "mensagem": str }`  → fallback amigável (worker no `except`).

## Regras invioláveis

- Toda matemática em `Decimal`; nenhum valor passa por LLM.
- Nenhuma Tool chama outra Tool.
- `cadastrar`/`atualizar`/`excluir` **nunca** persistem direto: devolvem pendência. A persistência ocorre no `confirmar` do roteador, sobre `payload_pendente` — **sem nova chamada LLM**.

## Critérios de aceitação

- Cada (acao, status) tem um shape de `dados` único e estável.
- O Formatador cobre todos os pares e reproduz os templates dos `fluxo-atendimento-*.md`.
