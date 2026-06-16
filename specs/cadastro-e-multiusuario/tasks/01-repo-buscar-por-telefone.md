# Tarefa A (01) — UsuarioRepository.buscar_por_telefone

**Stack:** python
**Depende de:** contratos congelados
**Contratos:** `usuario-repository.md`

## Objetivo

Adicionar `buscar_por_telefone(telefone)` ao `UsuarioRepository`, filtrando por ativo e normalizando o telefone para dígitos. Base da resolução de identidade (webhook + endpoint).

## Arquivos (posse exclusiva)

- `backend/repositories/usuario_repository.py`
- `tests/test_usuario_repository.py`

## Escopo

1. Helper de normalização (só dígitos).
2. `async def buscar_por_telefone(self, telefone: str) -> Usuario | None`: `select(Usuario).where(Usuario.telefone == digitos, Usuario.ativo == True)`, `scalar_one_or_none()`.
3. Telefone vazio após normalização → retorna `None` sem consultar.
4. Não alterar nenhum outro método do repositório.

## Critérios de aceite → teste

- [ ] Usuário ativo com telefone correspondente → retorna o `Usuario`
- [ ] Usuário com `ativo = False` → retorna `None`
- [ ] Telefone inexistente → retorna `None`
- [ ] Telefone com máscara (`+55 (11) 99999-8888`) normaliza e encontra `5511999998888`
- [ ] Telefone vazio/só-símbolos → `None` sem query

> Testes com `AsyncSession` mockado/fake como já feito nos testes de repositório existentes (sem DB real).

## Verificação local

```bash
uv run pytest tests/test_usuario_repository.py -v
```
