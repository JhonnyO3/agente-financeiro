# Contrato: Webhook, Fila e Worker

**Status:** Congelado
**Fronteira:** Evolution API ↔ Webhook ↔ Fila ↔ Worker ↔ Roteador
**Arquivos de posse:** `agent/entrypoint/webhook.py`, `agent/entrypoint/worker.py`

## Webhook (`POST /webhook/mensagem`)

Responsabilidade: **autenticar, filtrar, deduplicar, enfileirar, 200**. Sem lógica de negócio.

```
1. AUTENTICAÇÃO: header `apikey` == Settings.WEBHOOK_APIKEY (comparação constante-time).
   Ausente/divergente → HTTP 401 (NÃO 200 silencioso).
2. FILTROS (silenciosos, 200 {"status":"ok"}):
   - evento != "messages.upsert" → descarta
   - data.key.fromMe == true → descarta (anti-loop)
   - numero (remoteJid) != Settings.WHATSAPP_ALLOWED_NUMBER → descarta (single-user v1)
   - sem texto (conversation / extendedTextMessage.text) → descarta
3. DEDUP: message_id = data.key.id; se já visto (dedup store TTL ~10min) → descarta.
4. EXTRAI: usuario_id (resolvido no boot), numero, texto, message_id, timestamp.
5. ENFILEIRA: fila por numero/usuario_id (preserva ordem por usuário).
6. RETORNA 200 imediatamente.
```

- `usuario_id` é o resolvido no lifespan por `AGENTE_USUARIO_EMAIL` (sem default — obrigatório).
- Não logar payload inteiro em INFO (PII): logar só metadados (numero mascarado, message_id).

## Dedup store

- `dict[str, datetime]` (message_id → visto_em) in-memory, TTL ~10 min, poda na inserção.
- Suficiente para neutralizar retry da Evolution. Invariante 1 worker (mesma de `EstadoStore`).

## Fila + Worker (`agent/entrypoint/worker.py`)

- **Uma fila por `numero`/`usuario_id`** (garante ordem por usuário). `asyncio.Queue` ou dict de buffers.
- **Micro-debounce ~5s** (`Settings.DEBOUNCE_SEGUNDOS`, default 5): cada mensagem reinicia o timer; ao disparar, agrupa o buffer com **`"\n"`** (preserva detecção de múltiplos itens) e processa **uma vez**.
- Correções do debounce atual: junta com `"\n"` (não espaço); **guarda referência** da task (evita GC); usa **lock** por usuário.
- Ao processar: chama `Classificador → Roteador → Formatador` e envia via `EvolutionApiClient`.
- **Histórico:** após processar, `EstadoStore.registrar_mensagem` para a mensagem do usuário (agrupada) e para a resposta enviada.
- **Erro:** qualquer exceção no processamento ⇒ enviar mensagem de falha amigável ao usuário (best-effort). **Nunca silêncio** (corrige bug crítico atual).

## Contrato de saída do worker

```python
async def processar(usuario_id: int, numero: str, texto: str) -> None
```
- Idempotente em relação a duplicações (dedup já filtrou no webhook).
- Recebe o texto **já agrupado** pelo debounce.

## Critérios de aceitação

- `apikey` ausente/errado → 401.
- Mesma `message_id` duas vezes → processa uma vez.
- Dois fragmentos em < 5s → um único processamento com texto unido por `"\n"`.
- Exceção no processamento → usuário recebe mensagem de erro (mock do client é chamado).
- Filtros (fromMe/evento/numero/sem texto) retornam 200 sem processar.
