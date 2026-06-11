from pathlib import Path

_FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


def _modulos_python():
    return [p for p in _FRONTEND.rglob("*.py")]


def test_frontend_nao_importa_app_repositories():
    for arquivo in _modulos_python():
        conteudo = arquivo.read_text(encoding="utf-8")
        assert "app.repositories" not in conteudo, arquivo
        assert "import app" not in conteudo, arquivo
        assert "from app" not in conteudo, arquivo


def test_frontend_nao_acessa_banco():
    proibidos = ("sqlalchemy", "asyncpg", "SessionFactory", "create_engine")
    for arquivo in _modulos_python():
        conteudo = arquivo.read_text(encoding="utf-8")
        for termo in proibidos:
            assert termo not in conteudo, f"{arquivo} contém {termo}"
