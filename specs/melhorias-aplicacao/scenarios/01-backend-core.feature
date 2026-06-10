# language: pt
Funcionalidade: Backend FastAPI com engine pooled
  RF-01.

  Cenário: App sobe e responde health
    Dado o app FastAPI do backend
    Quando faço GET em /health
    Então recebo status 200 e corpo {"ok": true}

  Cenário: Engine é criado uma única vez
    Dado o backend inicializado
    Quando dois requests consecutivos são atendidos
    Então o engine não é recriado por request (mesmo sessionmaker em app.state)

  Cenário: Log de startup documenta o gargalo
    Quando o backend inicia
    Então um log INFO menciona a reconexão por request anterior e o pool reusado
