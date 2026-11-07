# Limite do motor de sugestão com validação cruzada (07/11/2026)

## O que foi medido

O motor de sugestão só mostra uma skill quando a similaridade de cosseno passa de `SKILL_SUGGESTION_MIN_SCORE`. Esse limite é o único número do pipeline ajustado com dados. Por isso ele foi escolhido por validação cruzada, e não na mesma amostra em que é medido.

- **Perguntas do assunto:** 20, duas por área do catálogo. Para cada uma vale a nota da skill certa, que deve ficar acima do limite.
- **Perguntas fora do assunto:** 12 (receitas, viagens, animais...). Para cada uma vale a maior nota de qualquer skill, que deve ficar abaixo do limite.
- **Método:** k-fold estratificado com k=4 e semente fixa. Em cada rodada, o limite é escolhido em 3 partes, pela melhor acurácia balanceada, e medido na parte que ficou de fora ([`calibration.py`](../../../backend/app/rag/calibration.py)).
- **Modelo de embeddings:** `liquid/lfm-2.5-embedding-350m:free`, gratuito. Produção usa `openai/text-embedding-3-small`, que não foi usado nesta medição.

Comando: `pytest tests/test_skill_suggestion_quality.py -m llm -s`.

## Resultado

| Medida | Valor |
|---|---:|
| Recall@3 (a skill certa entre as 3 primeiras) | 1,000 |
| MRR | 0,908 |
| Nota da skill certa | 0,135 a 0,570 |
| Maior nota fora do assunto | 0,004 a 0,163 |
| Limites escolhidos nas 4 rodadas | 0,116 · 0,116 · 0,118 · 0,112 |
| Acurácia balanceada nas partes de fora | 1,00 · 1,00 · 1,00 · 0,83 |
| **Média fora da escolha** | **0,958** |

Os limites quase não mudam entre as rodadas, então a escolha é estável nesta amostra. A única rodada abaixo de 1,00 tem uma pergunta do assunto com nota menor que a da pergunta fora do assunto mais alta (0,135 contra 0,163).

## O que isso diz sobre o limite configurado

Com este modelo, o limite configurado (0,35) acerta só 5 das 20 perguntas do assunto: acurácia balanceada de 0,625. O limite certo para ele seria por volta de 0,12.

Isso não quer dizer que 0,35 está errado em produção. As notas de similaridade dependem do modelo, e o limite precisa ser calibrado com o modelo em uso. Falta rodar o mesmo teste com `openai/text-embedding-3-small`, que é pago, e ajustar `SKILL_SUGGESTION_MIN_SCORE` pelo resultado.

## Limites desta medição

- 32 perguntas é pouco. Com 3 perguntas fora do assunto por parte, uma pergunta muda a acurácia da parte em 0,17.
- As perguntas foram escritas pela equipe, sem repetir o nome das áreas, mas não vêm de uso real.
- As perguntas fora do assunto são bem distantes de tecnologia. Uma pergunta técnica de uma área que não está no catálogo, como contabilidade, não foi testada.
