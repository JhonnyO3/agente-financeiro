from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.base import criar_llm_formatacao, carregar_prompt
from app.services.cadastrar import ResultadoCadastro
from app.services.consultar import ResultadoConsulta


class Formatador:
    def __init__(self):
        self._llm = criar_llm_formatacao()

    async def formatar(self, resultado, tipo_resultado: str) -> str:
        if tipo_resultado == "aguarda_confirmacao":
            return resultado.pergunta

        if tipo_resultado == "erro":
            return "Ocorreu um erro ao processar sua mensagem. Por favor, tente novamente."

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
        linhas = [
            f"mensagem_resposta: {resultado.mensagem_resposta}",
            f"aguarda_confirmacao: {resultado.aguarda_confirmacao}",
            f"transacoes: {len(resultado.transacoes)} registrada(s)",
        ]
        return "\n".join(linhas)

    if isinstance(resultado, ResultadoConsulta):
        linhas = [
            f"tipo: {resultado.tipo}",
            f"periodo: {resultado.periodo_label}",
            f"total_gastos: {resultado.total_gastos}",
            f"total_investimentos: {resultado.total_investimentos}",
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
