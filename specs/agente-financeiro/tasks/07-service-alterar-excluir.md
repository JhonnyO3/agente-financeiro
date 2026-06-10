# Tarefa 07 — Service: Alterar e Excluir

**Stack:** python  
**Depende de:** 03-repository-transacoes, 05-agent-classificador  
**Arquivos próprios:** `app/services/alterar.py`, `app/services/excluir.py`, `app/services/confirmacao_state.py`

## Objetivo

Implementar busca semântica + fluxo de confirmação para alteração e exclusão.

## Entregáveis

### `app/services/confirmacao_state.py`

Cache em memória (dict) por número de telefone. Cobre **todos** os estados de espera do pipeline:

```python
@dataclass
class EstadoConfirmacao:
    acao: Literal["ALTERAR", "EXCLUIR", "AGUARDAR_PARCELAS"]
    # ALTERAR / EXCLUIR: aguarda "sim/não" (ou escopo no parcelado)
    # AGUARDAR_PARCELAS: aguarda número de parcelas após mencionar cartão

    transacao_id: int | None         # None quando acao=AGUARDAR_PARCELAS
    grupo_parcela_id: UUID | None    # preenchido se for parcelado
    novos_dados: TransacaoUpdate | None  # apenas para ALTERAR
    pergunta_grupo: bool = False     # True = aguarda "só essa" / "todas" (antes do sim/não)
    mensagem_original: str = ""      # texto original do usuário — reutilizado ao confirmar parcelas

class ConfirmacaoState:
    _estados: dict[str, EstadoConfirmacao] = {}

    def salvar(self, numero: str, estado: EstadoConfirmacao) -> None: ...
    def obter(self, numero: str) -> EstadoConfirmacao | None: ...
    def limpar(self, numero: str) -> None: ...
    # TTL de 5 minutos: limpar estado se obter() for chamado após expiração
```

### `app/services/alterar.py`

> Ver **`contracts/embedding.md`** — o embedding de busca é gerado a partir da mensagem bruta do usuário. 1 chamada OpenAI por operação de busca.

> Ver **`contracts/agent-llm.md`** — `ExtracaoAlteracaoResult` é o chain que extrai os `novos_dados` da mensagem.

```python
class AlterarService:
    async def iniciar(self, mensagem: str, numero: str) -> str:
        # 1. extrator_alteracao.extrair(mensagem) → ExtracaoAlteracaoResult (novos_dados)
        # 2. embedder.gerar(mensagem) → vetor de busca
        # 3. repository.buscar_semantico(embedding, limite=1)
        # 4. Se distância L2 > 1.0 → retorna "Não encontrei nenhum registro parecido."
        # 5. Salva EstadoConfirmacao(acao="ALTERAR", transacao_id=..., novos_dados=...)
        # 6. Retorna card de confirmação (ver prompts/confirmacao.md)

    async def confirmar(self, numero: str, confirmado: bool) -> str:
        # 1. Busca EstadoConfirmacao do cache
        # 2. Se confirmado → repository.atualizar(id, novos_dados)
        # 3. Limpa estado
        # 4. Retorna mensagem de sucesso ou cancelamento
```

### `app/services/excluir.py`

```python
class ExcluirService:
    async def iniciar(self, mensagem: str, numero: str) -> str:
        # 1. embedder.gerar(mensagem) → vetor de busca
        # 2. repository.buscar_semantico(embedding, limite=1)
        # 3. Se distância L2 > 1.0 → retorna "Não encontrei nenhum registro parecido."
        # 4. Se parcela_total > 1:
        #      salva EstadoConfirmacao(acao="EXCLUIR", pergunta_grupo=True, ...)
        #      retorna "Deseja excluir só esta parcela ou todas as N parcelas?"
        # 5. Se parcela_total == 1:
        #      salva EstadoConfirmacao(acao="EXCLUIR", pergunta_grupo=False, ...)
        #      retorna card de confirmação simples

    async def confirmar(self, numero: str, resposta: ConfirmacaoResposta) -> str:
        # ConfirmacaoResposta.tipo = "sim" | "nao" | "parcela" | "grupo"
        # 1. Busca EstadoConfirmacao
        # 2. Se pergunta_grupo=True e resposta não é "parcela"/"grupo" → pede para escolher
        # 3. Se resposta="parcela" → repository.excluir(transacao_id)
        # 4. Se resposta="grupo"  → repository.excluir_grupo(grupo_parcela_id)
        # 5. Se resposta="nao"    → cancela, limpa estado
        # 6. Limpa estado
```

### Threshold de similaridade (fix #4)

Ambos os services aplicam o mesmo critério:

```python
resultado, distancia = await repository.buscar_semantico_com_distancia(embedding, limite=1)
if distancia > 1.0:  # L2 distance > 1.0 = registros muito diferentes
    return "Não encontrei nenhum registro parecido com o que você descreveu. Pode detalhar mais?"
```

`buscar_semantico_com_distancia` retorna `tuple[Transacao, float]`. Adicionar este método ao contrato do repository.

## Critério de aceite

- [ ] Busca semântica com distância L2 > 1.0 retorna mensagem de "não encontrado"
- [ ] Confirmação positiva → dado alterado/excluído no banco
- [ ] Recusa → estado limpo, mensagem de cancelamento
- [ ] Parcelado: pergunta sobre escopo (`pergunta_grupo=True`) antes do sim/não
- [ ] Pipeline lê `pergunta_grupo` para rotear entre "parcela/grupo" vs "sim/não"
- [ ] Estado `AGUARDAR_PARCELAS` é limpado após resposta do usuário
- [ ] Estado expira após 5 min sem resposta
