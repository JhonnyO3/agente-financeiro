# language: pt
Funcionalidade: Frontend em camadas, proxy e layout
  RF-02, RF-03, RF-04.

  Cenário: Proxy repassa ao backend
    Dado o frontend com BACKEND_URL apontando para o backend
    Quando o browser busca /api/resumo na origem do frontend
    Então o frontend chama o backend via httpx e devolve o mesmo JSON e status

  Cenário: Backend indisponível vira 502
    Dado o backend fora do ar
    Quando o frontend tenta proxyar /api/resumo
    Então responde 502 com {"erro": "backend indisponível"}

  Cenário: Layout centralizado e responsivo
    Quando a página é renderizada
    Então o container tem max-width 1400px, margin auto e borda
    E em viewport de 375px não há overflow horizontal

  Cenário: View sem lógica de negócio
    Então o frontend não importa app.repositories nem acessa o banco
