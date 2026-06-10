# Tarefa 04 — Webhook Receiver + Debounce

**Stack:** python  
**Depende de:** 01-setup-projeto  
**Arquivos próprios:** `app/entrypoint/webhook.py`, `app/entrypoint/debounce.py`, `app/entrypoint/main.py`

## Objetivo

Receber o webhook da Evolution API, filtrar número autorizado e implementar o debounce de 10s antes de despachar para o pipeline.

## Contrato de referência

`contracts/webhook.md` — payload, filtro e lógica de debounce.

## Entregáveis

### `app/entrypoint/main.py`

App FastAPI com router do webhook montado em `/webhook`.

### `app/entrypoint/debounce.py`

```python
class MessageDebouncer:
    _timers: dict[str, asyncio.TimerHandle] = {}
    _buffers: dict[str, list[str]] = {}

    async def receber(self, numero: str, texto: str, callback: Callable) -> None:
        self._buffers.setdefault(numero, []).append(texto)
        if numero in self._timers:
            self._timers[numero].cancel()
        loop = asyncio.get_event_loop()
        self._timers[numero] = loop.call_later(10, self._disparar, numero, callback)

    def _disparar(self, numero: str, callback: Callable) -> None:
        texto_acumulado = " ".join(self._buffers.pop(numero, []))
        self._timers.pop(numero, None)
        asyncio.ensure_future(callback(numero, texto_acumulado))
```

### `app/entrypoint/webhook.py`

```python
@router.post("/mensagem")
async def receber_mensagem(payload: dict) -> dict:
    numero = extrair_numero(payload)
    texto = extrair_texto(payload)
    if numero != settings.WHATSAPP_ALLOWED_NUMBER:
        return {"status": "ok"}
    await debouncer.receber(numero, texto, pipeline.processar)
    return {"status": "ok"}
```

- `extrair_numero`: `data.key.remoteJid.split("@")[0]`
- `extrair_texto`: tenta `data.message.conversation`; se ausente (áudio, imagem, reação, sticker) → retorna `None`
- Se `texto is None` → retorna `200 OK` sem chamar pipeline (mensagem não-texto é ignorada silenciosamente)
- Retorna sempre `200 OK`

```python
def extrair_texto(payload: dict) -> str | None:
    msg = payload.get("data", {}).get("message", {})
    return msg.get("conversation") or msg.get("extendedTextMessage", {}).get("text")
```

## Critério de aceite

- [ ] POST com número não autorizado → retorna 200 sem chamar pipeline
- [ ] Duas mensagens enviadas com < 10s de diferença → pipeline recebe texto concatenado
- [ ] Mensagem única → pipeline chamado após ~10s
- [ ] `pytest` cobre o filtro de número (teste unitário)
