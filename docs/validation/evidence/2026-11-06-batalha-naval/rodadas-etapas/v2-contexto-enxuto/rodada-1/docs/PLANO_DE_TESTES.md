# PLANO DE TESTES - Jogo de Batalha Naval

## Objetivo
Validar a qualidade e o correto funcionamento do jogo de batalha naval contra o computador, cobrindo fluxos principais, casos de borda e critérios de aceitação.

## Casos de Teste

### CT-01: Inicialização do jogo
- **Passos**: 1. Abrir index.html. 2. Verificar se o tabuleiro 10x10 é exibido para o jogador e para o computador.
- **Resultado Esperado**: Dois tabuleiros com 100 casas cada, identificados claramente.

### CT-02: Posicionamento aleatório das frotas
- **Passos**: 1. Recarregar a página. 2. Observar a posição dos navios no tabuleiro do jogador (ocultos) e no computador (também ocultos).
- **Resultado Esperado**: A frota (porta-aviões 5, encouraçado 4, cruzador 3, submarino 3, destróier 2) é posicionada aleatoriamente, sem sobreposição, totalmente dentro do tabuleiro.

### CT-03: Navios não se sobrepõem
- **Passos**: 1. Executar múltiplos recarregamentos. 2. Verificar que nenhuma casa é ocupada por mais de um navio.
- **Resultado Esperado**: Sem sobreposição em todos os posicionamentos.

### CT-04: Navios dentro dos limites do tabuleiro
- **Passos**: 1. Verificar que todos os navios estão contidos nas coordenadas 0-9 para linha e coluna.
- **Resultado Esperado**: Nenhum navio ultrapassa o tabuleiro.

### CT-05: Jogador acerta tiro
- **Passos**: 1. Clicar em uma casa que contém um navio no tabuleiro do computador.
- **Resultado Esperado**: A casa é marcada como acerto (ex: cor differente, índice de acerto).

### CT-06: Jogador erra tiro
- **Passos**: 1. Clicar em uma casa vazia no tabuleiro do computador.
- **Resultado Esperado**: A casa é marcada como erro (ex: cor de fundo, índice de erro).

### CT-07: Computador acerta tiro
- **Passos**: 1. Jogar até o computador disparar. 2. Verificar que o tiro do computador atinge uma casa com navio.
- **Resultado Esperado**: A casa correspondente no tabuleiro do jogador é marcada como acerto.

### CT-08: Computador erra tiro
- **Passos**: 1. Jogar até o computador disparar. 2. Verificar que o tiro atinge uma casa vazia.
- **Resultado Esperado**: A casa é marcada como erro.

### CT-09: Navio afundado
- **Passos**: 1. Acertar todas as partes de um navio. 2. Verificar a mensagem ou marcação de afundamento.
- **Resultado Esperado**: O navio é marcado como afundado e a mensagem é exibida.

### CT-10: Tiro repetido na mesma casa
- **Passos**: 1. Clicar duas vezes na mesma casa do tabuleiro do computador.
- **Resultado Esperado**: O segundo clique é ignorado ou exibe a mesma informação do primeiro (sem alteração de estado).

### CT-11: Vitória do jogador
- **Passos**: 1. Acertar todos os navios do computador. 2. Verificar a mensagem de vitória.
- **Resultado Esperado**: Mensagem "Você venceu!" com opção de reiniciar.

### CT-12: Derrota do jogador
- **Passos**: 1. Deixar o computador afundar todos os navios do jogador. 2. Verificar a mensagem de derrota.
- **Resultado Esperado**: Mensagem "Você perdeu!" com opção de reiniciar.

### CT-13: Reinício do jogo
- **Passos**: 1. Clicar em "Reiniciar" após o fim da partida. 2. Verificar se o tabuleiro é resetado e uma nova frota é posicionada.
- **Resultado Esperado**: Novo jogo iniciado com nova configuração aleatória.

### CT-14: Caso de borda - Tabuleiro vazio (sem navios)
- **Passos**: 1. Simular configuração sem navios (se possível). 2. Jogar até o fim.
- **Resultado Esperado**: O jogo termina imediatamente com vitória do jogador (ou tratamento adequado).

### CT-15: Caso de borda - Tiro fora do tabuleiro
- **Passos**: 1. Tentar disparar para coordenadas inválidas (se a interface permitir).
- **Resultado Esperado**: O tiro é rejeitado ou ignorado.

## Critérios de Aceitação
- Todos os casos de teste devem passar sem erros.
- A interface deve estar responsiva e visualmente consistente.
- O jogo deve funcionar em navegadores modernos (Chrome, Firefox, Edge) sem dependências.

**Aprovação Humana Obrigatória**: Este plano de testes deve ser revisado e aprovado antes da implementação.
