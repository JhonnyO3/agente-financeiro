# Tarefa 06 — Service: Cadastrar Gasto/Investimento

**Stack:** python  
**Depende de:** 03-repository-transacoes, 05-agent-classificador  
**Arquivos próprios:** `app/services/cadastrar.py`

## Objetivo

Orquestrar o caso de uso de cadastro: extrair dados da mensagem, calcular parcelas, gerar embeddings e persistir N registros.

## Entregáveis

### `app/services/cadastrar.py`

```python
class CadastrarService:
    async def executar(self, mensagem: str) -> ResultadoCadastro: ...
    async def executar_com_parcelas_confirmadas(
        self, mensagem: str, parcela_total: int
    ) -> ResultadoCadastro: ...
```

### Fluxo interno

1. `extrator.extrair(mensagem)` → `ExtracaoResult`
2. Se `menciona_cartao and parcela_total == 1`:
   - `confirmacao_state.salvar(numero, EstadoConfirmacao(acao="AGUARDAR_PARCELAS", mensagem_original=mensagem))`
   - Retorna `ResultadoCadastro(aguarda_confirmacao=True, pergunta="É à vista ou parcelado? Se parcelado, quantas vezes?")`
   - **O pipeline não prossegue — aguarda próxima mensagem do usuário**
3. `categorizador.categorizar(...)` → categoria
4. Python calcula:
   - `valor_por_parcela = total / parcela_total` (Decimal, 2 casas; último absorve arredondamento)
   - Datas: `data_base`, `data_base + 30`, `data_base + 60` ... para cada parcela
   - `grupo_parcela_id = uuid4()`
5. `embedder.gerar_para_transacao(tipo, categoria, descricao, data_1a_parcela)` → 1 chamada OpenAI; mesmo vetor para todas as parcelas do grupo (ver `contracts/embedding.md`)
6. `repository.criar_lote(lista_de_transacao_create)`
7. Retorna `ResultadoCadastro` com resumo formatado

### `executar_com_parcelas_confirmadas`

Chamado pelo pipeline quando há `EstadoConfirmacao(acao="AGUARDAR_PARCELAS")` e o usuário respondeu com número de parcelas:

```python
async def executar_com_parcelas_confirmadas(
    self, mensagem_original: str, parcela_total: int, numero: str
) -> ResultadoCadastro:
    # Reutiliza o fluxo normal a partir do passo 3,
    # forçando parcela_total = valor respondido pelo usuário
    # e limpando o estado de confirmação ao final
```

### `ResultadoCadastro`

```python
@dataclass
class ResultadoCadastro:
    aguarda_confirmacao: bool = False
    pergunta: str | None = None          # quando aguarda_confirmacao=True
    transacoes: list[Transacao] = field(default_factory=list)
    mensagem_resposta: str = ""
```

## Critério de aceite

- [ ] "gastei 45 no mercado" → 1 registro, `parcela_total=1`, `categoria=ALIMENTACAO`
- [ ] "celular 6x de 150" → 6 registros com mesmo `grupo_parcela_id`, datas corretas
- [ ] "900 em 6x" → cada registro com `valor=150.00` (Python calculou)
- [ ] "comprei no cartão" → retorna `aguarda_confirmacao=True` sem salvar no banco
- [ ] Último centavo de divisão não exata absorvido na última parcela
- [ ] Todos os registros do lote compartilham o mesmo embedding
