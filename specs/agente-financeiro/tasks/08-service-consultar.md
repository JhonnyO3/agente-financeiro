# Tarefa 08 — Service: Consultar e Resumos

**Stack:** python  
**Depende de:** 03-repository-transacoes, 05-agent-classificador  
**Arquivos próprios:** `app/services/consultar.py`

## Objetivo

Extrair filtros da mensagem, executar queries em Python e retornar dados estruturados para formatação.

## Entregáveis

### `app/services/consultar.py`

```python
class ConsultarService:
    async def executar(self, mensagem: str) -> ResultadoConsulta: ...
```

### Fluxo interno por tipo de consulta

**mensal:**
1. `filtro_chain.extrair(mensagem)` → `FiltroConsultaResult(mes=M, ano=A)`
2. Python calcula `inicio = date(A, M, 1)` e `fim = date(A, M, último_dia)`
3. `repository.agregar_por_categoria(inicio, fim)` → lista de `AgregadoCategoria`
4. Python separa gastos e investimentos pelo campo `tipo` (não misturar na mesma soma)
5. Retorna `ResultadoConsulta`

**semanal:**
1. Python calcula `inicio` e `fim` com `date.today().isocalendar()` — semana ISO (segunda a domingo)
   ```python
   hoje = date.today()
   inicio = hoje - timedelta(days=hoje.weekday())  # weekday() == 0 → segunda
   fim = inicio + timedelta(days=6)                # domingo
   ```
2. Segue mesmo fluxo do mensal a partir do passo 3

**grupo_parcela:**
1. `filtro_chain.extrair(mensagem)` → `FiltroConsultaResult(descricao_grupo="celular")`
2. `embedder.gerar(descricao_grupo)` → vetor de busca
3. `repository.buscar_semantico_com_distancia(embedding, limite=1)` → pega `grupo_parcela_id`
4. `repository.buscar_por_grupo(grupo_parcela_id)` → todas as parcelas ordenadas por `parcela_numero`
5. Python calcula status de cada parcela (fix #8 — lógica correta):
   ```python
   hoje = date.today()
   if parcela.data < hoje:
       status = "Paga"
   elif parcela.data <= fim_do_mes_atual:
       status = "Próxima"
   else:
       status = "Futura"
   # "Próxima" = vence ainda neste mês e ainda não passou
   ```

**geral:**
- `repository.agregar_por_categoria(date(2000, 1, 1), date.today())` — piso fixo, não `date.min` (fix #10)
- Python soma separado para `GASTO` e `INVESTIMENTO`

### `ResultadoConsulta`

```python
@dataclass
class ResultadoConsulta:
    tipo: str
    periodo_label: str
    total_gastos: Decimal
    total_investimentos: Decimal
    por_categoria: list[AgregadoCategoria]
    parcelas: list[ParcelaStatus] | None = None  # para tipo=grupo_parcela

@dataclass
class ParcelaStatus:
    parcela_numero: int
    parcela_total: int
    valor: Decimal
    data: date
    status: Literal["Paga", "Próxima", "Futura"]
```

## Critério de aceite

- [ ] "resumo de junho" → totais calculados em Python com Decimal (não float)
- [ ] Resumo mensal não duplica parcelas futuras — conta só a do mês
- [ ] "parcelas do celular" → lista completa com status correto por data
- [ ] "quanto gastei essa semana" → período seg–dom da semana atual
- [ ] Nenhuma operação matemática delegada ao LLM
