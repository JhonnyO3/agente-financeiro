Requisito de Negócio — Controle Financeiro Pessoal
RN-01 — Projeção futura de parcelamentos
Problema atual: ao registrar um gasto parcelado (ex.: 2/4), apenas a parcela informada é gravada. As parcelas seguintes não aparecem, então a projeção de meses futuros fica incompleta.

Regra: quando o usuário informar um gasto parcelado com (a) valor da parcela, (b) quantidade total de parcelas, (c) parcela atual e (d) dia de vencimento, o sistema deve gerar automaticamente um registro para cada parcela restante, projetando-as nos meses subsequentes.

Exemplo: entrada 10/06/2026 – jogo batman play 5 – R$ 200,00 – 2/4 deve gerar:

Data Nome Categoria Valor Parcela Tipo Status
10/06/2026 jogo batman play 5 PARCELAMENTOS R$ 200,00 2/4 GASTO PENDENTE
10/07/2026 jogo batman play 5 PARCELAMENTOS R$ 200,00 3/4 GASTO PENDENTE
10/08/2026 jogo batman play 5 PARCELAMENTOS R$ 200,00 4/4 GASTO PENDENTE
(parcela 1/4, se já vencida, registrada como histórico). O dia de vencimento é mantido em todas as parcelas, avançando o mês.

Aceite: revisar todos os registros existentes e completar as parcelas faltantes dos lançamentos já feitos.

RN-02 — Status de pagamento
Regra: todo lançamento deve ter um campo Status com dois valores possíveis: PAGO ou PENDENTE.

Pagamentos via PIX entram automaticamente como PAGO.
Demais formas (cartão, parcelamentos futuros) entram como PENDENTE por padrão, podendo ser atualizadas.
RN-03 — Campo Responsável
Regra: novo campo Responsável para identificar de quem é o gasto, já que terceiros (mãe, namorada) às vezes lançam no seu cartão.

Se o responsável não for informado, o padrão é Jhonatas.
RN-04 — Novas categorias
Ampliar a lista de categorias para incluir, além das existentes:

RECEITA
OUTROS
PARCELAMENTOS
RN-05 — Campo Descrição enriquecido
Regra: manter o campo Nome curto (já está adequado). O campo Descrição deve ser preenchido pela IA usando como referência o detalhamento fornecido pelo usuário, capturando o contexto adicional informado.

RN-06 — Feature de Receitas
Regra: permitir o cadastro de receitas (não só gastos), usando a categoria RECEITA / tipo RECEITA, para compor o balanço (receitas − gastos).

RN-07 — Visões mensal e projetada
O sistema deve oferecer simultaneamente:

Controle mensal — gastos e receitas consolidados por mês corrente.
Projeção futura — soma das parcelas e lançamentos já agendados para os próximos meses, permitindo enxergar o comprometimento financeiro futuro.
Estrutura de dados resultante (modelo de registro)
Campo Obrigatório Regra/Padrão
Data Sim Data do lançamento / vencimento
Nome Sim Curto
Descrição Não Preenchido pela IA a partir do detalhe do usuário
Categoria Sim inclui RECEITA, OUTROS, PARCELAMENTOS
Valor Sim —
Parcela Não formato atual/total; dispara RN-01
Tipo Sim GASTO ou RECEITA
Status Sim PAGO / PENDENTE (PIX = PAGO)
Responsável Sim padrão Jhonatas
