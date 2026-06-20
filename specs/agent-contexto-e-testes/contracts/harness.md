# Contrato — HarnessAgente (CLI multi-turno)

**Status: Congelado**

## Interface

```python
# scripts/chat_terminal.py (classe interna)

class HarnessAgente:
    async def enviar(self, usuario_id: int, texto: str) -> str:
        """Roda o pipeline completo e retorna a resposta formatada."""
        ...

    async def resetar(self, usuario_id: int) -> None:
        """Limpa estado de conversação (para novo cenário)."""
        ...
```

## Componentes inicializados pelo harness

- `EstadoStoreMemoria` — sem banco
- `Classificador` — LLM real (ou mockado via `--seed`)
- `Extrator` — LLM real (ou mockado via `--seed`)
- `ToolCadastrar`, `ToolListar`, etc. — com repo mockado (retorna listas vazias)
- `Roteador` — instanciado com as tools acima
- `Formatador` — formata resultado para texto

## CLI flags

| Flag | Comportamento |
|---|---|
| (nenhum) | Modo interativo: lê stdin linha a linha |
| `--batch <arquivo.jsonl>` | Modo batch: lê cenários do arquivo |
| `--seed <respostas.json>` | Injeta respostas LLM mockadas (substitui ChatOpenAI) |
| `--usuario <id>` | ID numérico do usuário (padrão: 1) |

## Formato JSONL de cenários (`cenarios_teste.jsonl`)

Cada linha é um objeto JSON. Um cenário pode ter vários turnos:

```jsonl
{"cenario": 1, "turno": 1, "msg": "gastei 200 no mercado", "espera": "ALIMENTACAO"}
{"cenario": 1, "turno": 2, "msg": "foi no pix", "espera": null}
{"cenario": 2, "turno": 1, "msg": "comprei roupa no crédito em 3x, 150 cada", "espera": "CARTAO_CREDITO"}
```

- `cenario`: int — agrupa turnos do mesmo cenário (resetar estado entre cenários)
- `turno`: int — ordem dentro do cenário
- `msg`: str — texto enviado pelo usuário
- `espera`: str | null — substring buscada na resposta (case-insensitive); null = só verifica sem exception

## Formato do arquivo `--seed`

```json
{
  "respostas": [
    {
      "prompt_contém": "classificador",
      "resposta": {"acao": "cadastrar", "parametros": {"itens": [{"descricao": "mercado", "valor": 200}]}, "confianca": 0.95}
    }
  ]
}
```

## Saída modo batch

```
[Cenário 1] gastei 200 no mercado → [OK] (contém "ALIMENTACAO")
[Cenário 2] comprei roupa... → [OK] (contém "CARTAO_CREDITO")
...
Resultado: 58/60 passaram | 2 falharam
```

Exit code 0 se todos passam, 1 se algum falha.

## Repo mockado

```python
class RepoMock:
    async def criar_lote(self, registros, usuario_id): pass
    async def listar(self, **kwargs): return []
    async def buscar_semantico(self, **kwargs): return []
    async def atualizar(self, *args, **kwargs): pass
    async def excluir(self, *args, **kwargs): pass
    # ... demais métodos retornam valores neutros
```
