from langchain_core.messages import SystemMessage, HumanMessage

from agent.agents.base import criar_llm_formatacao, carregar_prompt
from agent.services.cadastrar import ResultadoCadastro, ResultadoCadastroLote
from agent.services.consultar import ResultadoConsulta


class Formatador:
    def __init__(self):
        self._llm = criar_llm_formatacao()

    async def formatar(self, resultado, tipo_resultado: str) -> str:
        if tipo_resultado == "aguarda_confirmacao":
            return resultado.pergunta

        if tipo_resultado == "erro":
            return "Ocorreu um erro ao processar sua mensagem. Por favor, tente novamente."

        if tipo_resultado == "cadastro_lote":
            return _serializar(resultado)

        prompt_map = {
            "cadastro": "cadastro-confirmado.md",
            "consulta": "resumo.md",
            "confirmacao": "confirmacao.md",
            "fora_escopo": "fora-de-escopo.md",
        }

        nome_prompt = prompt_map.get(tipo_resultado)
        if nome_prompt is None:
            return "Não foi possível formatar a resposta."

        system_prompt = carregar_prompt(nome_prompt)
        conteudo = _serializar(resultado)

        try:
            resposta = await self._llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=conteudo),
            ])
            return resposta.content
        except Exception:
            return "Não foi possível formatar a resposta no momento."


def _serializar(resultado) -> str:
    if isinstance(resultado, ResultadoCadastro):
        if not resultado.transacoes:
            return resultado.mensagem_resposta
        t = resultado.transacoes[0]
        parcela_total = t.parcela_total
        linhas = [
            f"descricao: {t.descricao or ''}",
            f"categoria: {t.categoria if isinstance(t.categoria, str) else t.categoria.value}",
            f"parcela_total: {parcela_total}",
        ]
        if parcela_total == 1:
            linhas += [
                f"data: {t.data.strftime('%d/%m/%Y')}",
                f"valor: R$ {t.valor:.2f}",
            ]
        else:
            valor_total = sum(x.valor for x in resultado.transacoes)
            meses = " · ".join(x.data.strftime("%b/%y") for x in resultado.transacoes)
            linhas += [
                f"valor_por_parcela: R$ {t.valor:.2f}",
                f"valor_total: R$ {valor_total:.2f}",
                f"lista_meses: {meses}",
            ]
        return "\n".join(linhas)

    if isinstance(resultado, ResultadoCadastroLote):
        linhas = [f"✅ {len(resultado.transacoes)} registro(s) cadastrado(s) com sucesso!\n"]
        for t in resultado.transacoes:
            cat = t.categoria if isinstance(t.categoria, str) else t.categoria.value
            parc = f" ({t.parcela_numero}/{t.parcela_total})" if t.parcela_total > 1 else ""
            linhas.append(f"• {t.descricao or cat} — R$ {t.valor:.2f}{parc} [{cat}]")
        return "\n".join(linhas)

    if isinstance(resultado, ResultadoConsulta):
        linhas = [
            f"tipo: {resultado.tipo}",
            f"periodo: {resultado.periodo_label}",
            f"total_gastos: {resultado.total_gastos}",
            f"total_investimentos: {resultado.total_investimentos}",
            f"total_receitas: {resultado.total_receitas}",
            f"balanco: {resultado.balanco}",
        ]
        for cat in resultado.por_categoria:
            linhas.append(f"  {cat.categoria}: {cat.total}")
        if resultado.parcelas:
            for p in resultado.parcelas:
                linhas.append(f"  parcela {p.parcela_numero}/{p.parcela_total} — R${p.valor} — {p.data} — {p.status}")
        return "\n".join(linhas)

    if isinstance(resultado, str):
        return resultado

    return str(resultado)
