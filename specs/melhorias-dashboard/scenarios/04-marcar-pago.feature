# language: pt
# Tarefa: T04 — pytest (mocks)
Funcionalidade: Marcar pago via WhatsApp

  Cenário: Iniciar marca estado e pergunta
    Dado busca semântica encontra transação com distância 0.5
    Quando processo "paguei o jogo do batman"
    Então recebo card de confirmação e estado MARCAR_PAGO salvo

  Cenário: Confirmação positiva atualiza status
    Dado estado MARCAR_PAGO com transacao_id=42
    Quando respondo "sim"
    Então atualizar(42, TransacaoUpdate(status=PAGO)) é chamado e o estado limpo

  Cenário: Negativa cancela
    Quando respondo "não"
    Então nada é atualizado e o estado é limpo

  Cenário: Não encontrado
    Dado distância 1.5 na busca semântica
    Então mensagem de não encontrado e nenhum estado salvo
