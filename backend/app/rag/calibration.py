"""Calibração do limite de similaridade do motor de sugestão, com validação cruzada.

Cada pergunta do assunto dá a nota da skill certa (deve ficar acima do limite), e
cada pergunta fora do assunto dá a maior nota de qualquer skill (deve ficar abaixo).
O limite é escolhido numa parte das perguntas e medido na parte que ficou de fora,
para a nota medida não ser a mesma usada para escolher.
"""

import random
from dataclasses import dataclass


def balanced_accuracy(positives: list[float], negatives: list[float], threshold: float) -> float:
    """Média entre os acertos de cada grupo, para o grupo maior não dominar a nota."""
    hits = sum(score >= threshold for score in positives) / len(positives)
    rejections = sum(score < threshold for score in negatives) / len(negatives)
    return (hits + rejections) / 2


def best_threshold(positives: list[float], negatives: list[float]) -> float:
    """O limite com a melhor acurácia balanceada entre os pontos médios das notas.

    No empate, fica o do meio da faixa empatada, que deixa a maior margem dos dois lados.
    """
    scores = sorted(set(positives) | set(negatives))
    candidates = [(low + high) / 2 for low, high in zip(scores, scores[1:], strict=False)] or scores
    accuracies = [balanced_accuracy(positives, negatives, t) for t in candidates]
    best = max(accuracies)
    tied = [t for t, accuracy in zip(candidates, accuracies, strict=True) if accuracy == best]
    return tied[len(tied) // 2]


@dataclass(frozen=True)
class CrossValidation:
    thresholds: list[float]
    held_out_accuracies: list[float]

    @property
    def mean_accuracy(self) -> float:
        return sum(self.held_out_accuracies) / len(self.held_out_accuracies)


def _folds(values: list[float], k: int, rng: random.Random) -> list[list[float]]:
    shuffled = values[:]
    rng.shuffle(shuffled)
    return [shuffled[i::k] for i in range(k)]


def cross_validate_threshold(
    positives: list[float], negatives: list[float], *, k: int = 4, seed: int = 42
) -> CrossValidation:
    """k-fold estratificado: cada parte mantém a proporção de perguntas dentro e fora
    do assunto. A semente fixa faz a divisão sair igual em toda execução."""
    if min(len(positives), len(negatives)) < k:
        raise ValueError(f"Cada grupo precisa de pelo menos {k} notas para {k} partes.")
    rng = random.Random(seed)
    positive_folds, negative_folds = _folds(positives, k, rng), _folds(negatives, k, rng)
    thresholds, accuracies = [], []
    for held in range(k):
        train_pos = [s for i, fold in enumerate(positive_folds) if i != held for s in fold]
        train_neg = [s for i, fold in enumerate(negative_folds) if i != held for s in fold]
        threshold = best_threshold(train_pos, train_neg)
        thresholds.append(threshold)
        accuracies.append(balanced_accuracy(positive_folds[held], negative_folds[held], threshold))
    return CrossValidation(thresholds=thresholds, held_out_accuracies=accuracies)
