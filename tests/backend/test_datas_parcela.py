"""
Testes TDD para backend.services.datas_parcela.

Módulo ainda não existe — todos os testes devem FALHAR (vermelho).
Contratos: specs/parcelas-assinaturas/contracts/datas-parcela.md
Cenários:  specs/parcelas-assinaturas/scenarios/01-base-datas-repositorio.feature
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")

from datetime import date

import pytest

from backend.services.datas_parcela import adicionar_meses, datas_do_grupo, status_por_data
from backend.models.enums import StatusEnum


# ---------------------------------------------------------------------------
# adicionar_meses
# ---------------------------------------------------------------------------


class TestAdicionarMeses:
    def test_dia_existente_no_mes_destino(self):
        assert adicionar_meses(date(2026, 3, 15), 1) == date(2026, 4, 15)

    def test_clamp_31_para_fevereiro_nao_bissexto(self):
        # Cenário: adicionar_meses clampeia dia 31 para fim de fevereiro (não bissexto)
        assert adicionar_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)

    def test_clamp_31_para_fim_de_abril(self):
        # Cenário: adicionar_meses clampeia dia 31 para fim de abril
        assert adicionar_meses(date(2026, 3, 31), 1) == date(2026, 4, 30)

    def test_meses_negativos_recua_no_tempo(self):
        # Cenário: adicionar_meses com meses negativos recua no tempo
        assert adicionar_meses(date(2026, 3, 31), -1) == date(2026, 2, 28)

    def test_preserva_dia_em_fevereiro_bissexto(self):
        # Cenário: adicionar_meses preserva dia em fevereiro bissexto
        assert adicionar_meses(date(2024, 1, 29), 1) == date(2024, 2, 29)

    def test_soma_zero_retorna_mesma_data(self):
        d = date(2026, 6, 15)
        assert adicionar_meses(d, 0) == d

    def test_soma_varios_meses(self):
        assert adicionar_meses(date(2026, 1, 1), 12) == date(2027, 1, 1)

    def test_subtrai_varios_meses(self):
        assert adicionar_meses(date(2026, 6, 15), -6) == date(2025, 12, 15)


# ---------------------------------------------------------------------------
# status_por_data
# ---------------------------------------------------------------------------


class TestStatusPorData:
    def test_data_passada_retorna_pago(self):
        # Cenário: status_por_data retorna PAGO para data passada
        resultado = status_por_data(date(2026, 6, 11), hoje=date(2026, 6, 12))
        assert resultado == StatusEnum.PAGO

    def test_hoje_retorna_pendente(self):
        # Cenário: status_por_data retorna PENDENTE para hoje
        resultado = status_por_data(date(2026, 6, 12), hoje=date(2026, 6, 12))
        assert resultado == StatusEnum.PENDENTE

    def test_data_futura_retorna_pendente(self):
        # Cenário: status_por_data retorna PENDENTE para data futura
        resultado = status_por_data(date(2026, 7, 1), hoje=date(2026, 6, 12))
        assert resultado == StatusEnum.PENDENTE

    def test_hoje_default_nao_levanta(self):
        # Quando hoje=None, usa date.today() internamente — não deve lançar exceção
        resultado = status_por_data(date(2100, 1, 1))
        assert resultado == StatusEnum.PENDENTE


# ---------------------------------------------------------------------------
# datas_do_grupo
# ---------------------------------------------------------------------------


class TestDatasDoGrupo:
    def test_parcela_atual_1_gera_cadeia_crescente(self):
        # Cenário: datas_do_grupo com parcela_atual=1 gera cadeia crescente
        resultado = datas_do_grupo(date(2026, 6, 5), parcela_atual=1, parcela_total=3)
        assert resultado == [date(2026, 6, 5), date(2026, 7, 5), date(2026, 8, 5)]

    def test_ancora_parcela_atual_e_recua_anteriores(self):
        # Cenário: datas_do_grupo ancora a parcela atual e recua as anteriores
        resultado = datas_do_grupo(date(2026, 6, 5), parcela_atual=3, parcela_total=5)
        assert resultado == [
            date(2026, 4, 5),
            date(2026, 5, 5),
            date(2026, 6, 5),
            date(2026, 7, 5),
            date(2026, 8, 5),
        ]

    def test_clamp_em_mes_curto_no_retrocesso(self):
        # Cenário: datas_do_grupo clampeia data de retrocesso em mês curto
        resultado = datas_do_grupo(date(2026, 3, 31), parcela_atual=2, parcela_total=3)
        assert resultado == [date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)]

    def test_tamanho_da_lista_igual_a_parcela_total(self):
        # Cenário: datas_do_grupo retorna lista com parcela_total elementos
        resultado = datas_do_grupo(date(2026, 6, 10), parcela_atual=2, parcela_total=6)
        assert len(resultado) == 6

    def test_indice_da_parcela_atual_e_a_data_base(self):
        # Cenário: o elemento de índice 1 (parcela 2) é 2026-06-10
        resultado = datas_do_grupo(date(2026, 6, 10), parcela_atual=2, parcela_total=6)
        # índice 1 corresponde à parcela 2 (parcela_atual)
        assert resultado[1] == date(2026, 6, 10)

    def test_formula_contrato_datas_i_eq_adicionar_meses(self):
        # datas[i] = adicionar_meses(data_parcela_atual, i + 1 - parcela_atual)
        base = date(2026, 6, 5)
        parcela_atual = 3
        parcela_total = 5
        resultado = datas_do_grupo(base, parcela_atual=parcela_atual, parcela_total=parcela_total)
        for i in range(parcela_total):
            esperado = adicionar_meses(base, i + 1 - parcela_atual)
            assert resultado[i] == esperado, f"índice {i}: esperado {esperado}, obtido {resultado[i]}"
