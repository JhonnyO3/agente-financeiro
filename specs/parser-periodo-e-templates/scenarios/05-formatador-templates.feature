# language: pt
Funcionalidade: Formatador renderiza via templates externos
  O Formatador monta contexto em Python e delega o layout aos templates, sem regressão de output.

  Cenário: listar concluído produz o mesmo texto de antes
    Dado um ResultadoTool (listar, concluido) com grupos, totais, pendente e pago
    Quando o Formatador formata o resultado
    Então o texto é idêntico ao output atual (cabeçalho, subtotais, total, pendente, pago)
    E os valores monetários estão no formato "R$ X.XXX,YY"

  Cenário: listar vazio produz o mesmo texto de antes
    Dado um ResultadoTool (listar, vazio) com periodo_label "Jun/2026"
    Quando o Formatador formata o resultado
    Então o texto informa que nenhum registro foi encontrado para "Jun/2026"

  Cenário: cadastrar confirmação produz o mesmo texto de antes
    Dado um ResultadoTool (cadastrar, aguardando_confirmacao) com um registro
    Quando o Formatador formata o resultado
    Então o card do registro e o rodapé de confirmação são idênticos ao output atual

  Cenário: menu produz o mesmo texto de antes
    Dado um ResultadoTool (menu, concluido)
    Quando o Formatador formata o resultado
    Então o texto do menu é idêntico ao output atual

  Cenário: conversar permanece passthrough
    Dado um ResultadoTool (conversar, concluido) com resposta "texto livre"
    Quando o Formatador formata o resultado
    Então o texto é exatamente "texto livre" (sem template)

  Cenário: sem strings de layout hardcoded no Formatador
    Dado o módulo agent/services/formatador.py
    Quando inspeciono o arquivo
    Então não há cabeçalho "📊" nem o texto "Confirme o registro" embutidos em Python
    E _brl e o cálculo de emoji permanecem em Python

  Cenário: alterar o template muda o output sem tocar Python
    Dado o template listar_concluido.md alterado
    Quando o Formatador formata um (listar, concluido)
    Então o novo texto reflete a alteração do template
