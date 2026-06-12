import os
from decimal import Decimal

import pytest
from pydantic import ValidationError

# Importa os módulos de domínio — ImportError é o vermelho esperado antes da implementação
from agent.domain.intencao import (
    Acao,
    Intencao,
    ItemCadastro,
    ParamsCadastrar,
    ParamsListar,
    ParamsAtualizar,
    ParamsExcluir,
    ParamsSelecionar,
    ParamsComplementar,
    ParamsVazio,
)
from agent.domain.resultado import ResultadoTool


# ---------------------------------------------------------------------------
# Fixtures dos 17 exemplos de classificador.md
# ---------------------------------------------------------------------------

# Cada entrada: (id_exemplo, payload_dict)
EXEMPLOS_CLASSIFICADOR = [
    (
        "gastei_472_claude_code",
        {
            "acao": "cadastrar",
            "parametros": {"itens": [{"descricao": "Claude Code", "valor": 472}]},
            "confianca": 0.98,
        },
    ),
    (
        "140_flores_190_internet",
        {
            "acao": "cadastrar",
            "parametros": {
                "itens": [
                    {"descricao": "Flores", "valor": 140},
                    {"descricao": "Internet", "valor": 190, "data": "ontem"},
                ]
            },
            "confianca": 0.96,
        },
    ),
    (
        "listar_gastos",
        {
            "acao": "listar",
            "parametros": {"periodo": "mes_atual"},
            "confianca": 0.99,
        },
    ),
    (
        "quanto_gastei_esse_mes",
        {
            "acao": "listar",
            "parametros": {"periodo": "mes_atual"},
            "confianca": 0.97,
        },
    ),
    (
        "estou_no_azul",
        {
            "acao": "listar",
            "parametros": {"periodo": "mes_atual"},
            "confianca": 0.92,
        },
    ),
    (
        "vale_a_pena_parcelar",
        {
            "acao": "conversar",
            "parametros": {},
            "confianca": 0.93,
        },
    ),
    (
        "corrige_valor_zara",
        {
            "acao": "atualizar",
            "parametros": {"referencia": "zara", "campo": "valor", "novo_valor": "200"},
            "confianca": 0.96,
        },
    ),
    (
        "paguei_a_internet",
        {
            "acao": "atualizar",
            "parametros": {"referencia": "internet", "campo": "status", "novo_valor": "PAGO"},
            "confianca": 0.94,
        },
    ),
    (
        "apaga_gasto_flores",
        {
            "acao": "excluir",
            "parametros": {"referencia": "flores"},
            "confianca": 0.95,
        },
    ),
    (
        "apaga_tudo_de_maio",
        {
            "acao": "excluir",
            "parametros": {"periodo": "2026-05"},
            "confianca": 0.95,
        },
    ),
    (
        "confirmar",
        {
            "acao": "confirmar",
            "parametros": {},
            "confianca": 0.99,
        },
    ),
    (
        "nao_deixa_cancelar",
        {
            "acao": "cancelar",
            "parametros": {},
            "confianca": 0.98,
        },
    ),
    (
        "selecionar_opcao_2",
        {
            "acao": "selecionar",
            "parametros": {"opcao": 2},
            "confianca": 0.99,
        },
    ),
    (
        "todos_selecionar_opcao_2",
        {
            "acao": "selecionar",
            "parametros": {"opcao": 2},
            "confianca": 0.97,
        },
    ),
    (
        "foi_350_complementar_valor",
        {
            "acao": "complementar",
            "parametros": {"campo": "valor", "valor": "350"},
            "confianca": 0.97,
        },
    ),
    (
        "em_3x_complementar_parcelas",
        {
            "acao": "complementar",
            "parametros": {"campo": "parcelas", "valor": "3"},
            "confianca": 0.97,
        },
    ),
    (
        "me_conta_uma_piada_desconhecida",
        {
            "acao": "desconhecida",
            "parametros": {},
            "confianca": 0.99,
        },
    ),
]


# ---------------------------------------------------------------------------
# Mapeamento acao → tipo de parametros esperado
# ---------------------------------------------------------------------------

TIPO_POR_ACAO = {
    "cadastrar": ParamsCadastrar,
    "listar": ParamsListar,
    "atualizar": ParamsAtualizar,
    "excluir": ParamsExcluir,
    "conversar": ParamsVazio,
    "confirmar": ParamsVazio,
    "cancelar": ParamsVazio,
    "selecionar": ParamsSelecionar,
    "complementar": ParamsComplementar,
    "desconhecida": ParamsVazio,
}


# ---------------------------------------------------------------------------
# Cenário: os 17 exemplos do classificador.md são instâncias válidas de Intencao
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("exemplo_id,payload", EXEMPLOS_CLASSIFICADOR, ids=[e[0] for e in EXEMPLOS_CLASSIFICADOR])
def test_exemplos_classificador_sao_intencoes_validas(exemplo_id, payload):
    intencao = Intencao.model_validate(payload)
    assert intencao.acao == payload["acao"]
    tipo_esperado = TIPO_POR_ACAO[intencao.acao]
    assert isinstance(intencao.parametros, tipo_esperado), (
        f"[{exemplo_id}] esperava {tipo_esperado.__name__}, "
        f"obteve {type(intencao.parametros).__name__}"
    )


# ---------------------------------------------------------------------------
# Cenário: instanciar Intencao de cadastro simples
# ---------------------------------------------------------------------------

