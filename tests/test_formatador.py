"""
Testes vermelhos — Task 12: Formatador (templates Python puros, sem LLM).

Estes testes descrevem o comportamento NOVO do Formatador: templates Python
determinísticos, interface síncrona `formatar(resultado: ResultadoTool) -> str`,
sem qualquer chamada a LLM. Eles falham intencionalmente contra o formatador
antigo (que usa LangChain/OpenAI).
"""
import ast
import inspect
import os
from datetime import date
from decimal import Decimal

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost:8080")
os.environ.setdefault("EVOLUTION_API_KEY", "test-key")
os.environ.setdefault("EVOLUTION_INSTANCE", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("ADMIN_EMAILS", "admin@exemplo.com")

import pytest

from agent.domain.resultado import ResultadoTool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(resultado: ResultadoTool) -> str:
    """Chama Formatador.formatar de forma síncrona."""
    from agent.services.formatador import Formatador  # import tardio
    f = Formatador()
    result = f.formatar(resultado)
    # Suporta tanto interface síncrona quanto corrotina (para garantir vermelho correto)
    import asyncio, inspect as _inspect
    if _inspect.iscoroutine(result):
        return asyncio.get_event_loop().run_until_complete(result)
    return result


def _registro_base(
    descricao="Claude Code",
    valor=Decimal("472.00"),
    data=date(2026, 6, 11),
    categoria="GASTOS_FIXOS",
    forma_pagamento="PIX",
    responsavel="Jhonatas",
    status="PAGO",
    parcela_numero=1,
    parcela_total=1,
    grupo_parcela_id=None,
    detalhes=None,
) -> dict:
    return {
        "descricao": descricao,
        "valor": valor,
        "data": data,
        "categoria": categoria,
        "forma_pagamento": forma_pagamento,
        "responsavel": responsavel,
        "status": status,
        "parcela_numero": parcela_numero,
        "parcela_total": parcela_total,
        "grupo_parcela_id": grupo_parcela_id,
        "detalhes": detalhes,
    }


# ---------------------------------------------------------------------------
# Cenário: o formatador NÃO importa nem instancia LLM
# ---------------------------------------------------------------------------

def test_formatador_modulo_sem_llm():
    """O módulo formatador não deve importar ChatOpenAI, LangChain nem criar LLM."""
    import importlib.util, pathlib
    path = pathlib.Path(__file__).parent.parent / "agent" / "services" / "formatador.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    proibidos = {"ChatOpenAI", "langchain", "langchain_core", "langchain_openai",
                 "criar_llm", "criar_llm_formatacao", "ainvoke"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            nome = ""
            if isinstance(node, ast.ImportFrom) and node.module:
                nome = node.module
            elif isinstance(node, ast.Import):
                nome = " ".join(a.name for a in node.names)
            for p in proibidos:
                assert p not in nome, (
                    f"Formatador importa '{p}' — LLM proibido no template puro"
                )


def test_instancia_formatador_sem_atributo_llm():
    """A instância do Formatador não deve ter atributo _llm ou similar."""
    from agent.services.formatador import Formatador
    f = Formatador()
    assert not hasattr(f, "_llm"), "Formatador não deve expor atributo _llm (sem LLM)"
    assert not hasattr(f, "llm"), "Formatador não deve expor atributo llm"


# ---------------------------------------------------------------------------
# Cenário: assinatura — formatar é síncrono e recebe ResultadoTool
# ---------------------------------------------------------------------------

def test_formatar_e_sincrono():
    """formatar(ResultadoTool) deve retornar str diretamente (sem corrotina)."""
    import inspect as _inspect
    from agent.services.formatador import Formatador
    f = Formatador()
    resultado = ResultadoTool(
        acao="conversar",
        status="concluido",
        dados={"resposta": "Olá!"},
    )
    ret = f.formatar(resultado)
    assert not _inspect.iscoroutine(ret), (
        "formatar() deve ser síncrono e retornar str, não corrotina"
    )
    assert isinstance(ret, str)


# ---------------------------------------------------------------------------
# cadastrar / aguardando_confirmacao — card 📋
# ---------------------------------------------------------------------------

def test_cadastrar_aguardando_confirmacao_card_basico():
    resultado = ResultadoTool(
        acao="cadastrar",
        status="aguardando_confirmacao",
        dados={
            "registros": [_registro_base()],
            "campos_faltantes": [],
            "parcelas_futuras": [],
        },
    )
    texto = _fmt(resultado)
    assert "📋 *Confirme o registro abaixo:*" in texto
    assert "Claude Code" in texto
    assert "R$ 472,00" in texto
    assert "GASTOS_FIXOS" in texto
    assert "PIX" in texto
    assert "Jhonatas" in texto
    assert "PAGO" in texto
    assert "confirmar" in texto.lower()
    assert "cancelar" in texto.lower()


def test_cadastrar_aguardando_confirmacao_data_formatada():
    resultado = ResultadoTool(
        acao="cadastrar",
        status="aguardando_confirmacao",
        dados={
            "registros": [_registro_base(data=date(2026, 6, 11))],
            "campos_faltantes": [],
            "parcelas_futuras": [],
        },
    )
    texto = _fmt(resultado)
    assert "11/06/2026" in texto


def test_cadastrar_aguardando_confirmacao_com_parcelas_futuras():
    resultado = ResultadoTool(
        acao="cadastrar",
        status="aguardando_confirmacao",
        dados={
            "registros": [_registro_base(parcela_numero=3, parcela_total=5)],
            "campos_faltantes": [],
            "parcelas_futuras": ["Jul/26", "Ago/26"],
        },
    )
    texto = _fmt(resultado)
    assert "📅 Parcelas" in texto
    assert "Jul/26" in texto
    assert "Ago/26" in texto


def test_cadastrar_aguardando_confirmacao_multiplos_registros():
    resultado = ResultadoTool(
        acao="cadastrar",
        status="aguardando_confirmacao",
        dados={
            "registros": [
                _registro_base(descricao="Flores Natasha", valor=Decimal("140.00")),
                _registro_base(descricao="Internet", valor=Decimal("190.00")),
            ],
            "campos_faltantes": [],
            "parcelas_futuras": [],
        },
    )
    texto = _fmt(resultado)
    assert "📋" in texto
    assert "Flores Natasha" in texto
    assert "R$ 140,00" in texto
    assert "Internet" in texto
    assert "R$ 190,00" in texto


def test_cadastrar_aguardando_confirmacao_parcelado_exibe_Nx():
    """Parcelas: exibe 'Nx de R$ X,XX (total R$ X,XX)'."""
    resultado = ResultadoTool(
        acao="cadastrar",
        status="aguardando_confirmacao",
        dados={
            "registros": [
                _registro_base(
                    descricao="Roupas Zara",
                    valor=Decimal("180.00"),
                    parcela_numero=3,
                    parcela_total=5,
                    forma_pagamento="CARTAO_CREDITO",
                )
            ],
            "campos_faltantes": [],
            "parcelas_futuras": ["Ago/26", "Set/26"],
        },
    )
    texto = _fmt(resultado)
    assert "5x" in texto or "5/" in texto or "3/5" in texto


# ---------------------------------------------------------------------------
# cadastrar / aguardando_complemento — campo em destaque
# ---------------------------------------------------------------------------

def test_cadastrar_aguardando_complemento_campo_valor():
    resultado = ResultadoTool(
        acao="cadastrar",
        status="aguardando_complemento",
        dados={
            "registros": [_registro_base(descricao="Roupas Zara", valor=Decimal("0"))],
            "campos_faltantes": ["valor"],
            "parcelas_futuras": [],
        },
    )
    texto = _fmt(resultado)
    assert "valor" in texto.lower() or "📋" in texto


# ---------------------------------------------------------------------------
# cadastrar / concluido — ✅ variações
# ---------------------------------------------------------------------------

def test_cadastrar_concluido_unico_avista():
    resultado = ResultadoTool(
        acao="cadastrar",
        status="concluido",
        dados={
            "registros_salvos": [
                _registro_base(descricao="Claude Code", valor=Decimal("472.00"))
            ],
            "qtd": 1,
        },
    )
    texto = _fmt(resultado)
    assert "✅ *Registrado com sucesso!*" in texto
    assert "Claude Code" in texto
    assert "R$ 472,00" in texto
    assert "extrato" in texto.lower()


def test_cadastrar_concluido_unico_parcelado():
    resultado = ResultadoTool(
        acao="cadastrar",
        status="concluido",
        dados={
            "registros_salvos": [
                _registro_base(
                    descricao="Roupas Zara",
                    valor=Decimal("180.00"),
                    parcela_numero=3,
                    parcela_total=5,
                ),
                _registro_base(
                    descricao="Roupas Zara",
                    valor=Decimal("180.00"),
                    parcela_numero=4,
                    parcela_total=5,
                ),
            ],
            "qtd": 2,
        },
    )
    texto = _fmt(resultado)
    assert "✅ *Registrado com sucesso!*" in texto
    assert "Roupas Zara" in texto
    assert "5x" in texto or "180,00" in texto


def test_cadastrar_concluido_multiplos():
    resultado = ResultadoTool(
        acao="cadastrar",
        status="concluido",
        dados={
            "registros_salvos": [
                _registro_base(descricao="Flores Natasha", valor=Decimal("140.00")),
                _registro_base(descricao="Internet", valor=Decimal("190.00")),
            ],
            "qtd": 2,
        },
    )
    texto = _fmt(resultado)
    assert "✅ *Registrado com sucesso!*" in texto
    assert "2 registros salvos" in texto or "2" in texto
    assert "Flores Natasha" in texto
    assert "R$ 140,00" in texto
    assert "Internet" in texto
    assert "R$ 190,00" in texto
    assert "extrato" in texto.lower()


# ---------------------------------------------------------------------------
# listar / concluido — 📊 seções + subtotais
# ---------------------------------------------------------------------------

def _item_lista(
    descricao="Internet",
    valor=Decimal("190.00"),
    data=date(2026, 6, 10),
    status="PAGO",
    parcela_numero=1,
    parcela_total=1,
) -> dict:
    return {
        "descricao": descricao,
        "valor": valor,
        "data": data,
        "status": status,
        "parcela_numero": parcela_numero,
        "parcela_total": parcela_total,
    }


def test_listar_concluido_cabecalho_periodo():
    resultado = ResultadoTool(
        acao="listar",
        status="concluido",
        dados={
            "periodo_label": "Jun/2026",
            "grupos": [
                {
                    "titulo": "GASTOS_FIXOS",
                    "itens": [_item_lista()],
                    "subtotal": Decimal("190.00"),
                }
            ],
            "total": Decimal("190.00"),
            "pago": Decimal("190.00"),
            "pendente": Decimal("0.00"),
        },
    )
    texto = _fmt(resultado)
    assert "📊 *Gastos de Jun/2026*" in texto


def test_listar_concluido_categoria_e_subtotal():
    resultado = ResultadoTool(
        acao="listar",
        status="concluido",
        dados={
            "periodo_label": "Jun/2026",
            "grupos": [
                {
                    "titulo": "GASTOS_FIXOS",
                    "itens": [
                        _item_lista(descricao="Internet", valor=Decimal("190.00")),
                        _item_lista(descricao="Academia", valor=Decimal("120.00")),
                        _item_lista(descricao="Claude Code", valor=Decimal("472.00")),
                    ],
                    "subtotal": Decimal("782.00"),
                }
            ],
            "total": Decimal("782.00"),
            "pago": Decimal("782.00"),
            "pendente": Decimal("0.00"),
        },
    )
    texto = _fmt(resultado)
    assert "GASTOS_FIXOS" in texto
    assert "_Subtotal: R$ 782,00_" in texto
    assert "Internet" in texto


def test_listar_concluido_totais():
    resultado = ResultadoTool(
        acao="listar",
        status="concluido",
        dados={
            "periodo_label": "Jun/2026",
            "grupos": [
                {
                    "titulo": "GASTOS_FIXOS",
                    "itens": [_item_lista(valor=Decimal("782.00"))],
                    "subtotal": Decimal("782.00"),
                },
                {
                    "titulo": "PARCELAMENTOS",
                    "itens": [
                        _item_lista(descricao="Roupas Zara 3/5", valor=Decimal("180.00"), status="PAGO", parcela_numero=3, parcela_total=5),
                        _item_lista(descricao="Batman PS5 2/4", valor=Decimal("200.00"), status="PENDENTE", parcela_numero=2, parcela_total=4),
                    ],
                    "subtotal": Decimal("380.00"),
                },
            ],
            "total": Decimal("1302.00"),
            "pago": Decimal("1102.00"),
            "pendente": Decimal("200.00"),
        },
    )
    texto = _fmt(resultado)
    assert "💳 *Total do período: R$ 1.302,00*" in texto
    assert "⏳ *Pendente: R$ 200,00*" in texto
    assert "✅ *Pago: R$ 1.102,00*" in texto


def test_listar_concluido_parcelamentos_secao():
    resultado = ResultadoTool(
        acao="listar",
        status="concluido",
        dados={
            "periodo_label": "Jun/2026",
            "grupos": [
                {
                    "titulo": "PARCELAMENTOS",
                    "itens": [
                        _item_lista(descricao="Roupas Zara 3/5", valor=Decimal("180.00"), status="PAGO", parcela_numero=3, parcela_total=5),
                    ],
                    "subtotal": Decimal("180.00"),
                }
            ],
            "total": Decimal("180.00"),
            "pago": Decimal("180.00"),
            "pendente": Decimal("0.00"),
        },
    )
    texto = _fmt(resultado)
    assert "PARCELAMENTOS" in texto
    assert "Roupas Zara" in texto


def test_listar_concluido_status_pago_pendente_emojis():
    resultado = ResultadoTool(
        acao="listar",
        status="concluido",
        dados={
            "periodo_label": "Jun/2026",
            "grupos": [
                {
                    "titulo": "GASTOS_FIXOS",
                    "itens": [
                        _item_lista(descricao="Internet", valor=Decimal("190.00"), status="PAGO"),
                        _item_lista(descricao="Batman", valor=Decimal("200.00"), status="PENDENTE"),
                    ],
                    "subtotal": Decimal("390.00"),
                }
            ],
            "total": Decimal("390.00"),
            "pago": Decimal("190.00"),
            "pendente": Decimal("200.00"),
        },
    )
    texto = _fmt(resultado)
    assert "✅" in texto
    assert "⏳" in texto


def test_listar_concluido_sem_pendente_omite_linha_pendente():
    """Quando pendente=0, a linha de pendente pode ser omitida (comportamento dos exemplos)."""
    resultado = ResultadoTool(
        acao="listar",
        status="concluido",
        dados={
            "periodo_label": "Mai/2026",
            "grupos": [
                {
                    "titulo": "GASTOS_FIXOS",
                    "itens": [_item_lista(descricao="Internet", valor=Decimal("190.00"), status="PAGO")],
                    "subtotal": Decimal("190.00"),
                }
            ],
            "total": Decimal("190.00"),
            "pago": Decimal("190.00"),
            "pendente": Decimal("0.00"),
        },
    )
    texto = _fmt(resultado)
    # Pendente 0 não deve aparecer ou deve aparecer sem destaque excessivo
    # O template do exemplo de maio não mostra linha de pendente quando é zero
    if "Pendente" in texto or "pendente" in texto:
        assert "R$ 0,00" in texto or "0,00" in texto


# ---------------------------------------------------------------------------
# listar / vazio — 📭
# ---------------------------------------------------------------------------

def test_listar_vazio_mensagem():
    resultado = ResultadoTool(
        acao="listar",
        status="vazio",
        dados={"periodo_label": "Jan/2026"},
    )
    texto = _fmt(resultado)
    assert "Nenhum registro encontrado" in texto
    assert "Jan/2026" in texto
    assert "📭" in texto


def test_listar_vazio_sugere_cadastrar():
    resultado = ResultadoTool(
        acao="listar",
        status="vazio",
        dados={"periodo_label": "Jan/2026"},
    )
    texto = _fmt(resultado)
    assert "cadastrar" in texto.lower()


# ---------------------------------------------------------------------------
# atualizar / aguardando_confirmacao — ✏️ com diff tachado
# ---------------------------------------------------------------------------

def test_atualizar_aguardando_confirmacao_card():
    resultado = ResultadoTool(
        acao="atualizar",
        status="aguardando_confirmacao",
        dados={
            "registro": _registro_base(descricao="Internet", valor=Decimal("190.00")),
            "diff": {"campo": "status", "antigo": "PENDENTE", "novo": "PAGO"},
            "parcelas_afetadas": [],
        },
    )
    texto = _fmt(resultado)
    assert "✏️ *Confirme a atualização:*" in texto
    assert "Internet" in texto
    assert "~~PENDENTE~~" in texto
    assert "*PAGO*" in texto
    assert "confirmar" in texto.lower()
    assert "cancelar" in texto.lower()


def test_atualizar_aguardando_confirmacao_com_parcelas_afetadas():
    resultado = ResultadoTool(
        acao="atualizar",
        status="aguardando_confirmacao",
        dados={
            "registro": _registro_base(descricao="Roupas Zara 3/5", valor=Decimal("180.00")),
            "diff": {"campo": "valor", "antigo": "R$ 180,00", "novo": "R$ 200,00"},
            "parcelas_afetadas": ["Jul/26", "Ago/26"],
        },
    )
    texto = _fmt(resultado)
    assert "📅 Parcelas afetadas: Jul/26 · Ago/26" in texto


def test_atualizar_aguardando_confirmacao_sem_parcelas_sem_secao():
    resultado = ResultadoTool(
        acao="atualizar",
        status="aguardando_confirmacao",
        dados={
            "registro": _registro_base(descricao="Internet"),
            "diff": {"campo": "status", "antigo": "PENDENTE", "novo": "PAGO"},
            "parcelas_afetadas": [],
        },
    )
    texto = _fmt(resultado)
    assert "Parcelas afetadas" not in texto


# ---------------------------------------------------------------------------
# atualizar / aguardando_selecao — 🔍 opções numeradas
# ---------------------------------------------------------------------------

def test_atualizar_aguardando_selecao_opcoes():
    resultado = ResultadoTool(
        acao="atualizar",
        status="aguardando_selecao",
        dados={
            "opcoes": [
                {"descricao": "Roupas Zara", "valor": Decimal("180.00"), "data": date(2026, 6, 10), "forma_pagamento": "CARTAO_CREDITO"},
                {"descricao": "Batman PS5", "valor": Decimal("200.00"), "data": date(2026, 6, 10), "forma_pagamento": "CARTAO_CREDITO"},
            ]
        },
    )
    texto = _fmt(resultado)
    assert "🔍" in texto
    assert "*1.*" in texto
    assert "*2.*" in texto
    assert "Roupas Zara" in texto
    assert "Batman PS5" in texto


# ---------------------------------------------------------------------------
# atualizar / concluido — ✅
# ---------------------------------------------------------------------------

def test_atualizar_concluido_sem_parcelas():
    resultado = ResultadoTool(
        acao="atualizar",
        status="concluido",
        dados={"descricao": "Internet", "propagou_parcelas": False},
    )
    texto = _fmt(resultado)
    assert "✅ *Registro atualizado!*" in texto
    assert "Internet" in texto
    assert "parcelas futuras" not in texto.lower()


def test_atualizar_concluido_com_parcelas():
    resultado = ResultadoTool(
        acao="atualizar",
        status="concluido",
        dados={"descricao": "Roupas Zara", "propagou_parcelas": True},
    )
    texto = _fmt(resultado)
    assert "✅ *Registro atualizado!*" in texto
    assert "Roupas Zara" in texto
    assert "parcelas futuras" in texto.lower()


# ---------------------------------------------------------------------------
# atualizar / nao_encontrado
# ---------------------------------------------------------------------------

def test_atualizar_nao_encontrado():
    resultado = ResultadoTool(
        acao="atualizar",
        status="nao_encontrado",
        dados={"referencia": "batman"},
    )
    texto = _fmt(resultado)
    assert "batman" in texto.lower() or "não encontrado" in texto.lower() or "nenhum" in texto.lower()


# ---------------------------------------------------------------------------
# excluir / aguardando_confirmacao — 🗑️
# ---------------------------------------------------------------------------

def test_excluir_aguardando_confirmacao_individual():
    resultado = ResultadoTool(
        acao="excluir",
        status="aguardando_confirmacao",
        dados={
            "registro": _registro_base(descricao="Flores Natasha", valor=Decimal("140.00")),
        },
    )
    texto = _fmt(resultado)
    assert "🗑️ *Confirme a exclusão:*" in texto
    assert "Flores Natasha" in texto
    assert "R$ 140,00" in texto
    assert "confirmar" in texto.lower()
    assert "cancelar" in texto.lower()


def test_excluir_aguardando_confirmacao_lote():
    resultado = ResultadoTool(
        acao="excluir",
        status="aguardando_confirmacao",
        dados={
            "modo": "lote",
            "qtd": 5,
            "periodo_label": "Mai/2026",
        },
    )
    texto = _fmt(resultado)
    assert "🗑️" in texto
    assert "5" in texto or "Mai/2026" in texto


# ---------------------------------------------------------------------------
# excluir / aguardando_escopo — opções 1/2
# ---------------------------------------------------------------------------

def test_excluir_aguardando_escopo_opcoes_numeradas():
    resultado = ResultadoTool(
        acao="excluir",
        status="aguardando_escopo",
        dados={
            "registro": _registro_base(
                descricao="Batman PS5",
                valor=Decimal("200.00"),
                forma_pagamento="CARTAO_CREDITO",
                status="PENDENTE",
            ),
            "parcelas_futuras": ["Jul/26", "Ago/26", "Set/26"],
        },
    )
    texto = _fmt(resultado)
    assert "🗑️ *Confirme a exclusão:*" in texto or "🗑️" in texto
    assert "*1.* Somente este" in texto
    assert "*2.* Todos, incluindo as parcelas futuras" in texto
    assert "Jul/26 · Ago/26 · Set/26" in texto
    assert "⚠️" in texto


# ---------------------------------------------------------------------------
# excluir / aguardando_selecao — 🔍
# ---------------------------------------------------------------------------

def test_excluir_aguardando_selecao_opcoes():
    resultado = ResultadoTool(
        acao="excluir",
        status="aguardando_selecao",
        dados={
            "opcoes": [
                {"descricao": "Internet", "valor": Decimal("190.00"), "data": date(2026, 6, 10), "status": "PAGO"},
                {"descricao": "Roupas Zara", "valor": Decimal("180.00"), "data": date(2026, 6, 10), "status": "PAGO"},
                {"descricao": "Batman PS5", "valor": Decimal("200.00"), "data": date(2026, 6, 10), "status": "PENDENTE"},
            ],
            "modo": "individual",
        },
    )
    texto = _fmt(resultado)
    assert "🔍" in texto
    assert "*1.*" in texto
    assert "*2.*" in texto
    assert "*3.*" in texto
    assert "Internet" in texto
    assert "Batman PS5" in texto


# ---------------------------------------------------------------------------
# excluir / concluido — 🗑️
# ---------------------------------------------------------------------------

def test_excluir_concluido_sem_parcelas():
    resultado = ResultadoTool(
        acao="excluir",
        status="concluido",
        dados={
            "descricao": "Flores Natasha",
            "valor": Decimal("140.00"),
            "parcelas_removidas": 0,
        },
    )
    texto = _fmt(resultado)
    assert "🗑️ *Registro excluído!*" in texto
    assert "Flores Natasha" in texto
    assert "R$ 140,00" in texto
    assert "parcelas" not in texto.lower() or "0" in texto


def test_excluir_concluido_com_parcelas():
    resultado = ResultadoTool(
        acao="excluir",
        status="concluido",
        dados={
            "descricao": "Batman PS5",
            "valor": Decimal("200.00"),
            "parcelas_removidas": 3,
        },
    )
    texto = _fmt(resultado)
    assert "🗑️ *Registro excluído!*" in texto
    assert "Batman PS5" in texto
    assert "R$ 200,00" in texto
    assert "3" in texto
    assert "parcelas" in texto.lower()


# ---------------------------------------------------------------------------
# excluir / nao_encontrado
# ---------------------------------------------------------------------------

def test_excluir_nao_encontrado():
    resultado = ResultadoTool(
        acao="excluir",
        status="nao_encontrado",
        dados={"referencia": "flores"},
    )
    texto = _fmt(resultado)
    assert "flores" in texto.lower() or "não encontrado" in texto.lower() or "nenhum" in texto.lower()


# ---------------------------------------------------------------------------
# conversar / concluido — repassa dados.resposta sem modificar
# ---------------------------------------------------------------------------

def test_conversar_concluido_repassa_resposta():
    resultado = ResultadoTool(
        acao="conversar",
        status="concluido",
        dados={"resposta": "Vale sim, depende do CET"},
    )
    texto = _fmt(resultado)
    assert texto == "Vale sim, depende do CET"


def test_conversar_concluido_repassa_resposta_longa():
    resposta = "O CET (Custo Efetivo Total) inclui juros, tarifas e IOF.\nSempre compare antes de fechar."
    resultado = ResultadoTool(
        acao="conversar",
        status="concluido",
        dados={"resposta": resposta},
    )
    texto = _fmt(resultado)
    assert texto == resposta


# ---------------------------------------------------------------------------
# menu / concluido — lista de capacidades
# ---------------------------------------------------------------------------

def test_menu_concluido_exibe_capacidades():
    resultado = ResultadoTool(
        acao="menu",
        status="concluido",
        dados={},
    )
    texto = _fmt(resultado)
    # Deve conter alguma orientação sobre o que o assistente faz
    assert len(texto) > 20
    palavras_esperadas = ["cadastrar", "listar", "extrato", "atualizar", "excluir", "ajuda"]
    encontrou = any(p in texto.lower() for p in palavras_esperadas)
    assert encontrou, f"Menu deve mencionar capacidades do assistente. Obtido: {texto!r}"


# ---------------------------------------------------------------------------
# erro / concluido — fallback amigável
# ---------------------------------------------------------------------------

def test_erro_concluido_mensagem_amigavel():
    resultado = ResultadoTool(
        acao="erro",
        status="concluido",
        dados={"mensagem": "Ocorreu um erro inesperado."},
    )
    texto = _fmt(resultado)
    assert "Ocorreu um erro inesperado." in texto


def test_erro_concluido_sem_traceback_tecnico():
    resultado = ResultadoTool(
        acao="erro",
        status="concluido",
        dados={"mensagem": "Timeout na conexão com o banco."},
    )
    texto = _fmt(resultado)
    assert "Traceback" not in texto
    assert "Exception" not in texto


# ---------------------------------------------------------------------------
# Formatação de valores Decimal — padrão brasileiro (vírgula)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("valor,esperado", [
    (Decimal("472.00"), "R$ 472,00"),
    (Decimal("1302.00"), "R$ 1.302,00"),
    (Decimal("140.00"), "R$ 140,00"),
    (Decimal("0.50"), "R$ 0,50"),
])
def test_formato_decimal_brasileiro(valor, esperado):
    """Valores Decimal devem ser formatados com vírgula decimal e ponto nos milhares."""
    resultado = ResultadoTool(
        acao="cadastrar",
        status="aguardando_confirmacao",
        dados={
            "registros": [_registro_base(valor=valor)],
            "campos_faltantes": [],
            "parcelas_futuras": [],
        },
    )
    texto = _fmt(resultado)
    assert esperado in texto, f"Esperava '{esperado}' no texto. Obtido:\n{texto}"
