# Contrato: Tela de cadastro de usuário (dashboard Flask)

**Status:** Congelado
**Fronteira:** browser ↔ Flask (`frontend/`) ↔ `BackendClient` ↔ `POST /admin/usuarios`

## Rotas Flask

| Rota | Método | Comportamento |
|---|---|---|
| `/admin/usuarios/novo` | GET | Renderiza o formulário de cadastro. Exige admin. |
| `/admin/usuarios/novo` | POST | Valida, deriva `username`, chama `BackendClient.criar_usuario(body)`, trata 201/409/422. |

> Blueprint novo (ex.: `frontend/blueprints/admin_usuarios.py`), registrado em `create_app`. Não colide com `auth.py`/`dashboard.py`/`api_proxy.py`.

## Proteção de rota

- A rota é protegida pelo `before_request` existente (não-autenticado → redirect login).
- Além disso, exige **role ADMIN**: se `sessao` não for admin, redirect para login (RN-01 / critério "rejeita não-admin").
- `sessao` já guarda `role` (`gravar_tokens(..., role=...)`). Usar `session.get("role") == "ADMIN"`.

## Formulário (campos)

| Campo | Obrigatório | Validação client-side |
|---|---|---|
| Nome | sim | não vazio |
| E-mail | sim | contém `@` |
| Telefone | sim | só dígitos, 10–15 caracteres |
| Senha | sim | não vazio |

- `role` não aparece no formulário básico (default USER no backend). (Opcional: checkbox "tornar admin" — fora do mínimo.)

## Derivação de username

```python
username = email.split("@")[0]
```

Feito no handler Flask antes de montar o body. Não exposto ao admin (RN-05).

## Mapeamento → POST /admin/usuarios

```json
{
  "nome": "<form.nome>",
  "username": "<email.split('@')[0]>",
  "email": "<form.email>",
  "senha": "<form.senha>",
  "telefone": "<form.telefone (só dígitos)>",
  "role": "USER"
}
```

Chamado via `BackendClient.criar_usuario(body)` (novo método no client, reusa `_autenticado` → injeta Bearer + refresh).

## Tratamento de resposta

| Status backend | Ação na tela |
|---|---|
| 201 | Flash "Usuário cadastrado com sucesso!" + redirect para lista de usuários (`/admin/usuarios` no front, ou o dashboard se a lista não existir) |
| 409 | Re-renderiza o form com erro "Este e-mail já está cadastrado." **preservando** nome/telefone preenchidos (não a senha) |
| 422 | Re-renderiza com "Dados inválidos." preservando campos não-sensíveis |
| 503 / erro httpx | "Backend indisponível." |

## BackendClient (novo método)

```python
def criar_usuario(self, body: dict) -> httpx.Response:
    return self._autenticado("POST", "/admin/usuarios", json=body)
```

- Posse: `frontend/services/backend_client.py` é compartilhado — **adição de um método** é a única edição; sem conflito com outras tasks (nenhuma outra task toca esse arquivo nesta feature).

## Template

- `frontend/templates/admin/usuarios_novo.html`, estende `base.html`.
- Mostra erros via bloco de flash/variável `erro`; reexibe valores submetidos.

## Invariantes

- Nenhuma mudança na API backend (`POST /admin/usuarios` já existe; `telefone` segue opcional na API, obrigatório só no front — sem migration).
- Senha nunca reexibida no HTML após erro.
