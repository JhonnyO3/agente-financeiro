from decimal import Decimal

from agent.domain.resultado import ResultadoTool
from agent.services.template_loader import renderizar


def _brl(valor) -> str:
    """Decimal → 'R$ 1.302,00' (padrão brasileiro)."""
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor))
    # Formata com 2 casas e converte separadores
    formatted = f"{valor:,.2f}"  # e.g. "1,302.00"
    # Troca: ponto de milhar → X temporário, vírgula → ponto, X → vírgula
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _status_emoji(status: str) -> str:
    return "✅" if status == "PAGO" else "⏳"


class Formatador:
    def formatar(self, resultado: ResultadoTool) -> str:
        acao = resultado.acao
        status = resultado.status
        dados = resultado.dados

        match (acao, status):
            # ------------------------------------------------------------------
            # cadastrar
            # ------------------------------------------------------------------
            case ("cadastrar", "aguardando_confirmacao") | (
                "cadastrar",
                "aguardando_complemento",
            ):
                return self._cadastrar_confirmacao(dados)

            case ("cadastrar", "concluido"):
                return self._cadastrar_concluido(dados)

            # ------------------------------------------------------------------
            # listar
            # ------------------------------------------------------------------
            case ("listar", "concluido"):
                return self._listar_concluido(dados)

            case ("listar", "vazio"):
                periodo = dados.get("periodo_label", "")
                return renderizar("listar_vazio.md", {"periodo": periodo})

            # ------------------------------------------------------------------
            # atualizar
            # ------------------------------------------------------------------
            case ("atualizar", "aguardando_confirmacao"):
                return self._atualizar_confirmacao(dados)

            case ("atualizar", "aguardando_selecao"):
                return self._selecao_opcoes(dados["opcoes"], verbo="atualizar")

            case ("atualizar", "concluido"):
                return renderizar(
                    "atualizar_concluido.md",
                    {
                        "descricao": dados.get("descricao", ""),
                        "propagou": dados.get("propagou_parcelas", False),
                    },
                )

            case ("atualizar", "nao_encontrado"):
                return renderizar(
                    "atualizar_nao_encontrado.md",
                    {"referencia": dados.get("referencia", "")},
                )

            # ------------------------------------------------------------------
            # excluir
            # ------------------------------------------------------------------
            case ("excluir", "aguardando_confirmacao"):
                return self._excluir_confirmacao(dados)

            case ("excluir", "aguardando_escopo"):
                return self._excluir_escopo(dados)

            case ("excluir", "aguardando_selecao"):
                return self._selecao_opcoes(dados["opcoes"], verbo="excluir")

            case ("excluir", "concluido"):
                return self._excluir_concluido(dados)

            case ("excluir", "nao_encontrado"):
                return renderizar(
                    "excluir_nao_encontrado.md",
                    {"referencia": dados.get("referencia", "")},
                )

            # ------------------------------------------------------------------
            # cancelar
            # ------------------------------------------------------------------
            case ("cancelar", "concluido"):
                return "Ok, operação cancelada."

            # ------------------------------------------------------------------
            # conversar — passthrough sem template
            # ------------------------------------------------------------------
            case ("conversar", "concluido"):
                return dados.get("resposta", "")

            # ------------------------------------------------------------------
            # menu
            # ------------------------------------------------------------------
            case ("menu", "concluido"):
                return renderizar("menu.md", {})

            # ------------------------------------------------------------------
            # erro
            # ------------------------------------------------------------------
            case ("erro", "concluido"):
                mensagem = dados.get("mensagem", "Ocorreu um erro inesperado.")
                return renderizar("erro.md", {"mensagem": mensagem})

            # ------------------------------------------------------------------
            # fallback
            # ------------------------------------------------------------------
            case _:
                return renderizar(
                    "erro.md",
                    {
                        "mensagem": (
                            f"Não foi possível processar a ação *{acao}* (status: {status}).\n"
                            "Digite *ajuda* para ver o menu de opções."
                        )
                    },
                )

    # --------------------------------------------------------------------------
    # helpers privados — constroem contexto e delegam ao template
    # --------------------------------------------------------------------------

    def _cadastrar_confirmacao(self, dados: dict) -> str:
        registros = dados.get("registros", [])
        parcelas_futuras = dados.get("parcelas_futuras", [])
        campos_faltantes = dados.get("campos_faltantes", [])
        multiplo = len(registros) > 1

        regs_ctx = []
        for reg in registros:
            valor = reg.get("valor", Decimal("0"))
            parcela_total = reg.get("parcela_total", 1)
            parcela_numero = reg.get("parcela_numero", 1)
            data = reg.get("data")
            regs_ctx.append(
                {
                    "descricao": reg.get("descricao", ""),
                    "valor_fmt": _brl(valor),
                    "total_fmt": _brl(valor * parcela_total)
                    if parcela_total and parcela_total > 1
                    else _brl(valor),
                    "data_fmt": (
                        data.strftime("%d/%m/%Y")
                        if hasattr(data, "strftime")
                        else (
                            __import__("datetime").date.fromisoformat(data).strftime("%d/%m/%Y")
                            if data
                            else ""
                        )
                    ),
                    "categoria": reg.get("categoria", ""),
                    "forma_pagamento": reg.get("forma_pagamento", ""),
                    "detalhes": reg.get("detalhes"),
                    "responsavel": reg.get("responsavel", ""),
                    "status": reg.get("status", ""),
                    "parcela_numero": parcela_numero,
                    "parcela_total": parcela_total,
                }
            )

        return renderizar(
            "cadastrar_confirmacao.md",
            {
                "multiplo": multiplo,
                "registros": regs_ctx,
                "campos_faltantes": campos_faltantes,
                "parcelas_futuras": parcelas_futuras,
            },
        )

    def _cadastrar_concluido(self, dados: dict) -> str:
        registros = dados.get("registros_salvos", [])
        qtd = dados.get("qtd", len(registros))

        # Deduplica por descricao (para parcelados) — lógica de negócio permanece em Python
        seen: set[str] = set()
        regs_ctx = []
        for reg in registros:
            desc = reg.get("descricao", "")
            if desc in seen:
                continue
            seen.add(desc)
            valor = reg.get("valor", Decimal("0"))
            parcela_total = reg.get("parcela_total", 1)
            regs_ctx.append(
                {
                    "descricao": desc,
                    "valor_fmt": _brl(valor),
                    "parcela_total": parcela_total,
                }
            )

        return renderizar(
            "cadastrar_concluido.md",
            {"qtd": qtd, "registros": regs_ctx},
        )

    def _listar_concluido(self, dados: dict) -> str:
        periodo = dados.get("periodo_label", "")
        grupos = dados.get("grupos", [])
        total = dados.get("total", Decimal("0"))
        pago = dados.get("pago", Decimal("0"))
        pendente = dados.get("pendente", Decimal("0"))

        grupos_ctx = []
        for grupo in grupos:
            itens_ctx = []
            for item in grupo.get("itens", []):
                data = item.get("data")
                st = item.get("status", "")
                itens_ctx.append(
                    {
                        "descricao": item.get("descricao", ""),
                        "valor_fmt": _brl(item.get("valor", Decimal("0"))),
                        "data_fmt": data.strftime("%d/%m") if data else "",
                        "emoji": _status_emoji(st),
                        "status": st,
                    }
                )
            grupos_ctx.append(
                {
                    "titulo": grupo.get("titulo", ""),
                    "itens": itens_ctx,
                    "subtotal_fmt": _brl(grupo.get("subtotal", Decimal("0"))),
                }
            )

        pendente_dec = Decimal(str(pendente))
        return renderizar(
            "listar_concluido.md",
            {
                "periodo": periodo,
                "grupos": grupos_ctx,
                "total_fmt": _brl(total),
                "pago_fmt": _brl(pago),
                "pendente_fmt": _brl(pendente),
                "pendente_positivo": pendente_dec > 0,
            },
        )

    def _atualizar_confirmacao(self, dados: dict) -> str:
        reg = dados.get("registro", {})
        diff = dados.get("diff", {})
        parcelas_afetadas = dados.get("parcelas_afetadas", [])

        campo = diff.get("campo", "")
        antigo = diff.get("antigo", "")
        novo = diff.get("novo", "")

        valor = reg.get("valor", Decimal("0"))
        data = reg.get("data")
        data_str = data.strftime("%d/%m/%Y") if data else ""
        categoria = reg.get("categoria", "")
        forma = reg.get("forma_pagamento", "")
        responsavel = reg.get("responsavel", "")
        status = reg.get("status", "")

        campos = {
            "valor": f"💰 Valor: {_brl(valor)}",
            "data": f"📅 Data: {data_str}",
            "categoria": f"🗂 Categoria: {categoria}",
            "forma_pagamento": f"💳 Pagamento: {forma}",
            "responsavel": f"👤 Responsável: {responsavel}",
            "status": f"📌 Status: {status}",
        }

        # Aplica diff inline no campo alterado
        if campo == "valor":
            campos["valor"] = f"💰 Valor: ~~{antigo}~~ → *{novo}*"
        elif campo == "data":
            campos["data"] = f"📅 Data: ~~{antigo}~~ → *{novo}*"
        elif campo == "categoria":
            campos["categoria"] = f"🗂 Categoria: ~~{antigo}~~ → *{novo}*"
        elif campo == "forma_pagamento":
            campos["forma_pagamento"] = f"💳 Pagamento: ~~{antigo}~~ → *{novo}*"
        elif campo == "responsavel":
            campos["responsavel"] = f"👤 Responsável: ~~{antigo}~~ → *{novo}*"
        elif campo == "status":
            campos["status"] = f"📌 Status: ~~{antigo}~~ → *{novo}*"

        return renderizar(
            "atualizar_confirmacao.md",
            {
                "registro": {"descricao": reg.get("descricao", "")},
                "campo_valor_fmt": campos["valor"],
                "campo_data_fmt": campos["data"],
                "campo_categoria_fmt": campos["categoria"],
                "campo_forma_fmt": campos["forma_pagamento"],
                "campo_responsavel_fmt": campos["responsavel"],
                "campo_status_fmt": campos["status"],
                "parcelas_afetadas": parcelas_afetadas,
            },
        )

    def _selecao_opcoes(self, opcoes: list, verbo: str) -> str:
        opcoes_ctx = []
        for op in opcoes:
            data = op.get("data")
            data_str = data.strftime("%d/%m") if data else ""
            status_raw = op.get("status", "")
            emoji = _status_emoji(status_raw) if status_raw else ""
            extra = op.get("forma_pagamento") or op.get("status") or ""
            opcoes_ctx.append(
                {
                    "descricao": op.get("descricao", ""),
                    "valor_fmt": _brl(op.get("valor", Decimal("0"))),
                    "data_fmt": data_str,
                    "emoji": emoji,
                    "status": status_raw,
                    "extra": extra,
                }
            )
        return renderizar("selecao_opcoes.md", {"verbo": verbo, "opcoes": opcoes_ctx})

    def _excluir_confirmacao(self, dados: dict) -> str:
        modo = dados.get("modo")
        if modo == "lote":
            return renderizar(
                "excluir_confirmacao.md",
                {
                    "modo": "lote",
                    "qtd": dados.get("qtd", 0),
                    "periodo": dados.get("periodo_label", ""),
                    "registro": {},
                },
            )

        reg = dados.get("registro", {})
        data = reg.get("data")
        valor = reg.get("valor", Decimal("0"))
        reg_ctx = {
            "descricao": reg.get("descricao", ""),
            "valor_fmt": _brl(valor),
            "data_fmt": data.strftime("%d/%m/%Y") if data else "",
            "categoria": reg.get("categoria", ""),
            "forma_pagamento": reg.get("forma_pagamento", ""),
            "detalhes": reg.get("detalhes"),
            "responsavel": reg.get("responsavel", ""),
            "status": reg.get("status", ""),
        }
        return renderizar(
            "excluir_confirmacao.md",
            {"modo": None, "qtd": 0, "periodo": "", "registro": reg_ctx},
        )

    def _excluir_escopo(self, dados: dict) -> str:
        reg = dados.get("registro", {})
        parcelas_futuras = dados.get("parcelas_futuras", [])
        data = reg.get("data")
        valor = reg.get("valor", Decimal("0"))
        reg_ctx = {
            "descricao": reg.get("descricao", ""),
            "valor_fmt": _brl(valor),
            "data_fmt": data.strftime("%d/%m/%Y") if data else "",
            "categoria": reg.get("categoria", ""),
            "forma_pagamento": reg.get("forma_pagamento", ""),
            "detalhes": reg.get("detalhes"),
            "responsavel": reg.get("responsavel", ""),
            "status": reg.get("status", ""),
        }
        return renderizar(
            "excluir_escopo.md",
            {"registro": reg_ctx, "parcelas_futuras": parcelas_futuras},
        )

    def _excluir_concluido(self, dados: dict) -> str:
        valor = dados.get("valor", Decimal("0"))
        parcelas_removidas = dados.get("parcelas_removidas", 0)
        return renderizar(
            "excluir_concluido.md",
            {
                "descricao": dados.get("descricao", ""),
                "valor_fmt": _brl(valor),
                "parcelas_removidas": parcelas_removidas,
            },
        )
