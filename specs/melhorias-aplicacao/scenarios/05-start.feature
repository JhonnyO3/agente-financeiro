# language: pt
Funcionalidade: Script de inicialização unificado
  RF-06.

  Cenário: Sobe os dois serviços
    Quando executo uv run python start.py
    Então o backend sobe em :8000 e o frontend em :5000
    E os logs aparecem prefixados por [backend] e [frontend]

  Cenário: Encerramento limpo
    Dado os dois serviços rodando via start.py
    Quando envio CTRL+C
    Então backend e frontend encerram sem deixar processo órfão
