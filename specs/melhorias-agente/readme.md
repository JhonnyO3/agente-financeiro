# Prompts — Sistema de Injection

## Estrutura

```
prompts/
├── 00-base.md          # System prompt base — carregado em TODAS as chamadas
├── 01-classificador.md # Injection do classificador
├── 02-cadastrar.md     # Injection da Tool Cadastrar
├── 03-listar.md        # Injection da Tool Listar
├── 04-atualizar.md     # Injection da Tool Atualizar
├── 05-excluir.md       # Injection da Tool Excluir
└── 06-conversar.md     # Injection da Tool Conversar
```

## Como funciona

O `00-base.md` é sempre carregado com as variáveis do contexto do usuário.
No final do base há um placeholder `{injection_acao}` que recebe o conteúdo do arquivo da ação correspondente.

```python
def montar_prompt(acao: str, contexto: dict) -> str:
    base = carregar("00-base.md").format(
        user_name=contexto["user_name"],
        data_atual=contexto["data_atual"],
        responsavel_padrao=contexto["responsavel_padrao"],
        historico_recente=contexto["historico_recente"],
        injection_acao=carregar(f"prompt_{acao}.md").format(**contexto)
    )
    return base
```

## O que cada chamada LLM recebe

| Chamada | Base | Injection | Tokens estimados |
|---|---|---|---|
| Classificador | ✅ | 01-classificador.md | ~800 |
| Tool Cadastrar | ✅ | 02-cadastrar.md | ~900 |
| Tool Listar | ✅ | 03-listar.md | ~700 |
| Tool Atualizar | ✅ | 04-atualizar.md | ~850 |
| Tool Excluir | ✅ | 05-excluir.md | ~800 |
| Tool Conversar | ✅ | 06-conversar.md | ~750 |

## O que NÃO é injetado

Cada Tool recebe **apenas** sua própria injection. A Tool Cadastrar não sabe nada sobre os templates de exclusão. A Tool Listar não sabe nada sobre regras de parcelamento.

Isso garante:

- Contexto mínimo necessário por chamada
- Sem contaminação de regras entre ações
- Fácil de atualizar uma ação sem afetar as outras

## Variáveis disponíveis no contexto

| Variável | Descrição |
|---|---|
| `{user_name}` | Nome do usuário |
| `{data_atual}` | Data atual formatada |
| `{responsavel_padrao}` | Responsável padrão (ex: Jhonatas) |
| `{historico_recente}` | Últimas 5 mensagens da conversa |
| `{parametros}` | JSON dos parâmetros extraídos pelo classificador |
| `{registros}` | Registros retornados do banco (Listar) |
| `{candidatos}` | Registros candidatos retornados do RAG (Atualizar/Excluir) |
| `{contexto_rag}` | Registros relevantes retornados do RAG (Conversar) |
| `{mensagem}` | Mensagem original do usuário (Conversar) |
