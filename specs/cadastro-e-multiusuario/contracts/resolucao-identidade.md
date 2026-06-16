# Contrato: Resolução de identidade por telefone

**Status:** Congelado
**Fronteira:** webhook do agente (in-process) + endpoint REST `/auth` (administrativo/diagnóstico)

Há **dois caminhos** para resolver identidade por telefone. Ambos usam `UsuarioRepository.buscar_por_telefone` (ver `usuario-repository.md`). A decisão arquitetural (justificativa no `plan.md`):

- **Caminho quente (webhook):** in-process, chamada direta ao repositório. **É o usado em produção.**
- **Endpoint REST `/auth/...`:** criado para isolar as *rules* de identidade e para uso administrativo/diagnóstico futuro. **O webhook NÃO depende dele.**

---

## A) Resolução in-process (webhook) — Congelado

Função helper no webhook (ou em um pequeno serviço de identidade do agente):

```python
async def resolver_usuario_por_telefone(app_state, numero: str) -> Usuario | None:
    async with app_state.session_factory() as session:
        repo = UsuarioRepository(session)
        return await repo.buscar_por_telefone(numero)
```

- `app_state.session_factory` é exposto no `lifespan` (ver `worker-pipeline.md`).
- Lê com sessão sem `begin()` (somente leitura).
- Retorna o modelo `Usuario` ou `None`. O webhook usa `usuario.id` para enfileirar.
- **A cada mensagem** (RN-16: sem cache telefone→id).

## B) Endpoint REST `/auth/identidade/por-telefone/{telefone}` — Congelado

```
GET /auth/identidade/por-telefone/{telefone}
Authorization: Bearer <token>     ← autenticação de identidade (ver proteção abaixo)

200 application/json → corpo UsuarioResponse (id, nome, username, email, telefone, role, ativo, criado_em)
204 No Content       → telefone não corresponde a usuário ativo (inexistente OU inativo)
401                  → sem token / token inválido
```

- Vive em `backend/controllers/auth.py` (mesmo módulo do `/auth`, prefixo `/auth`) — **não** em `/admin`.
- Path da rota: `/auth/identidade/por-telefone/{telefone}`.
- Reusa `UsuarioRepository.buscar_por_telefone` (já filtra ativo) → inativo e inexistente caem ambos em 204.
- Resposta 200 reusa `backend.dtos.usuario.UsuarioResponse.de_modelo(...).model_dump()`.
- **Normalização** do path param: dígitos apenas, delegada ao repositório.

### Proteção

- Exige **usuário autenticado** (`get_usuario_atual` — Bearer válido). Retorna 401 sem token válido.
- **Não** usa `get_admin` (a allowlist de admin é regra de gestão, não de identidade). Mantém as regras de identidade isoladas das de administração — objetivo da decisão do usuário.
- Não revela diferença entre inativo e inexistente (ambos 204), evitando enumeração.

## Invariantes comuns

- Inativo e inexistente são **indistinguíveis** para o chamador (discard / 204).
- Nenhum dos caminhos cacheia telefone→id.
- Nenhum vazamento entre usuários: a resolução só devolve o usuário daquele telefone.
