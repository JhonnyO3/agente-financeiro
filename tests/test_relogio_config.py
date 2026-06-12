"""
Testes vermelhos (TDD) — Task 03: Relogio injetavel + novas Settings
Cenários espelhados de: specs/melhorias-agente/scenarios/03-relogio-config.feature

ESTADO ESPERADO: vermelho (red) — implementação ainda não existe.
"""

import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

# Caminho absoluto do worktree (usado para inspecionar sources sem executar o singleton)
_WORKTREE = Path(__file__).parent.parent
_CONFIG_PY = _WORKTREE / "agent" / "config.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OBRIGATORIOS_BASE = {
    "DATABASE_URL": "postgresql+asyncpg://u:p@localhost/db",
    "OPENAI_API_KEY": "sk-fake",
    "EVOLUTION_API_URL": "http://localhost:8080",
    "EVOLUTION_INSTANCE": "inst",
    "EVOLUTION_API_KEY": "evo-fake",
    "WHATSAPP_ALLOWED_NUMBER": "+5511999999999",
    "AGENTE_USUARIO_EMAIL": "admin@exemplo.com",
    "RESPONSAVEL_PADRAO": "Admin Teste",
    "WEBHOOK_APIKEY": "webhook-secret",
    "REDIS_URL": "redis://localhost:6379/0",
}


def _importar_settings_classe():
    """
    Importa a classe Settings sem executar o singleton module-level.
    Usa monkeypatch de sys.modules para reimportar limpo com env vars controladas.
    """
    # Limpa cache do módulo para reimportar
    for mod in list(sys.modules.keys()):
        if mod.startswith("agent.config"):
            del sys.modules[mod]

    from agent.config import Settings  # noqa: PLC0415
    return Settings


def _settings_com(env: dict):
    """Instancia Settings sem ler .env, usando apenas o dict fornecido."""
    # Define env vars necessárias para que o module-level não falhe
    old_env = {}
    for k, v in env.items():
        old_env[k] = os.environ.get(k)
        os.environ[k] = v

    try:
        for mod in list(sys.modules.keys()):
            if mod.startswith("agent.config"):
                del sys.modules[mod]
        from agent.config import Settings  # noqa: PLC0415
        return Settings(_env_file=None, **env)
    finally:
        for k, old_v in old_env.items():
            if old_v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = old_v


# ---------------------------------------------------------------------------
# Cenário: hoje() retorna a data no fuso America/Sao_Paulo quando UTC ja virou o dia
# ---------------------------------------------------------------------------

class TestRelogioHoje:
    def test_hoje_brt_quando_utc_virou_dia(self):
        """
        UTC 2026-06-12T02:30:00Z → BRT (UTC-3) ainda é 2026-06-11 às 23:30.
        hoje() deve retornar date(2026, 6, 11), não date(2026, 6, 12).
        """
        from agent.services.relogio import Relogio  # noqa: PLC0415

        utc_fixo = datetime(2026, 6, 12, 2, 30, 0, tzinfo=timezone.utc)
        relogio = Relogio("America/Sao_Paulo", _fixed=utc_fixo)

        resultado = relogio.hoje()

        assert resultado == date(2026, 6, 11), (
            f"Esperado 2026-06-11 (BRT), mas got {resultado}"
        )
        assert resultado != date(2026, 6, 12)

    def test_hoje_brt_retorna_date(self):
        """hoje() retorna um objeto date, não datetime."""
        from agent.services.relogio import Relogio  # noqa: PLC0415

        utc_fixo = datetime(2026, 6, 12, 3, 0, 0, tzinfo=timezone.utc)
        relogio = Relogio("America/Sao_Paulo", _fixed=utc_fixo)

        assert isinstance(relogio.hoje(), date)
        assert not isinstance(relogio.hoje(), datetime)  # date, não datetime


# ---------------------------------------------------------------------------
# Cenário: agora() retorna datetime aware no fuso configurado
# ---------------------------------------------------------------------------

class TestRelogioAgora:
    def test_agora_e_aware(self):
        """agora() deve retornar datetime com tzinfo não-None."""
        from agent.services.relogio import Relogio  # noqa: PLC0415

        relogio = Relogio("America/Sao_Paulo")
        resultado = relogio.agora()

        assert resultado.tzinfo is not None, "agora() deve ser datetime aware"

    def test_agora_fuso_america_sao_paulo(self):
        """agora() com tz='America/Sao_Paulo' deve ter offset correto."""
        from agent.services.relogio import Relogio  # noqa: PLC0415

        utc_fixo = datetime(2026, 6, 12, 3, 0, 0, tzinfo=timezone.utc)
        relogio = Relogio("America/Sao_Paulo", _fixed=utc_fixo)
        resultado = relogio.agora()

        tz_esperado = ZoneInfo("America/Sao_Paulo")
        esperado_offset = utc_fixo.astimezone(tz_esperado).utcoffset()
        assert resultado.utcoffset() == esperado_offset

    def test_agora_com_fixo_retorna_instante_correto(self):
        """agora() com base fixa retorna o instante convertido para o fuso (03:00 UTC = 00:00 BRT)."""
        from agent.services.relogio import Relogio  # noqa: PLC0415

        utc_fixo = datetime(2026, 6, 12, 3, 0, 0, tzinfo=timezone.utc)
        relogio = Relogio("America/Sao_Paulo", _fixed=utc_fixo)

        resultado = relogio.agora()

        assert resultado.tzinfo is not None
        # 03:00 UTC = 00:00 BRT (UTC-3)
        assert resultado.hour == 0
        assert resultado.day == 12


