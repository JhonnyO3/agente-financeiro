from pathlib import Path

_FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


def _modulos_python():
    return [p for p in _FRONTEND.rglob("*.py")]


def test_frontend_nao_importa_camada_de_dados():
    for arquivo in _modulos_python():
        conteudo = arquivo.read_text(encoding="utf-8")
        assert "backend.repositories" not in conteudo, arquivo
        assert "backend.models" not in conteudo, arquivo
        assert "import agent" not in conteudo, arquivo
        assert "from agent" not in conteudo, arquivo


def test_frontend_nao_acessa_banco():
    proibidos = ("sqlalchemy", "asyncpg", "SessionFactory", "create_engine")
    for arquivo in _modulos_python():
        conteudo = arquivo.read_text(encoding="utf-8")
        for termo in proibidos:
            assert termo not in conteudo, f"{arquivo} contém {termo}"
