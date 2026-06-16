# Contrato: UsuarioRepository.buscar_por_telefone

**Status:** Congelado
**Fronteira:** `backend/repositories/usuario_repository.py` ↔ resolução de identidade (webhook in-process + endpoint /auth)

## Assinatura

```python
async def buscar_por_telefone(self, telefone: str) -> Usuario | None:
    ...
```

## Comportamento

- Normaliza `telefone` para **apenas dígitos** antes de comparar (remove `+`, espaços, hífens, parênteses).
- Filtra por **usuário ativo**: `WHERE telefone = :tel AND ativo = True`.
- Retorna o `Usuario` (modelo ORM) quando há correspondência ativa; caso contrário `None`.
- Usuário com `ativo = False` retorna `None` (mesma resposta de inexistente — discard silencioso a cargo do chamador).
- Telefone vazio/`""` após normalização → `None` (não consulta com filtro vazio).

## Normalização (determinística)

```python
def _so_digitos(t: str) -> str:
    return "".join(ch for ch in (t or "") if ch.isdigit())
```

> A coluna `telefone` é armazenada já como dígitos (RN-07). A normalização no repositório protege contra entradas com máscara vindas de qualquer chamador.

## Invariantes

- **Não** muda nenhuma outra assinatura do `UsuarioRepository`.
- **Não** filtra por role — qualquer usuário ativo com aquele telefone resolve.
- Determinístico: índice único parcial em `telefone` garante no máximo 1 ativo por número.

## Como o chamador interpreta

| Retorno | Significado | Ação do webhook |
|---|---|---|
| `Usuario` | Cadastrado e ativo | Enfileira `(usuario.id, numero, texto)` |
| `None` | Inexistente OU inativo | Discard silencioso (HTTP 200) |
