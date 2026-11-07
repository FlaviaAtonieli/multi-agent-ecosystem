# PLANO DE TESTES - Jogo de Batalha Naval

## Objetivo
Validar a qualidade e o correto funcionamento do jogo de Batalha Naval, garantindo que todos os requisitos sejam atendidos e que casos de borda sejam tratados.

## Escopo
Testes focados em: inicialização do tabuleiro, posicionamento de navios, mecânica de tiros, vitória/derrota, e reinício.

## Casos de Teste

### TC01: Inicialização dos Tabuleiros
- **Passos:** 1. Abrir o index.html. 2. Verificar se os tabuleiros do jogador e do computador são gerados com 10x10 casas.
- **Resultado Esperado:** Dois tabuleiros de 10x10 exibidos, identificados como "Jogador" e "Computador".

### TC02: Posicionamento Aleatório dos Navios
- **Passos:** 1. Recarregar a página. 2. Verificar se os navios estão posicionados sem sobreposição e dentro dos limites.
- **Resultado Esperado:** Cada navio (porta-aviões 5, encouraçado 4, cruzador 3, submarino 3, destróier 2) está em posições válidas, sem sobreposição e totalmente dentro do tabuleiro.

### TC03: Tiro do Jogador - Acerto
- **Passos:** 1. Clicar em uma casa que contém um navio no tabuleiro do computador.
- **Resultado Esperado:** A casa marcada como acerto, exibindo feedback visual e textual "Acerto!".

### TC04: Tiro do Jogador - Erro
- **Passos:** 1. Clicar em uma casa vazia no tabuleiro do computador.
- **Resultado Esperado:** A casa marcada como erro, exibindo feedback visual e textual "Errou!".

### TC05: Tiro Repetido na Mesma Casa (Borda)
- **Passos:** 1. Clicar em uma casa já atingida anteriormente.
- **Resultado Esperado:** O clique é ignorado ou exibe mensagem de "Casa já atingida", sem alterar o estado do jogo.

### TC06: Tiro do Computador - Aleatório e sem Repetição
- **Passos:** 1. Jogar até o computador efetuar vários tiros. 2. Verificar se os tiros não repetem casas já atingidas.
- **Resultado Esperado:** Cada tiro do computador é em uma casa não visitada anteriormente no tabuleiro do jogador.

### TC07: Afundamento de Navio
- **Passos:** 1. Acertar todas as casas de um navio específico (ex.: destróier de 2 casas).
- **Resultado Esperado:** Ao acertar a última casa, o jogo exibe "Navio afundado!" e marca o navio como destruído.

### TC08: Fim de Jogo - Vitória
- **Passos:** 1. Simular ou jogar até afundar todos os navios do computador.
- **Resultado Esperado:** O jogo exibe "Vitória!" e mostra opção de reiniciar.

### TC09: Fim de Jogo - Derrota
- **Passos:** 1. Simular ou jogar até todos os navios do jogador serem afundados.
- **Resultado Esperado:** O jogo exibe "Derrota!" e mostra opção de reiniciar.

### TC10: Reinício do Jogo
- **Passos:** 1. Clicar em "Reiniciar" após o fim do jogo. 2. Verificar se os tabuleiros são resetados e novos navios são posicionados.
- **Resultado Esperado:** O jogo recomeça com tabuleiros vazios, novos posicionamentos aleatórios e placar reiniciado.

### TC11: Verificação de Navios sem Sobreposição e sem Saída do Tabuleiro (Borda)
- **Passos:** 1. Executar múltiplas partidas. 2. Usar console ou inspeção para confirmar que nenhum navio ultrapassou os limites do tabuleiro ou sobrepos outro.
- **Resultado Esperado:** Em todas as partidas, os navios estão totalmente contidos no tabuleiro e sem sobreposição.

## Critérios de Aceitação
- Todos os casos de teste devem passar sem falhas.
- A interface deve estar responsiva e clara.
- Mensagens de feedback devem ser exibidas corretamente.

## Aprovação Necessária
Este plano de testes deve ser aprovado pela equipe de qualidade antes da execução dos testes.