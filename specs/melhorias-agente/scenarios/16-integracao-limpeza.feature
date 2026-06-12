# language: pt

Funcionalidade: Integracao, wiring e remocao de modulos antigos
  Como equipe de desenvolvimento
  Quero que o main.py suba com todos os componentes novos injetados
  E que nenhum módulo antigo de agent/ permaneça importado na suíte de testes

  Cenário: suíte completa de testes passa sem erros apos integracao
    Dado todos os módulos novos implementados (T01 a T15)
    Quando executo "uv run pytest tests/ -v"
    Então todos os testes passam (exit code 0)
    E nenhum teste exibe ImportError ou ModuleNotFoundError

  Cenário: nenhum import de modulo antigo permanece em agent/ ou tests/
    Dado a árvore de código após T16
    Quando executo grep buscando padrões de módulos removidos
    Então agent.services.pipeline não aparece em nenhum arquivo
    E confirmacao_chain não aparece em nenhum arquivo
    E agent.db não aparece em nenhum arquivo
    E services.cadastrar (serviço antigo) não aparece em nenhum arquivo
    E entrypoint.debounce não aparece em nenhum arquivo

  Cenário: app sobe via lifespan sem erro de wiring
    Dado main.py com lifespan reescrito injetando Relogio, EstadoStoreMemoria, Embedder, BuscaRAG, ToolCadastrar, ToolListar, ToolAtualizar, ToolExcluir, ToolConversar, Formatador, Classificador, Roteador, Worker
    Quando o FastAPI inicia o lifespan
    Então app.state contém todos os componentes sem AttributeError
    E nenhum Depends() global é usado

  Cenário: test_parcelas_helper importa de agent.tools._parcelas apos migracao
    Dado tests/test_parcelas_helper.py atualizado
    Quando o teste é importado
    Então o import aponta para agent.tools._parcelas
    E agent.services.parcelas nao e importado

  Cenário: test_webhook_worker cobre a nova auth e fila
    Dado tests/test_webhook_worker.py implementado
    Quando executo os testes desse arquivo
    Então os cenários de 401, dedup e debounce passam
    E o arquivo antigo test_webhook.py foi removido ou substituído

  Cenário: 1 worker documentado como invariante no config
    Dado agent/config.py apos T16
    Quando leio o arquivo
    Então existe um comentário ou docstring mencionando a invariante de 1 worker uvicorn