# ---------------------------------------------------------------------------
# Cenário: Relogio aceita fuso alternativo
# ---------------------------------------------------------------------------

class TestRelogioFusoAlternativo:
    def test_fuso_utc_coerente(self):
        """Relogio('UTC').hoje() deve ser coerente com UTC."""
        from agent.services.relogio import Relogio  # noqa: PLC0415

        utc_fixo = datetime(2026, 6, 12, 3, 0, 0, tzinfo=timezone.utc)
        relogio = Relogio("UTC", _fixed=utc_fixo)

        assert relogio.hoje() == date(2026, 6, 12)


# ---------------------------------------------------------------------------
# Cenário: Settings — campos obrigatórios sem default
# ---------------------------------------------------------------------------

class TestSettingsObrigatorios:
    """
    Estes testes ficam vermelhos enquanto os campos não existirem em config.py.
    Quando o impl-03 adicionar os campos, os testes devem ficar verdes — e
    o `_settings_com(env_sem_campo)` deve levantar ValidationError por campo ausente.
    """

    def test_sem_responsavel_padrao_levanta_validacao(self):
        env = {k: v for k, v in _OBRIGATORIOS_BASE.items() if k != "RESPONSAVEL_PADRAO"}

        with pytest.raises((ValidationError, TypeError)):
            _settings_com(env)

    def test_sem_webhook_apikey_levanta_validacao(self):
        env = {k: v for k, v in _OBRIGATORIOS_BASE.items() if k != "WEBHOOK_APIKEY"}

        with pytest.raises((ValidationError, TypeError)):
            _settings_com(env)

    def test_sem_agente_usuario_email_levanta_validacao(self):
        """AGENTE_USUARIO_EMAIL perdeu o default hardcoded — agora é obrigatório."""
        env = {k: v for k, v in _OBRIGATORIOS_BASE.items() if k != "AGENTE_USUARIO_EMAIL"}

        with pytest.raises((ValidationError, TypeError)):
            _settings_com(env)

    def test_sem_redis_url_levanta_validacao(self):
        env = {k: v for k, v in _OBRIGATORIOS_BASE.items() if k != "REDIS_URL"}

        with pytest.raises((ValidationError, TypeError)):
            _settings_com(env)


# ---------------------------------------------------------------------------
# Cenário: Settings carrega valores padrão para campos opcionais
# ---------------------------------------------------------------------------

class TestSettingsDefaults:
    def test_defaults_opcionais(self):
        """Novos campos opcionais devem ter os defaults do contrato."""
        s = _settings_com(_OBRIGATORIOS_BASE)

        assert s.TIMEZONE_USUARIO == "America/Sao_Paulo"
        assert s.DEBOUNCE_SEGUNDOS == 5
        assert s.CONFIANCA_MINIMA == pytest.approx(0.7)
        assert s.RAG_PISO == pytest.approx(1.0)
        assert s.RAG_MARGEM == pytest.approx(0.15)
        assert s.RAG_MAX_OPCOES == 5
        assert s.LLM_MODELO_CLASSIFICACAO == "gpt-4o-mini"
        assert s.LLM_MODELO_CONVERSAR == "gpt-4o"

    def test_obrigatorios_aceitam_valor_customizado(self):
        env = dict(_OBRIGATORIOS_BASE)
        env["RESPONSAVEL_PADRAO"] = "Jhonatas"
        env["TIMEZONE_USUARIO"] = "America/Manaus"

        s = _settings_com(env)

        assert s.RESPONSAVEL_PADRAO == "Jhonatas"
        assert s.TIMEZONE_USUARIO == "America/Manaus"

    def test_agente_usuario_email_sem_default_no_source(self):
        """AGENTE_USUARIO_EMAIL não pode ter default hardcoded no source de config.py."""
        source = _CONFIG_PY.read_text(encoding="utf-8")

        # Se o default pessoal ainda estiver no source, o teste falha (RED correto)
        assert 'AGENTE_USUARIO_EMAIL: str = ' not in source, (
            "AGENTE_USUARIO_EMAIL não deve ter default hardcoded em config.py"
        )

    def test_novos_campos_existem_no_source(self):
        """Verifica que os novos campos do contrato aparecem no source de config.py."""
        source = _CONFIG_PY.read_text(encoding="utf-8")

        campos_esperados = [
            "RESPONSAVEL_PADRAO",
            "TIMEZONE_USUARIO",
            "WEBHOOK_APIKEY",
            "REDIS_URL",
            "DEBOUNCE_SEGUNDOS",
            "CONFIANCA_MINIMA",
            "RAG_PISO",
            "RAG_MARGEM",
            "RAG_MAX_OPCOES",
            "LLM_MODELO_CLASSIFICACAO",
            "LLM_MODELO_CONVERSAR",
        ]
        campos_faltando = [c for c in campos_esperados if c not in source]
        assert not campos_faltando, f"Campos ausentes em Settings: {campos_faltando}"
