# language: pt
Funcionalidade: Prompt do classificador documenta o vocabulário de período
  O classificador passa a conhecer todos os valores que o parser entende.

  Cenário: a regra de extração lista o vocabulário completo
    Dado o prompt agent/prompts/01-classificador.md
    Quando leio a regra de extração de "periodo"
    Então constam os valores hoje, ontem, semana_atual, semana_passada, mes_atual, mes_passado, YYYY-MM, YYYY-MM-DD e nome de mês

  Cenário: a tabela de exemplos cobre os novos casos
    Dado o prompt agent/prompts/01-classificador.md
    Quando leio a tabela de exemplos
    Então "quanto eu gastei hoje?" mapeia para periodo="hoje"
    E "o que gastei ontem?" mapeia para periodo="ontem"
    E "gastos dessa semana" mapeia para periodo="semana_atual"
    E "resumo da semana passada" mapeia para periodo="semana_passada"
    E "gastos de maio" mapeia para periodo="2026-05"

  Cenário: o prompt continua carregável via str.format
    Dado o carregamento de prompts em agent/services/prompts.py
    Quando monto o prompt do classificador
    Então não há chaves de template não escapadas que quebrem str.format
