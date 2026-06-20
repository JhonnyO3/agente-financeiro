# Regras de desenvolvimento do projeto agente-financeiro

TYPING = """
- Proibido usar `Any` de typing. Sempre use o tipo concreto ou defina um Protocol.
- Proibido usar `| None` ou `Optional[X]` em parâmetros — torne o argumento obrigatório
  ou modele a ausência com um tipo explícito (ex: Protocol, valor sentinela).
- Prefira Protocol a classes abstratas para contratos entre camadas.
- Imports que disparam carregamento de config (ex: services que importam agent.config)
  devem ficar sob `if TYPE_CHECKING:` para não quebrar testes que não setam env vars.
"""

ARQUITETURA = """
- Nenhuma lógica de negócio em agent/entrypoint/ — apenas orquestração e wiring.
- Serviços (agent/services/) não importam de entrypoint/.
- Math financeiro sempre em Decimal, nunca delegado ao LLM.
- Repositórios recebem AsyncSession por injeção — nunca criam sessão própria.
"""

DEPENDENCIAS = """
- Gerenciador de pacotes: sempre `uv`. Nunca `pip` ou `poetry`.
- uv.lock é commitado e deve ser mantido atualizado.
"""

TESTES = """
- Sem chamadas reais a banco ou LLM nos testes — apenas mocks.
- Imports do projeto dentro de funções de teste quando há risco de falha na
  validação de settings antes das env vars serem setadas.
"""

ESTILO = """
- Sem comentários que expliquem O QUE o código faz — nomes devem ser autoexplicativos.
- Comentários apenas para invariantes não óbvias, workarounds ou restrições ocultas.
- Sem docstrings longas — uma linha no máximo quando necessário.
"""
