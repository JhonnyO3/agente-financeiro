# Contrato — Extrator (segunda etapa de extração)

**Status: Congelado**

## Interface

```python
# agent/services/extrator.py

class Extrator:
    def __init__(self, llm: Any) -> None: ...

    async def extrair_cadastro(
        self,
        itens_parciais: list[ItemCadastro],  # saída do classificador (pode ter None)
        mensagem_original: str,
        historico: list[str],                # ["usuario: ...", "assistente: ..."]
        contexto_extra: dict[str, Any] | None = None,
    ) -> list[ItemCadastro]:                 # campos preenchidos ao máximo
        ...
```

## Comportamento

- Chama `montar_prompt("cadastrar", ctx)` onde `ctx` inclui:
  - `mensagem`: mensagem original do usuário
  - `historico_recente`: histórico formatado como string
  - `parametros`: representação dos itens parciais (JSON ou texto estruturado)
  - `data_atual`: data de hoje em DD/MM/YYYY
  - `user_name`: nome do usuário
  - `estado_pendente`: "nenhuma" (extração não tem pendência ativa)
- Usa `llm.with_structured_output(ParamsCadastrar)` → retorna `ParamsCadastrar`
- Extrai `.itens` do retorno e devolve como `list[ItemCadastro]`
- Mantém valores já preenchidos pelo classificador (não sobrescreve com None)

## Onde é chamado

`Roteador._executar_operacional` quando `acao == "cadastrar"`, antes de repassar para `ToolCadastrar`.

## Ponto de inserção no Roteador

```python
# Em _executar_operacional:
if acao == "cadastrar":
    itens = params.itens if isinstance(params, ParamsCadastrar) else []
    if self._extrator is not None:
        itens = await self._extrator.extrair_cadastro(
            itens_parciais=itens,
            mensagem_original=contexto.get("mensagem", ""),
            historico=[f"{m.papel}: {m.texto}" for m in estado.historico],
        )
    resultado = await self.tool_cadastrar.executar(itens, contexto)
```

## Wiring em main.py

```python
extrator = Extrator(llm=criar_llm())
# Injetado no Roteador via parâmetro `extrator`
```

## Invariantes

- Nunca lança exceção por campo ausente — campos não inferíveis retornam None
- Nunca diminui informação já extraída pelo classificador
- Thread-safe (stateless)
