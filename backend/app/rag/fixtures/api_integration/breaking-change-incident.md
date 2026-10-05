# Incidente — Mudança não anunciada no serviço externo de score (2022)

> Registrado informalmente pelo time depois do incidente. Complementa
> `external-score-integration-notes.md` com um caso real de quebra de
> contrato sem versionamento.

## O que aconteceu

O serviço externo de score (`BureauScoreClient`, ver notas da integração)
mudou o campo `score` de inteiro (`score: 720`) para um objeto
(`score: {"valor": 720, "faixa": "BOM"}`) sem aviso prévio — sem changelog
público, sem e-mail de deprecação, sem versão nova de URL. A mudança
quebrou o parsing no `OrderApprovalController`, que esperava um número
simples.

## Como foi detectado

Não por alerta (ver lacuna de observabilidade,
`observability/logging-metrics-gaps.md`) — o código tinha um bloco de
tratamento de erro que, ao falhar o parsing, **silenciosamente tratava
como "sem score externo disponível"** e seguia a aprovação só com a regra
de limite interna. Ninguém percebeu por 3 dias, até um cliente de alto
risco ser aprovado sem o sinal externo que normalmente o teria bloqueado —
caso levantado manualmente pelo time de Risco ao revisar uma aprovação
específica.

## Causa raiz

Combinação de dois problemas, não um só:

1. Ausência de contrato versionado com o serviço externo (mudança
   silenciosa é possível porque nenhum dos dois lados tem um contrato
   formal a respeitar).
2. Tratamento de erro "generoso demais": falha de parsing virou
   "prosseguir sem o sinal" em vez de "bloquear e alertar" — uma decisão
   de design que faz sentido para disponibilidade, mas esconde quebras de
   integração em vez de torná-las visíveis.

## Recomendação registrada (não implementada)

Validar o formato da resposta externa contra um schema explícito antes de
usar o valor; quando a validação falhar, emitir um alerta (não só seguir
em frente silenciosamente) — a aprovação pode continuar sem o score
externo por disponibilidade, mas alguém precisa saber que isso está
acontecendo.
