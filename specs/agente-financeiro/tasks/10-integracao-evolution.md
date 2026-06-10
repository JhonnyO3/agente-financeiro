# Tarefa 10 — Integração Evolution API (Envio) + Wiring Final

**Stack:** python  
**Depende de:** 04-webhook-receiver, 09-formatacao-respostas  
**Arquivos próprios:** `app/integrations/evolution_client.py`

## Objetivo

Implementar o cliente HTTP para envio de mensagens via Evolution API e conectar o pipeline ao webhook para fechar o ciclo completo.

## Contrato de referência

`contracts/evolution-api.md` — endpoint, payload e variáveis de ambiente.

## Entregáveis

### `app/integrations/evolution_client.py`

```python
class EvolutionApiClient:
    def __init__(self, base_url: str, instance: str, api_key: str):
        self._client = httpx.AsyncClient(timeout=10.0)

    async def enviar_mensagem(self, numero: str, texto: str) -> None:
        url = f"{self._base_url}/message/sendText/{self._instance}"
        payload = {"number": numero, "text": texto}
        headers = {"Authorization": f"Bearer {self._api_key}"}
        await self._client.post(url, json=payload, headers=headers)
```

Falha no envio → loga com `logging.error`, não propaga exceção.

### Wiring no `app/entrypoint/webhook.py`

O callback do debounce chama `pipeline.processar(numero, texto)` → obtém resposta → chama `evolution_client.enviar_mensagem(numero, resposta)`.

### `app/entrypoint/main.py` — lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: criar pool de banco, inicializar clientes
    yield
    # shutdown: fechar conexões
```

## Critério de aceite

- [ ] Envio de mensagem via Evolution API funciona com credenciais reais
- [ ] Falha no envio não derruba o servidor (exceção capturada)
- [ ] Ciclo completo: mensagem WhatsApp → webhook → debounce → pipeline → resposta enviada
- [ ] `docker compose up` + servidor rodando → fluxo ponta a ponta testável manualmente
