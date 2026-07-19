from backend.models.transacao import Transacao

_GASTOS_FIXOS = "GASTOS_FIXOS"


def _como_str(campo) -> str:
    return getattr(campo, "value", campo)


def chave_recorrencia(t: Transacao) -> tuple[str, str, str]:
    return (t.descricao or "", _como_str(t.categoria), _como_str(t.tipo))


def eh_recorrente(t: Transacao) -> bool:
    if getattr(t, "recorrente", False):
        return True
    return _como_str(t.categoria) == _GASTOS_FIXOS and t.parcela_total == 1


def consolidar_templates(
    transacoes: list[Transacao],
) -> dict[tuple[str, str, str], Transacao]:
    por_chave: dict[tuple[str, str, str], Transacao] = {}
    for t in transacoes:
        if not eh_recorrente(t):
            continue
        chave = chave_recorrencia(t)
        atual = por_chave.get(chave)
        if atual is None or t.data > atual.data:
            por_chave[chave] = t
    return por_chave
