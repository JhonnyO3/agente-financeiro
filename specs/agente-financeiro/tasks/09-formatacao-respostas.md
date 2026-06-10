# Tarefa 09 — Formatação de Respostas + Pipeline Central

**Stack:** python  
**Depende de:** 06-service-cadastrar, 07-service-alterar-excluir, 08-service-consultar  
**Arquivos próprios:** `app/services/pipeline.py`, `app/services/formatador.py`

## Objetivo

Montar o pipeline central que recebe texto processado pelo debounce, classifica a intenção, despacha para o service correto e formata a resposta via LLM.

## Entregáveis

### `app/services/formatador.py`

Usa LLM com temperatura 0.3 para formatar o resultado de cada service em texto amigável para WhatsApp, carregando o prompt correto:

| Resultado                    | Prompt usado                     |
|------------------------------|----------------------------------|
| `ResultadoCadastro` (salvo)  | `prompts/cadastro-confirmado.md` |
| `ResultadoCadastro` (cartão) | texto fixo (pergunta de parcelas)|
| `ResultadoConsulta`          | `prompts/resumo.md`              |
| confirmação alt/excl         | `prompts/confirmacao.md`         |
| fora de escopo               | `prompts/fora-de-escopo.md`      |

> `prompts/sistema.md` é identidade global — **nunca** usado como template de resposta.

### Injeção de dependências (fix #13)

Todos os services e o pipeline recebem suas dependências via construtor. O `main.py` instancia tudo no lifespan e os passa para os routers via `app.state`:

```python
# app/entrypoint/main.py — lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    db = await criar_engine()
    repo = TransacaoRepository(db)
    embedder = Embedder()
    state = ConfirmacaoState()

    cadastrar  = CadastrarService(repo, embedder, extrator, categorizador, state)
    alterar    = AlterarService(repo, embedder, extrator_alteracao, state)
    excluir    = ExcluirService(repo, embedder, state)
    consultar  = ConsultarService(repo, filtro_chain)
    formatador = Formatador()
    pipeline   = Pipeline(classificador, cadastrar, alterar, excluir, consultar, formatador, state)

    app.state.pipeline = pipeline
    yield
    await db.dispose()
```

O webhook acessa `request.app.state.pipeline` — sem `Depends()` global.

### `app/services/pipeline.py` — máquina de estados completa

```python
class Pipeline:
    async def processar(self, numero: str, texto: str) -> str:
        estado = self._state.obter(numero)

        if estado is not None:
            return await self._rotear_estado(numero, texto, estado)

        intencao = await self._classificador.classificar(texto)
        return await self._rotear_intencao(numero, texto, intencao)

    async def _rotear_estado(self, numero: str, texto: str, estado: EstadoConfirmacao) -> str:
        if estado.acao == "AGUARDAR_PARCELAS":
            # LLM extrai o número de parcelas da resposta do usuário
            parcelas = await self._extrator_parcelas.extrair(texto)  # retorna int
            return await self._cadastrar.executar_com_parcelas_confirmadas(
                estado.mensagem_original, parcelas, numero
            )

        resposta = await self._interpretador_confirmacao.interpretar(texto, estado)
        # resposta.tipo: "sim" | "nao" | "parcela" | "grupo"

        if estado.acao == "ALTERAR":
            return await self._alterar.confirmar(numero, resposta.tipo == "sim")

        if estado.acao == "EXCLUIR":
            return await self._excluir.confirmar(numero, resposta)
```

### Chain `InterpretadorConfirmacao` (fix #5)

Usa LLM (`gpt-4o-mini`, temperatura 0) para interpretar respostas ambíguas de confirmação:

```python
class ConfirmacaoResposta(BaseModel):
    tipo: Literal["sim", "nao", "parcela", "grupo"]

# Exemplos que o LLM normaliza:
# "pode ser" / "vai" / "bora" / "confirmo" → "sim"
# "não quero" / "esquece" / "cancela" → "nao"
# "só essa" / "apenas esta" / "essa aqui" → "parcela"
# "todas" / "o grupo todo" / "apaga tudo" → "grupo"
```

Ver `contracts/agent-llm.md` para o contrato completo deste chain.

### Chain `ExtratorParcelas`

Usa LLM (`gpt-4o-mini`, temperatura 0) para extrair um inteiro da resposta do usuário:

```python
class ExtratorParcelasResult(BaseModel):
    parcela_total: int   # 1 = à vista; N >= 2 = parcelado
    # "3 vezes" → 3 | "à vista" → 1 | "6x" → 6
```

## Critério de aceite

- [ ] Mensagem de gasto → pipeline retorna string formatada com `cadastro-confirmado.md`
- [ ] Mensagem de consulta → retorna resumo com valores corretos
- [ ] Estado `AGUARDAR_PARCELAS`: "3 vezes" → `executar_com_parcelas_confirmadas(3)` chamado
- [ ] Estado `EXCLUIR` + `pergunta_grupo=True`: "só essa" / "todas" roteiam corretamente
- [ ] Estado `ALTERAR`: "pode ser" interpretado como "sim" pelo LLM
- [ ] Fora de escopo → retorna resposta amigável + menu
- [ ] Pipeline instanciado uma vez no lifespan, não por request
