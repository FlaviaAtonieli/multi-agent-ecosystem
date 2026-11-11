# PLANO DE TESTES - Jogo Batalha Naval

## Objetivo
Validar a qualidade do jogo de batalha naval contra o computador, garantindo que todos os requisitos sejam atendidos e que a experiência do usuário seja consistente.

## Casos de Teste

### 1. Inicialização do Jogo
- **Caso 1.1**: Carregar index.html e verificar se o tabuleiro 10x10 é exibido corretamente para jogador e computador.
- **Passos**: Acessar o jogo, observar a interface.
- **Resultado Esperado**: Dois tabuleiros 10x10 visíveis, com coordenadas claras.

### 2. Posicionamento da Frota
- **Caso 2.1**: Verificar que todos os navios são posicionados aleatoriamente sem sobreposição.
- **Passos**: Reiniciar o jogo várias vezes e inspecionar a disposição dos navios.
- **Resultado Esperado**: Cada navio (porta-aviões 5, encouraçado 4, cruzador 3, submarino 3, destróier 2) está em posições válidas, sem sobreposição e dentro dos limites do tabuleiro.

### 3. Mecânicas de Jogo
- **Caso 3.1**: Jogador acerta um navio.
- **Passos**: Clicar em uma posição onde há um navio no tabuleiro do computador.
- **Resultado Esperado**: A casa é marcada como acerto, exibindo feedback visual e sonoro (se houver).

- **Caso 3.2**: Jogador erra um navio.
- **Passos**: Clicar em uma posição vazia no tabuleiro do computador.
- **Resultado Esperado**: A casa é marcada como erro, com feedback apropriado.

- **Caso 3.3**: Tiro repetido na mesma casa.
- **Passos**: Clicar duas vezes na mesma posição já atingida.
- **Resultado Esperado**: O jogo impete novos tiros na mesma casa, exibindo uma mensagem ou ignorando o clique.

### 4. Afundamento de Navios
- **Caso 4.1**: Afundar um navio de tamanho 2 (destróier).
- **Passos**: Acertar todas as partes do destróier.
- **Resultado Esperado**: O jogo anuncia "Navio afundado!" e marca o navio como destruído.

### 5. Fim de Jogo
- **Caso 5.1**: Vitória do jogador.
- **Passos**: Afundar todos os navios do computador.
- **Resultado Esperado**: Mensagem "Parabéns! Você venceu!" com opção de reiniciar.

- **Caso 5.2**: Derrota do jogador.
- **Passos**: Computador afunda todos os navios do jogador.
- **Resultado Esperado**: Mensagem "Você perdeu!" com opção de reiniciar.

### 6. Reinício do Jogo
- **Caso 6.1**: Reiniciar após vitória ou derrota.
- **Passos**: Clicar em "Reiniciar".
- **Resultado Esperado**: O jogo reinicia, gerando nova frota aleatória e resetando o estado do tabuleiro.

### 7. Casos de Borda
- **Caso 7.1**: Navios não saem do tabuleiro.
- **Passos**: Verificar que todos os navios estão contidos dentro do tabuleiro 10x10.
- **Resultado Esperado**: Nenhum navio ultrapassa os limites.

- **Caso 7.2**: Navios não se sobrepõem.
- **Passos**: Inspecionar multiple reinícios para garantir que não há sobreposição.
- **Resultado Esperado**: Sem sobreposição entre navios.

## Critérios de Aceitação
- O jogo deve ser responsivo e funcionar em navegadores modernos.
- Todas as interações devem fornecer feedback claro ao usuário.
- O código deve ser limpo, sem erros no console do navegador.