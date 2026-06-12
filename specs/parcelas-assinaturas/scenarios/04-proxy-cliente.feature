# language: pt
Funcionalidade: Proxy Flask e cliente HTTP para os endpoints novos (T04)
  Todas as rotas novas do backend expostas via Flask, seguindo o padrão de repasse
  de status/corpo e 502 quando o backend está indisponível.
  Contrato: frontend-dashboard.md, api-grupos.md, api-gastos-fixos.md.

  # ---------------------------------------------------------------------------
  # PUT /api/grupos/<grupo> — proxy editar grupo
  # ---------------------------------------------------------------------------

  Cenário: PUT /api/grupos repassa status 200 e corpo do backend
    Dado que o backend retorna 200 {"ok": true, "grupo_parcela_id": "grp-aaa", "parcela_total": 4}
    Quando o Flask recebe PUT /api/grupos/grp-aaa com body {"descricao": "Teste", "valor_parcela": "100.00", "proxima_data": "2026-07-05", "parcela_atual": 1, "parcela_total": 4}
    Então a resposta Flask tem status 200
    E o corpo da resposta é {"ok": true, "grupo_parcela_id": "grp-aaa", "parcela_total": 4}
    E o método atualizar_grupo foi chamado com grupo="grp-aaa" e o body correspondente

  Cenário: PUT /api/grupos repassa status 400 do backend
    Dado que o backend retorna 400 {"erro": "ID inválido"}
    Quando o Flask recebe PUT /api/grupos/nao-uuid
    Então a resposta Flask tem status 400
    E o corpo da resposta contém {"erro": "ID inválido"}

  Cenário: PUT /api/grupos repassa status 404 do backend
    Dado que o backend retorna 404 {"erro": "Grupo nao encontrado"}
    Quando o Flask recebe PUT /api/grupos/grp-zzz
    Então a resposta Flask tem status 404
    E o corpo da resposta contém {"erro": "Grupo nao encontrado"}

  Cenário: PUT /api/grupos retorna 502 quando backend está fora do ar
    Dado que o backend lança httpx.HTTPError ao ser chamado
    Quando o Flask recebe PUT /api/grupos/grp-aaa com body válido
    Então a resposta Flask tem status 502
    E o corpo da resposta é {"erro": "backend indisponível"}

  # ---------------------------------------------------------------------------
  # POST /api/grupos — proxy criar grupo
  # ---------------------------------------------------------------------------

  Cenário: POST /api/grupos repassa status 201 e corpo do backend
    Dado que o backend retorna 201 {"ok": true, "grupo_parcela_id": "novo-uuid", "parcela_total": 12}
    Quando o Flask recebe POST /api/grupos com body válido
    Então a resposta Flask tem status 201
    E o corpo da resposta é {"ok": true, "grupo_parcela_id": "novo-uuid", "parcela_total": 12}
    E o método criar_grupo foi chamado com o body correspondente

  Cenário: POST /api/grupos repassa status 400 do backend
    Dado que o backend retorna 400 {"erro": "Campos obrigatorios ausentes: descricao"}
    Quando o Flask recebe POST /api/grupos sem o campo descricao
    Então a resposta Flask tem status 400
    E o corpo da resposta contém {"erro": "Campos obrigatorios ausentes: descricao"}

  Cenário: POST /api/grupos retorna 502 quando backend está fora do ar
    Dado que o backend lança httpx.HTTPError ao ser chamado
    Quando o Flask recebe POST /api/grupos com body válido
    Então a resposta Flask tem status 502
    E o corpo da resposta é {"erro": "backend indisponível"}

  # ---------------------------------------------------------------------------
  # GET /api/gastos-fixos — proxy listar
  # ---------------------------------------------------------------------------

  Cenário: GET /api/gastos-fixos repassa status 200 e corpo do backend
    Dado que o backend retorna 200 {"itens": [{"id": 1, "descricao": "Netflix"}], "total_mensal": "45.90"}
    Quando o Flask recebe GET /api/gastos-fixos
    Então a resposta Flask tem status 200
    E o corpo da resposta contém "itens" e "total_mensal"
    E o método listar_gastos_fixos foi chamado sem argumentos extras

  Cenário: GET /api/gastos-fixos retorna 502 quando backend está fora do ar
    Dado que o backend lança httpx.HTTPError ao ser chamado
    Quando o Flask recebe GET /api/gastos-fixos
    Então a resposta Flask tem status 502
    E o corpo da resposta é {"erro": "backend indisponível"}

  # ---------------------------------------------------------------------------
  # POST /api/gastos-fixos — proxy incluir
  # ---------------------------------------------------------------------------

  Cenário: POST /api/gastos-fixos repassa status 201 e corpo do backend
    Dado que o backend retorna 201 {"id": 42, "ok": true}
    Quando o Flask recebe POST /api/gastos-fixos com body {"descricao": "Spotify", "valor": "19.90", "data": "2026-06-10"}
    Então a resposta Flask tem status 201
    E o corpo da resposta é {"id": 42, "ok": true}
    E o método criar_gasto_fixo foi chamado com o body correspondente

  Cenário: POST /api/gastos-fixos repassa status 400 do backend
    Dado que o backend retorna 400 {"erro": "Campos obrigatorios ausentes: valor"}
    Quando o Flask recebe POST /api/gastos-fixos sem o campo valor
    Então a resposta Flask tem status 400
    E o corpo da resposta contém {"erro": "Campos obrigatorios ausentes: valor"}

  Cenário: POST /api/gastos-fixos retorna 502 quando backend está fora do ar
    Dado que o backend lança httpx.HTTPError ao ser chamado
    Quando o Flask recebe POST /api/gastos-fixos com body válido
    Então a resposta Flask tem status 502
    E o corpo da resposta é {"erro": "backend indisponível"}

  # ---------------------------------------------------------------------------
  # PUT /api/gastos-fixos/<id> — proxy editar
  # ---------------------------------------------------------------------------

  Cenário: PUT /api/gastos-fixos/7 repassa status 200 e corpo do backend
    Dado que o backend retorna 200 {"ok": true}
    Quando o Flask recebe PUT /api/gastos-fixos/7 com body {"descricao": "Novo nome"}
    Então a resposta Flask tem status 200
    E o corpo da resposta é {"ok": true}
    E o método atualizar_gasto_fixo foi chamado com id=7 e o body correspondente

  Cenário: PUT /api/gastos-fixos repassa status 404 do backend
    Dado que o backend retorna 404 {"erro": "Gasto fixo nao encontrado"}
    Quando o Flask recebe PUT /api/gastos-fixos/99
    Então a resposta Flask tem status 404
    E o corpo da resposta contém {"erro": "Gasto fixo nao encontrado"}

  Cenário: PUT /api/gastos-fixos retorna 502 quando backend está fora do ar
    Dado que o backend lança httpx.HTTPError ao ser chamado
    Quando o Flask recebe PUT /api/gastos-fixos/7 com body válido
    Então a resposta Flask tem status 502
    E o corpo da resposta é {"erro": "backend indisponível"}

  # ---------------------------------------------------------------------------
  # DELETE /api/gastos-fixos/<id> — proxy remover
  # ---------------------------------------------------------------------------

  Cenário: DELETE /api/gastos-fixos/5 repassa status 200 e corpo do backend
    Dado que o backend retorna 200 {"ok": true}
    Quando o Flask recebe DELETE /api/gastos-fixos/5
    Então a resposta Flask tem status 200
    E o corpo da resposta é {"ok": true}
    E o método excluir_gasto_fixo foi chamado com id=5

  Cenário: DELETE /api/gastos-fixos repassa status 404 do backend
    Dado que o backend retorna 404 {"erro": "Gasto fixo nao encontrado"}
    Quando o Flask recebe DELETE /api/gastos-fixos/88
    Então a resposta Flask tem status 404
    E o corpo da resposta contém {"erro": "Gasto fixo nao encontrado"}

  Cenário: DELETE /api/gastos-fixos retorna 502 quando backend está fora do ar
    Dado que o backend lança httpx.HTTPError ao ser chamado
    Quando o Flask recebe DELETE /api/gastos-fixos/5
    Então a resposta Flask tem status 502
    E o corpo da resposta é {"erro": "backend indisponível"}

  # ---------------------------------------------------------------------------
  # Garantia de não-regressão na rota existente
  # ---------------------------------------------------------------------------

  Cenário: DELETE /api/grupos/<grupo> existente não é reescrito por T04
    Dado que a rota DELETE /api/grupos/<grupo> já existe no proxy antes da T04
    Quando o Flask recebe DELETE /api/grupos/grp-aaa
    Então a rota é tratada pelo handler original sem conflito com as rotas novas
