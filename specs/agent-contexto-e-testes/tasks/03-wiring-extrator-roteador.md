# Tarefa 03 — Wiring: Extrator no Roteador + main.py

**Stack:** python  
**Estado:** todo  
**Depende de:** 01 (Extrator deve existir)  
**Bloqueia:** nenhuma

## Objetivo

Injetar `Extrator` no `Roteador` e chamá-lo antes de `ToolCadastrar` quando `acao == "cadastrar"`. Atualizar `main.py` para criar e injetar o `Extrator`.

## Arquivos que esta tarefa possui

- `agent/services/roteador.py` ← modificar
- `agent/entrypoint/main.py` ← modificar

## NÃO toca em

- `agent/services/extrator.py` (tarefa 01)
- `agent/tools/cadastrar.py` (tarefa 04)

## Mudanças em `roteador.py`

### 1. Adicionar `extrator` ao `__init__`

```python
from agent.services.extrator import Extrator  # import condicional (TYPE_CHECKING) para evitar circular

class Roteador:
    def __init__(
        self,
        tool_cadastrar,
        tool_listar,
        tool_atualizar,
        tool_excluir,
        tool_conversar,
        estado_store,
        repository,
        llm=None,
        extrator=None,   # ← novo parâmetro opcional
    ) -> None:
        ...
        self._extrator = extrator
```

### 2. Chamar Extrator em `_executar_operacional`

```python
if acao == "cadastrar":
    itens = params.itens if isinstance(params, ParamsCadastrar) else []
    if self._extrator is not None and itens:
        itens = await self._extrator.extrair_cadastro(
            itens_parciais=itens,
            mensagem_original=contexto.get("mensagem", ""),
            historico=[f"{m.papel}: {m.texto}" for m in estado.historico],
        )
    resultado = await self.tool_cadastrar.executar(itens, contexto)
```

Nota: `estado` já está disponível no escopo de `_executar_operacional` (obtido no topo de `rotear`). Verificar se precisa passar `estado` para o método ou se lê da store de novo.

### 3. Carregar estado no método `_executar_operacional`

Atualmente `_executar_operacional` não tem acesso ao `estado`. Passar `estado` como parâmetro:

```python
async def _executar_operacional(self, intencao, estado, usuario_id, agora, contexto):
    # estado já está disponível (passado de rotear)
```

Verificar na leitura do código atual se `estado` é passado — na exploração, `rotear` obtém `estado` e pode passar para `_executar_operacional`.

## Mudanças em `main.py`

```python
from agent.services.extrator import Extrator
from agent.agents_llm import criar_llm

# No lifespan, junto com outras inicializações:
extrator = Extrator(llm=criar_llm())

# Em construir_roteador:
def construir_roteador(repo):
    return Roteador(
        ...,
        extrator=extrator,
    )
```

## Critério de verificação local

```bash
uv run pytest tests/test_roteador.py -v
uv run pytest tests/test_main_wiring.py -v
```

- Teste de integração: `Roteador` com `extrator` mockado → verifica que `extrair_cadastro` é chamado quando `acao == "cadastrar"`.
- Teste de não-regressão: `Roteador` sem `extrator` (None) → comportamento idêntico ao atual.
