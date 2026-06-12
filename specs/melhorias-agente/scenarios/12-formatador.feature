# language: pt

Funcionalidade: Formatador — ResultadoTool para string WhatsApp via templates Python
  Como worker
  Quero que o Formatador converta qualquer ResultadoTool em texto formatado
  Sem chamar LLM, sem recalcular valores, apenas aplicando templates dos fluxos

  Cenário: cadastrar aguardando_confirmacao exibe card com dados do registro
    Dado um ResultadoTool acao="cadastrar" status="aguardando_confirmacao"
    E dados.registros com descricao="Claude Code", valor=Decimal("472.00"), data=date(2026,6,11), categoria="GASTOS_FIXOS", forma_pagamento="PIX", responsavel="Jhonatas", status="PAGO"
    Quando chamo Formatador.formatar(resultado)
    Então o texto contém "📋 *Confirme o registro abaixo:*"
    E contém "Claude Code"
    E contém "R$ 472,00"
    E contém "confirmar" e "cancelar"

  Cenário: cadastrar aguardando_confirmacao com parcelas exibe secao de parcelas futuras
    Dado um ResultadoTool cadastrar aguardando_confirmacao com parcelas_futuras=["Jul/26","Ago/26"]
    Quando chamo Formatador.formatar(resultado)
    Então o texto contém "📅 Parcelas:"
    E contém "Jul/26" e "Ago/26"

  Cenário: cadastrar concluido unico a-vista exibe confirmacao simples
    Dado um ResultadoTool acao="cadastrar" status="concluido" dados.qtd=1 e descricao "Claude Code" valor Decimal("472.00")
    Quando chamo Formatador.formatar(resultado)
    Então o texto contém "✅ *Registrado com sucesso!*"
    E contém "Claude Code" e "R$ 472,00"

  Cenário: listar concluido exibe agrupamento com subtotais e totais
    Dado um ResultadoTool acao="listar" status="concluido"
    E dados.grupos com GASTOS_FIXOS subtotal Decimal("782.00") e PARCELAMENTOS subtotal Decimal("380.00")
    E dados.total=Decimal("1302.00"), pago=Decimal("1102.00"), pendente=Decimal("200.00")
    Quando chamo Formatador.formatar(resultado)
    Então o texto contém "📊 *Gastos de"
    E contém "_Subtotal: R$ 782,00_" para GASTOS_FIXOS
    E contém "💳 *Total do período: R$ 1.302,00*"
    E contém "⏳ *Pendente: R$ 200,00*"

  Cenário: listar vazio exibe mensagem de nenhum registro
    Dado um ResultadoTool acao="listar" status="vazio" com periodo_label="Jan/2026"
    Quando chamo Formatador.formatar(resultado)
    Então o texto contém "Nenhum registro encontrado"
    E contém "Jan/2026"

  Cenário: atualizar aguardando_confirmacao exibe diff tachado e novo valor
    Dado um ResultadoTool acao="atualizar" status="aguardando_confirmacao"
    E dados.diff com campo="status", antigo="PENDENTE", novo="PAGO"
    E dados.parcelas_afetadas=[]
    Quando chamo Formatador.formatar(resultado)
    Então o texto contém "✏️ *Confirme a atualização:*"
    E contém "~~PENDENTE~~" e "*PAGO*"

  Cenário: atualizar aguardando_confirmacao com parcelas afetadas exibe lista de parcelas
    Dado um ResultadoTool atualizar aguardando_confirmacao com parcelas_afetadas=["Jul/26","Ago/26"]
    Quando chamo Formatador.formatar(resultado)
    Então o texto contém "📅 Parcelas afetadas: Jul/26 · Ago/26"

  Cenário: excluir aguardando_escopo exibe opcoes numeradas 1 e 2
    Dado um ResultadoTool acao="excluir" status="aguardando_escopo"
    E dados.registro com descricao="Batman PS5" e parcelas_futuras=["Jul/26","Ago/26","Set/26"]
    Quando chamo Formatador.formatar(resultado)
    Então o texto contém "*1.* Somente este"
    E contém "*2.* Todos, incluindo as parcelas futuras"
    E contém "Jul/26 · Ago/26 · Set/26"

  Cenário: conversar concluido repassa a resposta sem modificar
    Dado um ResultadoTool acao="conversar" status="concluido" dados.resposta="Vale sim, depende do CET"
    Quando chamo Formatador.formatar(resultado)
    Então o texto é exatamente "Vale sim, depende do CET"

  Cenário: erro concluido exibe mensagem amigavel
    Dado um ResultadoTool acao="erro" status="concluido" dados.mensagem="Ocorreu um erro inesperado."
    Quando chamo Formatador.formatar(resultado)
    Então o texto contém "Ocorreu um erro inesperado."

  Cenário: formatador nao faz nenhuma chamada LLM
    Dado qualquer ResultadoTool válido
    E um spy em criar_llm
    Quando chamo Formatador.formatar(resultado)
    Então criar_llm não foi chamado nenhuma vez
