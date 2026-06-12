# language: pt

Funcionalidade: Método aditivo buscar_semantico_multiplos_com_distancia no repository
  Como serviço RAG
  Quero buscar até N candidatos com distância L2 ordenada
  Para que a lógica de faixas MATCH/AMBIGUO/PISO funcione com múltiplos resultados

  Cenário: busca retorna candidatos ordenados por distancia crescente
    Dado um repository mockado com 3 transações e distâncias [0.5, 0.8, 1.2] para o embedding dado
    Quando chamo buscar_semantico_multiplos_com_distancia(embedding, limite=5, usuario_id=1)
    Então recebo uma lista de 3 tuplas (Transacao, float)
    E as distâncias estão em ordem crescente [0.5, 0.8, 1.2]

  Cenário: busca respeita o limite informado
    Dado um repository mockado com 5 transações candidatas
    Quando chamo buscar_semantico_multiplos_com_distancia(embedding, limite=2, usuario_id=1)
    Então recebo no máximo 2 resultados

  Cenário: busca filtra por usuario_id
    Dado um repository com transações de usuario_id=1 e usuario_id=2
    Quando chamo buscar_semantico_multiplos_com_distancia(embedding, limite=5, usuario_id=1)
    Então todos os resultados têm usuario_id=1
    E nenhum resultado tem usuario_id=2

  Cenário: busca sem usuario_id devolve candidatos de todos os usuarios
    Dado um repository com transações de usuario_id=1 e usuario_id=2
    Quando chamo buscar_semantico_multiplos_com_distancia(embedding, limite=5, usuario_id=None)
    Então os resultados podem conter transações de ambos os usuários

  Cenário: busca sem candidatos retorna lista vazia
    Dado um repository mockado sem nenhuma transação
    Quando chamo buscar_semantico_multiplos_com_distancia(embedding, limite=5, usuario_id=1)
    Então recebo uma lista vazia

  Cenário: metodo existente buscar_semantico_com_distancia permanece inalterado
    Dado o TransacaoRepository com o método buscar_semantico_com_distancia existente
    Quando inspeciono a assinatura do método
    Então a assinatura original não foi alterada
    E o método ainda retorna apenas 1 resultado via .first()

  Cenário: adapter expoe o metodo novo com usuario_id fixo da instancia
    Dado um adapter com usuario_id=42 fixado
    Quando chamo buscar_semantico_multiplos_com_distancia no adapter com um embedding
    Então o repository subjacente é chamado com usuario_id=42
