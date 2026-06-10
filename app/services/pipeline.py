from app.services.confirmacao_state import EstadoConfirmacao


class Pipeline:
    def __init__(
        self,
        classificador,
        cadastrar,
        alterar,
        excluir,
        consultar,
        formatador,
        confirmacao_state,
        confirmacao_chain,
        extrator_parcelas,
        extrator_exclusao_lote,
        extrator_lista,
    ):
        self._classificador = classificador
        self._cadastrar = cadastrar
        self._alterar = alterar
        self._excluir = excluir
        self._consultar = consultar
        self._formatador = formatador
        self._state = confirmacao_state
        self._confirmacao_chain = confirmacao_chain
        self._extrator_parcelas = extrator_parcelas
        self._extrator_exclusao_lote = extrator_exclusao_lote
        self._extrator_lista = extrator_lista

    async def processar(self, numero: str, texto: str) -> str:
        estado = self._state.obter(numero)

        if estado is not None:
            return await self._rotear_estado(numero, texto, estado)

        intencao = await self._classificador.classificar(texto)
        return await self._rotear_intencao(numero, texto, intencao)

    async def _rotear_estado(self, numero: str, texto: str, estado: EstadoConfirmacao) -> str:
        if estado.acao == "AGUARDAR_PARCELAS":
            resultado_parcelas = await self._extrator_parcelas.extrair(texto)
            resultado = await self._cadastrar.executar_com_parcelas_confirmadas(
                estado.mensagem_original, resultado_parcelas.parcela_total, numero
            )
            return await self._formatador.formatar(resultado, "cadastro")

        if estado.acao == "EXCLUIR_LOTE":
            resposta = await self._confirmacao_chain.interpretar(texto, "sim_nao")
            resultado = await self._excluir.confirmar_lote(numero, resposta.tipo == "sim")
            return await self._formatador.formatar(resultado, "confirmacao")

        contexto = "escopo_parcela" if estado.pergunta_grupo else "sim_nao"
        resposta = await self._confirmacao_chain.interpretar(texto, contexto)

        if estado.acao == "ALTERAR":
            resultado = await self._alterar.confirmar(numero, resposta.tipo == "sim")
            return await self._formatador.formatar(resultado, "confirmacao")

        if estado.acao == "EXCLUIR":
            resultado = await self._excluir.confirmar(numero, resposta.tipo)
            return await self._formatador.formatar(resultado, "confirmacao")

        return await self._formatador.formatar("Estado desconhecido.", "erro")

    async def _rotear_intencao(self, numero: str, texto: str, intencao) -> str:
        if intencao.intencao == "CADASTRAR_LOTE":
            resultado = await self._cadastrar.executar_lote(texto, self._extrator_lista)
            return await self._formatador.formatar(resultado, "cadastro_lote")

        if intencao.intencao == "CADASTRAR":
            resultado = await self._cadastrar.executar(texto, numero)
            tipo = "aguarda_confirmacao" if resultado.aguarda_confirmacao else "cadastro"
            return await self._formatador.formatar(resultado, tipo)

        if intencao.intencao == "ALTERAR":
            resultado = await self._alterar.iniciar(texto, numero)
            return await self._formatador.formatar(resultado, "confirmacao")

        if intencao.intencao == "EXCLUIR":
            resultado = await self._excluir.iniciar(texto, numero)
            return await self._formatador.formatar(resultado, "confirmacao")

        if intencao.intencao == "EXCLUIR_LOTE":
            resultado = await self._excluir.iniciar_lote(texto, numero, self._extrator_exclusao_lote)
            return await self._formatador.formatar(resultado, "confirmacao")

        if intencao.intencao == "CONSULTAR":
            resultado = await self._consultar.executar(texto)
            return await self._formatador.formatar(resultado, "consulta")

        return await self._formatador.formatar(texto, "fora_escopo")
