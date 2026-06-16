"""Tests for agent/services/template_loader.py (P04 — TDD)."""
import pytest
from jinja2 import TemplateNotFound


def test_carregar_template_retorna_string_nao_vazia():
    from agent.services.template_loader import carregar_template

    conteudo = carregar_template("menu.md")
    assert isinstance(conteudo, str)
    assert len(conteudo) > 0


def test_renderizar_interpolacao_simples():
    from agent.services.template_loader import renderizar

    resultado = renderizar("listar_vazio.md", {"periodo": "Jun/2026"})
    assert "Jun/2026" in resultado


def test_renderizar_iteracao_lista():
    from agent.services.template_loader import renderizar

    contexto = {
        "periodo": "Jun/2026",
        "grupos": [
            {
                "titulo": "Alimentação",
                "subtotal_fmt": "R$ 150,00",
                "itens": [
                    {
                        "descricao": "Mercado",
                        "valor_fmt": "R$ 100,00",
                        "data_fmt": "10/06",
                        "emoji": "✅",
                        "status": "PAGO",
                    },
                    {
                        "descricao": "Lanche",
                        "valor_fmt": "R$ 50,00",
                        "data_fmt": "12/06",
                        "emoji": "⏳",
                        "status": "PENDENTE",
                    },
                ],
            }
        ],
        "total_fmt": "R$ 150,00",
        "pago_fmt": "R$ 100,00",
        "pendente_fmt": "R$ 50,00",
        "pendente_positivo": True,
    }
    resultado = renderizar("listar_concluido.md", contexto)
    assert "Mercado" in resultado
    assert "Lanche" in resultado
    assert "Alimentação" in resultado


def test_renderizar_condicional_pendente_verdadeiro():
    from agent.services.template_loader import renderizar

    contexto = {
        "periodo": "Jun/2026",
        "grupos": [],
        "total_fmt": "R$ 0,00",
        "pago_fmt": "R$ 0,00",
        "pendente_fmt": "R$ 50,00",
        "pendente_positivo": True,
    }
    resultado = renderizar("listar_concluido.md", contexto)
    assert "R$ 50,00" in resultado
    assert "Pendente" in resultado or "⏳" in resultado


def test_renderizar_condicional_pendente_falso():
    from agent.services.template_loader import renderizar

    contexto = {
        "periodo": "Jun/2026",
        "grupos": [],
        "total_fmt": "R$ 200,00",
        "pago_fmt": "R$ 200,00",
        "pendente_fmt": "R$ 0,00",
        "pendente_positivo": False,
    }
    resultado = renderizar("listar_concluido.md", contexto)
    # A linha de pendente NÃO deve aparecer quando pendente_positivo=False
    assert "⏳" not in resultado or "Pendente" not in resultado


def test_renderizar_sem_linhas_extras_de_blocos():
    """Tags {% %} não devem introduzir linhas em branco extras."""
    from agent.services.template_loader import renderizar

    contexto = {
        "periodo": "Jun/2026",
        "grupos": [
            {
                "titulo": "Cat",
                "subtotal_fmt": "R$ 10,00",
                "itens": [
                    {
                        "descricao": "Item",
                        "valor_fmt": "R$ 10,00",
                        "data_fmt": "01/06",
                        "emoji": "✅",
                        "status": "PAGO",
                    }
                ],
            }
        ],
        "total_fmt": "R$ 10,00",
        "pago_fmt": "R$ 10,00",
        "pendente_fmt": "R$ 0,00",
        "pendente_positivo": False,
    }
    resultado = renderizar("listar_concluido.md", contexto)
    # Não deve haver três ou mais linhas em branco consecutivas introduzidas pelo Jinja
    assert "\n\n\n" not in resultado


def test_template_inexistente_levanta_template_not_found():
    from agent.services.template_loader import renderizar

    with pytest.raises(TemplateNotFound):
        renderizar("nao_existe.md", {})


def test_carregar_template_inexistente_levanta_template_not_found():
    from agent.services.template_loader import carregar_template

    with pytest.raises(TemplateNotFound):
        carregar_template("nao_existe.md")
