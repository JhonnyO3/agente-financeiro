# Contrato: Webhook — Evolution API → Agente

**Status: Congelado**

## Endpoint

```
POST /webhook/mensagem
Content-Type: application/json
```

## Payload de entrada (Evolution API)

```json
{
  "event": "messages.upsert",
  "data": {
    "key": {
      "remoteJid": "5511957818539@s.whatsapp.net",
      "fromMe": false,
      "id": "MSG_ID"
    },
    "message": {
      "conversation": "texto da mensagem do usuário"
    },
    "messageTimestamp": 1718000000
  }
}
```

## Campos relevantes

| Campo                        | Uso                                              |
|------------------------------|--------------------------------------------------|
| `data.key.remoteJid`         | Extrai número de telefone para filtro de acesso  |
| `data.message.conversation`  | Texto da mensagem a processar                    |
| `data.messageTimestamp`      | Timestamp para ordenação no debounce             |

## Resposta HTTP

- `200 OK` — sempre, independente de autorização (não revelar rejeição a números não autorizados)

## Contrato do debounce

O entrypoint NÃO processa a mensagem imediatamente. Ele:
1. Armazena a mensagem em cache (chave = número de telefone, TTL = 10s)
2. Agenda processamento para daqui 10s
3. Se nova mensagem chegar antes dos 10s → faz append ao texto acumulado e reinicia o timer
4. Após 10s sem nova mensagem → dispara o pipeline com o texto completo

## Filtro de acesso

```python
numero_autorizado = settings.WHATSAPP_ALLOWED_NUMBER  # ex: "5511957818539"
numero_recebido = remoteJid.split("@")[0]
if numero_recebido != numero_autorizado:
    return {"status": "ok"}  # descarta silenciosamente
```
