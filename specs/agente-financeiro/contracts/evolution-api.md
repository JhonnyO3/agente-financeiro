# Contrato: Evolution API — Envio de Mensagem

**Status: Congelado**

## Endpoint de envio

```
POST {EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}
Authorization: Bearer {EVOLUTION_API_KEY}
Content-Type: application/json
```

## Payload

```json
{
  "number": "5511957818539",
  "text": "texto da resposta do agente"
}
```

## Interface no código

```python
class EvolutionApiClient:
    async def enviar_mensagem(self, numero: str, texto: str) -> None: ...
```

## Variáveis de ambiente necessárias

| Variável                  | Exemplo                              |
|---------------------------|--------------------------------------|
| `EVOLUTION_API_URL`       | `http://localhost:8080`              |
| `EVOLUTION_INSTANCE`      | `minha-instancia`                    |
| `EVOLUTION_API_KEY`       | `sua-chave-aqui`                     |
| `WHATSAPP_ALLOWED_NUMBER` | `5511957818539`                      |
| `DATABASE_URL`            | `postgresql+asyncpg://...`           |
| `OPENAI_API_KEY`          | `sk-...`                             |

## Comportamento de erro

- Falha no envio → loga o erro, não re-tenta (Evolution tem retry próprio)
- Timeout = 10s por requisição
