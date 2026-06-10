# language: pt
# Tarefa: T10 — pytest (repository mockado, funções puras)
Funcionalidade: Backfill de parcelas

  Cenário: Completa grupo incompleto
    Dado grupo com parcela_total=4 contendo apenas a parcela 2 (10/06/2026)
    Quando rodo o backfill
    Então cria as parcelas 1 (10/05, PAGO), 3 (10/07, PENDENTE) e 4 (10/08, PENDENTE)
    E copia valor, descricao, categoria e embedding do grupo

  Cenário: Idempotência
    Dado grupo já completo
    Quando rodo o backfill
    Então nenhuma parcela é criada

  Cenário: Grupo ambíguo é pulado
    Dado grupo com valores divergentes entre parcelas
    Quando rodo o backfill
    Então o grupo fica intacto e aparece no relatório com o motivo

  Cenário: Dry-run não grava
    Quando rodo com --dry-run
    Então criar_lote nunca é chamado e o relatório lista o que seria feito
