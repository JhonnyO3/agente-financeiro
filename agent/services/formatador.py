from decimal import Decimal

from agent.domain.resultado import ResultadoTool


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


def _card_registro(reg: dict, numero: int | None = None) -> str:
    """Monta o bloco de um registro para confirmação de cadastro."""
    linhas = []

    prefixo = f"*{numero}. {reg['descricao']}*" if numero else f"*{reg['descricao']}*"
    linhas.append(prefixo)

    parcela_total = reg.get("parcela_total", 1)
    parcela_numero = reg.get("parcela_numero", 1)
    valor = reg.get("valor", Decimal("0"))
    if parcela_total and parcela_total > 1:
        linhas.append(
            f"💰 Valor: {parcela_total}x de {_brl(valor)} (total {_brl(valor * parcela_total)})"
        )
        linhas.append(
            f"📅 Data: {reg['data'].strftime('%d/%m/%Y')} (parcela {parcela_numero}/{parcela_total})"
        )
    else:
        linhas.append(f"💰 Valor: {_brl(valor)}")
        linhas.append(f"📅 Data: {reg['data'].strftime('%d/%m/%Y')}")

    linhas.append(f"🗂 Categoria: {reg['categoria']}")

    forma = reg.get("forma_pagamento", "")
    detalhes = reg.get("detalhes")
    if detalhes:
        linhas.append(f"💳 Pagamento: {forma} _(detalhes: {detalhes})_")
    else:
        linhas.append(f"💳 Pagamento: {forma}")

    linhas.append(f"👤 Responsável: {reg['responsavel']}")
    linhas.append(f"📌 Status: {reg['status']}")

    return "\n".join(linhas)


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
                return (
                    f"📭 Nenhum registro encontrado para *{periodo}*.\n\n"
                    "Digite *cadastrar* para adicionar um gasto."
                )

            # ------------------------------------------------------------------
            # atualizar
            # ------------------------------------------------------------------
            case ("atualizar", "aguardando_confirmacao"):
                return self._atualizar_confirmacao(dados)

            case ("atualizar", "aguardando_selecao"):
                return self._selecao_opcoes(dados["opcoes"], verbo="atualizar")

            case ("atualizar", "concluido"):
                desc = dados.get("descricao", "")
                propagou = dados.get("propagou_parcelas", False)
                linhas = [
                    "✅ *Registro atualizado!*",
                    "",
                    f"_{desc}_ foi atualizado com sucesso.",
                ]
                if propagou:
                    linhas.append(
                        "_As parcelas futuras vinculadas também foram atualizadas._"
                    )
                return "\n".join(linhas)

            case ("atualizar", "nao_encontrado"):
                ref = dados.get("referencia", "")
                return f"Nenhum registro encontrado para *{ref}*."

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
                ref = dados.get("referencia", "")
                return f"Nenhum registro encontrado para *{ref}*."

            # ------------------------------------------------------------------
            # conversar
            # ------------------------------------------------------------------
            case ("conversar", "concluido"):
                return dados.get("resposta", "")

            # ------------------------------------------------------------------
            # menu
            # ------------------------------------------------------------------
            case ("menu", "concluido"):
                return (
                    "Olá! Sou seu assistente financeiro pessoal. Posso ajudar com:\n\n"
                    "• *cadastrar* — registrar gastos e investimentos\n"
                    "• *extrato* / *listar* — ver o resumo do mês\n"
                    "• *atualizar* — corrigir um registro\n"
                    "• *excluir* — remover um registro\n"
                    "• *ajuda* — ver este menu\n\n"
                    "Digite o que quiser fazer! 😊"
                )

            # ------------------------------------------------------------------
            # erro
            # ------------------------------------------------------------------
            case ("erro", "concluido"):
                mensagem = dados.get("mensagem", "Ocorreu um erro inesperado.")
                return mensagem

            # ------------------------------------------------------------------
            # fallback
            # ------------------------------------------------------------------
            case _:
                return (
                    f"Não foi possível processar a ação *{acao}* (status: {status}).\n"
                    "Digite *ajuda* para ver o menu de opções."
                )

    # --------------------------------------------------------------------------
    # helpers privados
    # --------------------------------------------------------------------------

    def _cadastrar_confirmacao(self, dados: dict) -> str:
        registros = dados.get("registros", [])
        parcelas_futuras = dados.get("parcelas_futuras", [])
        campos_faltantes = dados.get("campos_faltantes", [])

        multiplo = len(registros) > 1
        cabecalho = (
            "📋 *Confirme os registros abaixo:*"
            if multiplo
            else "📋 *Confirme o registro abaixo:*"
        )
        linhas = [cabecalho, ""]

        for i, reg in enumerate(registros, start=1):
            numero = i if multiplo else None
            linhas.append(_card_registro(reg, numero=numero))

            if campos_faltantes:
                linhas.append(f"_(faltante: {', '.join(campos_faltantes)})_")

            if parcelas_futuras and not multiplo:
                linhas.append(f"📅 Parcelas: {' · '.join(parcelas_futuras)}")

            linhas.append("")

        linhas.append(
            "_Responda *confirmar* para salvar ou *cancelar* para descartar._"
        )
        return "\n".join(linhas)

    def _cadastrar_concluido(self, dados: dict) -> str:
        registros = dados.get("registros_salvos", [])
        qtd = dados.get("qtd", len(registros))
        linhas = ["✅ *Registrado com sucesso!*", ""]

        if qtd == 1 and registros:
            reg = registros[0]
            desc = reg.get("descricao", "")
            valor = reg.get("valor", Decimal("0"))
            parcela_total = reg.get("parcela_total", 1)
            if parcela_total and parcela_total > 1:
                linhas.append(
                    f"_{desc}_ {parcela_total}x de *{_brl(valor)}* foi salvo."
                )
            else:
                linhas.append(f"_{desc}_ de *{_brl(valor)}* foi salvo.")
        else:
            linhas.append(f"*{qtd} registros salvos:*")
            # Deduplica por descricao para parcelados
            seen: set[str] = set()
            for reg in registros:
                desc = reg.get("descricao", "")
                if desc in seen:
                    continue
                seen.add(desc)
                valor = reg.get("valor", Decimal("0"))
                parcela_total = reg.get("parcela_total", 1)
                if parcela_total and parcela_total > 1:
                    linhas.append(f"  • {desc} — {parcela_total}x de {_brl(valor)}")
                else:
                    linhas.append(f"  • {desc} — {_brl(valor)}")

        linhas.append("")
        linhas.append("Digite *extrato* para ver o resumo do mês. 📊")
        return "\n".join(linhas)

    def _listar_concluido(self, dados: dict) -> str:
        periodo = dados.get("periodo_label", "")
        grupos = dados.get("grupos", [])
        total = dados.get("total", Decimal("0"))
        pago = dados.get("pago", Decimal("0"))
        pendente = dados.get("pendente", Decimal("0"))

        linhas = [f"📊 *Gastos de {periodo}*", ""]

        for grupo in grupos:
            titulo = grupo.get("titulo", "")
            itens = grupo.get("itens", [])
            subtotal = grupo.get("subtotal", Decimal("0"))

            linhas.append(f"*{titulo}*")
            for item in itens:
                desc = item.get("descricao", "")
                valor = item.get("valor", Decimal("0"))
                data = item.get("data")
                data_str = data.strftime("%d/%m") if data else ""
                st = item.get("status", "")
                emoji = _status_emoji(st)
                linhas.append(f"  • {desc} — {_brl(valor)} — {data_str} — {emoji} {st}")
            linhas.append(f"_Subtotal: {_brl(subtotal)}_")
            linhas.append("")

        linhas.append(f"💳 *Total do período: {_brl(total)}*")
        if pendente and Decimal(str(pendente)) > 0:
            linhas.append(f"⏳ *Pendente: {_brl(pendente)}*")
        linhas.append(f"✅ *Pago: {_brl(pago)}*")

        return "\n".join(linhas)

    def _atualizar_confirmacao(self, dados: dict) -> str:
        reg = dados.get("registro", {})
        diff = dados.get("diff", {})
        parcelas_afetadas = dados.get("parcelas_afetadas", [])

        campo = diff.get("campo", "")
        antigo = diff.get("antigo", "")
        novo = diff.get("novo", "")

        linhas = ["✏️ *Confirme a atualização:*", "", f"*{reg.get('descricao', '')}*"]

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

        for v in campos.values():
            linhas.append(v)

        if parcelas_afetadas:
            linhas.append(f"📅 Parcelas afetadas: {' · '.join(parcelas_afetadas)}")

        linhas.append("")
        linhas.append(
            "_Responda *confirmar* para salvar ou *cancelar* para descartar._"
        )
        return "\n".join(linhas)

    def _selecao_opcoes(self, opcoes: list, verbo: str) -> str:
        linhas = [f"🔍 Encontrei mais de um registro. Qual você quer {verbo}?", ""]
        for i, op in enumerate(opcoes, start=1):
            desc = op.get("descricao", "")
            valor = op.get("valor", Decimal("0"))
            data = op.get("data")
            data_str = data.strftime("%d/%m") if data else ""
            # campo extra: forma_pagamento (atualizar) ou status (excluir)
            extra = op.get("forma_pagamento") or op.get("status") or ""
            status_raw = op.get("status", "")
            emoji = _status_emoji(status_raw) if status_raw else ""
            if emoji:
                linhas.append(
                    f"*{i}.* {desc} — {_brl(valor)} — {data_str} — {emoji} {status_raw}"
                )
            else:
                linhas.append(f"*{i}.* {desc} — {_brl(valor)} — {data_str} — {extra}")
        linhas.append("")
        linhas.append("_Responda com o número do registro._")
        return "\n".join(linhas)

    def _excluir_confirmacao(self, dados: dict) -> str:
        # Modo lote
        if dados.get("modo") == "lote":
            qtd = dados.get("qtd", 0)
            periodo = dados.get("periodo_label", "")
            return (
                f"🗑️ *Confirme a exclusão:*\n\n"
                f"Você está prestes a excluir *{qtd}* registros de *{periodo}*.\n\n"
                "_Responda *confirmar* para excluir ou *cancelar* para descartar._"
            )

        # Individual
        reg = dados.get("registro", {})
        linhas = ["🗑️ *Confirme a exclusão:*", "", _card_registro(reg)]
        linhas.append("")
        linhas.append(
            "_Responda *confirmar* para excluir ou *cancelar* para descartar._"
        )
        return "\n".join(linhas)

    def _excluir_escopo(self, dados: dict) -> str:
        reg = dados.get("registro", {})
        parcelas_futuras = dados.get("parcelas_futuras", [])

        linhas = ["🗑️ *Confirme a exclusão:*", "", _card_registro(reg), ""]
        linhas.append(
            f"⚠️ Este registro possui parcelas futuras: {' · '.join(parcelas_futuras)}"
        )
        linhas.append("*1.* Somente este")
        linhas.append("*2.* Todos, incluindo as parcelas futuras")
        linhas.append("_Responda com o número — ou *cancelar*._")
        return "\n".join(linhas)

    def _excluir_concluido(self, dados: dict) -> str:
        desc = dados.get("descricao", "")
        valor = dados.get("valor", Decimal("0"))
        parcelas_removidas = dados.get("parcelas_removidas", 0)

        linhas = [
            "🗑️ *Registro excluído!*",
            "",
            f"_{desc}_ de *{_brl(valor)}* foi removido.",
        ]
        if parcelas_removidas and int(parcelas_removidas) > 0:
            linhas.append(
                f"_{parcelas_removidas} parcelas futuras vinculadas também foram removidas._"
            )
        return "\n".join(linhas)
