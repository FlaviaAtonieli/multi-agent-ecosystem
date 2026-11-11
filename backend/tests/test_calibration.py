import pytest

from app.rag.calibration import balanced_accuracy, best_threshold, cross_validate_threshold


def test_acuracia_balanceada_pesa_os_dois_grupos_igual() -> None:
    # 3 de 4 do assunto acima do limite e 1 de 2 fora do assunto abaixo.
    assert balanced_accuracy([0.9, 0.8, 0.7, 0.2], [0.3, 0.6], 0.5) == pytest.approx((0.75 + 0.5) / 2)


def test_limite_separa_grupos_que_nao_se_misturam() -> None:
    threshold = best_threshold([0.6, 0.7, 0.8], [0.1, 0.2, 0.3])

    assert 0.3 < threshold < 0.6
    assert balanced_accuracy([0.6, 0.7, 0.8], [0.1, 0.2, 0.3], threshold) == 1.0


def test_no_empate_fica_o_limite_do_meio() -> None:
    # Qualquer ponto entre 0.3 e 0.6 separa tudo; o do meio é o ponto médio 0.45.
    assert best_threshold([0.6, 0.7], [0.2, 0.3]) == pytest.approx(0.45)


def test_validacao_cruzada_mede_em_partes_que_nao_escolheram_o_limite() -> None:
    positives = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]
    negatives = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.58]

    result = cross_validate_threshold(positives, negatives, k=4)

    assert len(result.thresholds) == 4
    assert len(result.held_out_accuracies) == 4
    # O 0.58 fora do assunto fica no meio das notas do assunto: nenhum limite acerta tudo.
    assert 0.5 < result.mean_accuracy < 1.0


def test_validacao_cruzada_sai_igual_com_a_mesma_semente() -> None:
    positives = [0.4, 0.5, 0.6, 0.7, 0.45, 0.55]
    negatives = [0.1, 0.2, 0.3, 0.42, 0.25, 0.35]

    first = cross_validate_threshold(positives, negatives, k=3)
    second = cross_validate_threshold(positives, negatives, k=3)

    assert first == second


def test_validacao_cruzada_exige_notas_suficientes() -> None:
    with pytest.raises(ValueError, match="pelo menos 4"):
        cross_validate_threshold([0.5, 0.6, 0.7, 0.8], [0.1, 0.2], k=4)
