# language: pt
Funcionalidade: Separação de módulos (app/ → backend/ + agent/)

  Como desenvolvedor do sistema
  Quero dividir o antigo pacote app/ — camada de dados para backend/, orquestração para agent/
  Para que os 3 módulos (frontend, backend, agent) tenham responsabilidades nítidas

  Contexto:
    Dado que os contratos estão congelados
    E a branch atual possui o diretório app/ com a estrutura entrypoint/, agents/, services/, repositories/, models/, integrations/, config.py

  Cenário: Diretório app/ não existe mais após a separação
    Dado que a separação foi aplicada
    Quando verifico a raiz do repositório
    Então o diretório app/ não existe

  Cenário: A camada de dados passa a viver em backend/
    Dado que a separação foi aplicada
    Quando inspeciono o módulo backend/
    Então backend/models/ contém transacao.py e enums.py
    E a classe Base declarativa está em backend/models/transacao.py
    E backend/repositories/ contém transacao_repository.py e dtos.py

  Cenário: A orquestração do agente vive em agent/ e consome a camada de dados do backend
    Dado que a separação foi aplicada
    Quando inspeciono o módulo agent/
    Então agent/ contém entrypoint/, agents/, services/, integrations/, config.py
    E o engine helper do agente está em agent/db.py usando agent.config
    E os imports de dados no agente referenciam "backend.models" e "backend.repositories"

  Cenário: Suite de testes passa sem nenhum import ao pacote app.
    Dado que a separação foi aplicada
    Quando executo "uv run pytest tests/ -v"
    Então todos os testes passam
    E nenhum teste importa o namespace "app."

  Cenário: Nenhum arquivo de código ou configuração referencia o pacote antigo
    Dado que a separação foi aplicada
    Quando faço busca recursiva por "from app" e "app." em código, scripts e configurações
    Então o resultado é vazio (zero ocorrências do pacote antigo)

  Cenário: Alembic enxerga a metadata a partir de backend.models.transacao
    Dado que migrations/env.py importa "from backend.models.transacao import Base"
    Quando executo "uv run alembic upgrade head"
    Então a migration é aplicada com sucesso sem erro de importação
    E a metadata contém a tabela transacoes

  Cenário: start.py aponta para agent.entrypoint.main:app
    Dado que a separação foi aplicada
    Quando leio a variável AGENTE_CMD em start.py
    Então o valor é "agent.entrypoint.main:app"
    E não contém "app.entrypoint.main:app"

  Cenário: pyproject.toml declara os pacotes agent, backend e frontend e não app
    Dado que a separação foi aplicada
    Quando leio o campo packages em pyproject.toml
    Então o valor inclui "agent", "backend" e "frontend"
    E não inclui "app"

  Cenário: tests/test_start.py afirma o literal correto após a separação
    Dado que a separação foi aplicada
    Quando leio a asserção do literal no teste test_start.py
    Então o literal verificado é "agent.entrypoint.main:app"
    E não há asserção sobre "app.entrypoint.main:app"

  Cenário: Nenhuma mudança de comportamento observável após a separação
    Dado que a separação foi aplicada
    E o banco de dados está atualizado
    Quando o agente recebe uma mensagem de texto válida pelo webhook
    Então a resposta é idêntica à resposta anterior à separação
    E nenhuma exceção de importação é lançada