def test_intencao_cadastro_simples():
    payload = {
        "acao": "cadastrar",
        "parametros": {"itens": [{"descricao": "Claude Code", "valor": 472}]},
        "confianca": 0.98,
    }
    intencao = Intencao.model_validate(payload)
    assert intencao.acao == "cadastrar"
    assert isinstance(intencao.parametros, ParamsCadastrar)
    assert len(intencao.parametros.itens) == 1


# ---------------------------------------------------------------------------
# Cenário: instanciar Intencao de listagem com período
# ---------------------------------------------------------------------------

def test_intencao_listar_com_periodo():
    payload = {
        "acao": "listar",
        "parametros": {"periodo": "mes_atual"},
        "confianca": 0.99,
    }
    intencao = Intencao.model_validate(payload)
    assert isinstance(intencao.parametros, ParamsListar)
    assert intencao.parametros.periodo == "mes_atual"


# ---------------------------------------------------------------------------
# Cenário: parâmetros do tipo errado para a ação falham validação (union discriminada)
# ---------------------------------------------------------------------------

def test_parametros_tipo_errado_para_acao_levanta_validation_error():
    # acao="listar" mas parametros têm shape de ParamsCadastrar
    payload = {
        "acao": "listar",
        "parametros": {"itens": [{"descricao": "Claude Code", "valor": 472}]},
        "confianca": 0.9,
    }
    with pytest.raises(ValidationError):
        Intencao.model_validate(payload)


# ---------------------------------------------------------------------------
# Cenário: valor monetário em ItemCadastro é armazenado como Decimal
# ---------------------------------------------------------------------------

def test_item_cadastro_valor_float_vira_decimal():
    item = ItemCadastro(valor=472.0)
    assert isinstance(item.valor, Decimal)


def test_item_cadastro_valor_int_vira_decimal():
    item = ItemCadastro(valor=472)
    assert isinstance(item.valor, Decimal)


def test_item_cadastro_valor_string_numerica_vira_decimal():
    item = ItemCadastro(valor="350")
    assert isinstance(item.valor, Decimal)
    assert item.valor == Decimal("350")


# ---------------------------------------------------------------------------
# Cenário: ParamsSelecionar exige opcao inteiro positivo
# ---------------------------------------------------------------------------

def test_selecionar_opcao_inteiro():
    payload = {
        "acao": "selecionar",
        "parametros": {"opcao": 2},
        "confianca": 0.99,
    }
    intencao = Intencao.model_validate(payload)
    assert isinstance(intencao.parametros, ParamsSelecionar)
    assert intencao.parametros.opcao == 2


# ---------------------------------------------------------------------------
# Cenário: ResultadoTool aceita todos os pares (acao, status) do contrato
# ---------------------------------------------------------------------------

PARES_ACAO_STATUS_VALIDOS = [
    # cadastrar
    ("cadastrar", "aguardando_confirmacao", {"registros": [], "campos_faltantes": [], "parcelas_futuras": []}),
    ("cadastrar", "aguardando_complemento", {"registros": [], "campos_faltantes": ["valor"], "parcelas_futuras": []}),
    ("cadastrar", "concluido", {"registros_salvos": [], "qtd": 0}),
    # listar
    ("listar", "concluido", {"periodo_label": "Jun/2026", "grupos": [], "total": Decimal("0"), "pago": Decimal("0"), "pendente": Decimal("0")}),
    ("listar", "vazio", {"periodo_label": "Jun/2026", "grupos": [], "total": Decimal("0"), "pago": Decimal("0"), "pendente": Decimal("0")}),
    # atualizar
    ("atualizar", "aguardando_selecao", {"opcoes": []}),
    ("atualizar", "aguardando_confirmacao", {"registro": {}, "diff": {"campo": "valor", "antigo": "100", "novo": "200"}, "parcelas_afetadas": []}),
    ("atualizar", "nao_encontrado", {"referencia": "zara"}),
    ("atualizar", "concluido", {"descricao": "Zara", "propagou_parcelas": False}),
    # excluir
    ("excluir", "aguardando_selecao", {"opcoes": [], "modo": "individual"}),
    ("excluir", "aguardando_escopo", {"registro": {}, "parcelas_futuras": []}),
    ("excluir", "aguardando_confirmacao", {"registro": {}}),
    ("excluir", "nao_encontrado", {"referencia": "flores"}),
    ("excluir", "concluido", {"descricao": "Flores", "valor": Decimal("100"), "parcelas_removidas": 1}),
    # conversar
    ("conversar", "concluido", {"resposta": "Olá!"}),
    # menu
    ("menu", "concluido", {}),
    # erro
    ("erro", "concluido", {"mensagem": "Erro inesperado."}),
]


@pytest.mark.parametrize(
    "acao,status,dados",
    PARES_ACAO_STATUS_VALIDOS,
    ids=[f"{a}-{s}" for a, s, _ in PARES_ACAO_STATUS_VALIDOS],
)
def test_resultado_tool_pares_validos(acao, status, dados):
    resultado = ResultadoTool(acao=acao, status=status, dados=dados)
    assert resultado.acao == acao
    assert resultado.status == status


# ---------------------------------------------------------------------------
# Cenário: acao inválida em ResultadoTool levanta ValidationError
# ---------------------------------------------------------------------------

def test_resultado_tool_acao_invalida():
    with pytest.raises(ValidationError):
        ResultadoTool(acao="acao_inexistente", status="concluido", dados={})


def test_resultado_tool_status_invalido():
    with pytest.raises(ValidationError):
        ResultadoTool(acao="cadastrar", status="status_inexistente", dados={})
