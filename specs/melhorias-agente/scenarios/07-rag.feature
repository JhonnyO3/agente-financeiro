# language: pt

Funcionalidade: BuscaRAG — 3 faixas MATCH, AMBIGUO, PISO por limiares de Settings
  Como tools Atualizar e Excluir
  Quero que a busca semântica classifique candidatos em faixas bem definidas
  Para determinar se devo prosseguir direto, exibir opções ou informar que não encontrei

  Cenário: 1 candidato com distancia abaixo do piso e gap suficiente retorna MATCH
    Dado um adapter mockado que devolve [(transacao_A, 0.4)] para o embedding da referencia
    E Settings com RAG_PISO=1.0 e RAG_MARGEM=0.15
    Quando chamo BuscaRAG.buscar("zara", usuario_id=1)
    Então ResultadoBusca.faixa é MATCH
    E candidatos contém apenas transacao_A

  Cenário: 2 candidatos proximos entre si retornam AMBIGUO
    Dado um adapter mockado que devolve [(transacao_A, 0.5), (transacao_B, 0.6)] para o embedding
    E Settings com RAG_PISO=1.0 e RAG_MARGEM=0.15 (gap 0.1 < margem)
    Quando chamo BuscaRAG.buscar("internet", usuario_id=1)
    Então ResultadoBusca.faixa é AMBIGUO
    E candidatos contém transacao_A e transacao_B

  Cenário: nenhum candidato abaixo do piso retorna PISO
    Dado um adapter mockado que devolve [] (lista vazia)
    Quando chamo BuscaRAG.buscar("inexistente", usuario_id=1)
    Então ResultadoBusca.faixa é PISO
    E candidatos está vazio

  Cenário: todos os candidatos acima do piso retornam PISO
    Dado um adapter mockado que devolve [(transacao_A, 1.5)] (distancia > RAG_PISO=1.0)
    Quando chamo BuscaRAG.buscar("flores", usuario_id=1)
    Então ResultadoBusca.faixa é PISO

  Cenário: referencia embedada e a extraida pelo classificador nao a mensagem crua
    Dado um Embedder mockado que registra o texto embedado
    Quando chamo BuscaRAG.buscar("zara", usuario_id=1)
    Então o texto enviado ao Embedder é "zara"
    E não é "corrige o valor da zara para 200"

  Cenário: AMBIGUO respeita RAG_MAX_OPCOES
    Dado um adapter mockado que devolve 8 candidatos todos abaixo do piso e proximos entre si
    E Settings com RAG_MAX_OPCOES=5
    Quando chamo BuscaRAG.buscar("gastos", usuario_id=1)
    Então ResultadoBusca.faixa é AMBIGUO
    E candidatos contém no máximo 5 resultados

  Cenário: candidatos sao devolvidos ordenados por distancia crescente
    Dado um adapter mockado que devolve candidatos na ordem [(B, 0.8), (A, 0.3)]
    Quando chamo BuscaRAG.buscar("ref", usuario_id=1)
    Então ResultadoBusca.candidatos está ordenado com distância 0.3 primeiro
