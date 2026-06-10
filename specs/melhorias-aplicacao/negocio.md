1. Gráfico de Evolução — Linha de Receitas
Adicione uma linha de receitas no gráfico de evolução mensal, alongside a linha de gastos existente. A linha deve seguir o mesmo padrão visual do gráfico atual, com cor e legenda distintas.
2. Layout — Largura máxima e centralização
O painel atual usa width: 100% e fica ilegível em monitores grandes. Aplique uma largura máxima de 1400px no container principal, centralize o conteúdo horizontalmente com margin: 0 auto e adicione padding lateral adequado. Adicione uma borda sutil ao container para delimitar a área de leitura.
3. Performance das APIs — Migração para FastAPI
As APIs estão respondendo em ~5s, inaceitável. O target é abaixo de 1s.

Migre todas as APIs para FastAPI
Crie uma pasta backend/ com as seguintes camadas:

controllers/ — routers FastAPI, sem lógica de negócio
services/ — orquestração e regras de negócio
dtos/ — schemas Pydantic de entrada e saída
entities/ — modelos de domínio ricos

Siga as convenções do agente python-dev: uv, pydantic, ruff, logging com INFO/DEBUG, sem comentários no código, sem lógica nos controllers.
Antes de implementar, rode as rotas atuais localmente, meça o tempo de resposta e identifique o gargalo. Documente o motivo da lentidão como um log INFO na inicialização.

1. Refatoração do Frontend Flask
O frontend foi construído como um módulo monolítico em Flask. Separe-o em camadas dentro de uma pasta frontend/ com a seguinte estrutura:

blueprints/ — um Blueprint por funcionalidade (ex: dashboard, lancamentos, relatorios)
services/ — lógica de chamada ao backend (HTTP client com httpx, sem lógica de negócio no blueprint)
templates/ — Jinja2 organizados por blueprint, espelhando a estrutura de blueprints/
static/ — assets separados por tipo (css/, js/, img/)
config.py — configurações via pydantic-settings
Nenhuma lógica de negócio nas views; as views apenas recebem dados do service e passam ao template.

1. Tabela de Evolução e Gastos Mensais — Projeção completa
A tabela deve exibir sempre uma janela de 13 meses: 6 meses anteriores ao mês atual, o mês atual e 6 meses futuros. Meses passados exibem dados reais, meses futuros exibem projeção com base nos parcelamentos e receitas já registrados.
2. Script de inicialização unificado
Crie um arquivo start.py na raiz do projeto que sobe o frontend e o backend simultaneamente em portas separadas (ex: frontend :5000, backend :8000) com um único comando. Use subprocess para orquestrar os dois processos. Exiba os logs de ambos no mesmo terminal com prefixo identificando a origem ([frontend], [backend]). Em caso de CTRL+C, encerre ambos os processos de forma limpa.
