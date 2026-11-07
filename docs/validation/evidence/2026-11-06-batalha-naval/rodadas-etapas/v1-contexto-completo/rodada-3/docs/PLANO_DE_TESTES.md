# Plano de Testes - Jogo Batalha Naval

## Objetivo
Validar a qualidade do jogo de batalha naval sob a perspectiva de jogabilidade, usabilidade e robustesa, garantindo que todos os requisitos sejam atendidos e que a experiência do usuário seja consistente.

## Casos de Teste

### 1. Configuração Inicial
**Caso 1.1: Inicialização do Jogo**
- Passo: Abrir index.html em navegador compatível.
- Resultado Esperado: Tabuleiros 10x10 exibidos, frota posicionada aleatoriamente sem sobreposição, interface limpa.

**Caso 1.2: Posicionamento Aleatório**
- Passo: Reiniciar o jogo 10 vezes.
- Resultado Esperado: Em cada iteração, todos os navios devem estar posicionados sem sobreposição e dentro dos limites do tabuleiro.

### 2. Mecânicas de Jogabilidade
**Caso 2.1: Tiro com Acerto**
- Passo: Clicar em uma casa que contém um navio no tabuleiro do computador.
- Resultado Esperado: A casa marcada como acerto, exibindo feedback visual e sonoro (se houver).

**Caso 2.2: Tiro com Erro**
- Passo: Clicar em uma casa vazia no tabuleiro do computador.
- Resultado Esperado: A casa marcada como erro, exibindo feedback visual distinto do acerto.

**Caso 2.3: Tiro Repetido**
- Passo: Clicar em uma casa já atingida.
- Resultado Esperado: Nenhuma ação adicional, feedback indicando que a casa já foi atacada.

**Caso 2.4: Afundamento de Navio**
- Passo: Acertar todas as partes de um navio (ex: destróier de tamanho 2).
- Resultado Esperado: Navio marcado como afundado, feedback visual de destruição.

### 3. Interação com o Computador
**Caso 3.1: Ataque Computador**
- Passo: Após o jogador atacar, verificar o contra-ataque do computador.
- Resultado Esperado: O computador deve atacar uma casa aleatória não atingida no tabuleiro do jogador.

**Caso 3.2: Acerto do Computador**
- Passo: O computador acerta uma casa com navio.
- Resultado Esperado: Feedback de acerto no tabuleiro do jogador.

**Caso 3.3: Erro do Computador**
- Passo: O computador ataca uma casa vazia.
- Resultado Esperado: Feedback de erro no tabuleiro do jogador.

### 4. Fim de Jogo
**Caso 4.1: Vitória por Eliminação**
- Passo: Afundar todos os navios do computador.
- Resultado Esperado: Anúncio de vitória, opção de reiniciar habilitada.

**Caso 4.2: Derrota por Eliminação**
- Passo: Computador afunda todos os navios do jogador.
- Resultado Esperado: Anúncio de derrota, opção de reiniciar habilitada.

**Caso 4.3: Empate por Limite de Turnos**
- Passo: Jogo sem vitória após X turnos (se houver limite).
- Resultado Esperado: Anúncio de empate, opção de reiniciar.

### 5. Reinício
**Caso 5.1: Reinício com Estado Limpo**
- Passo: Clicar em "Reiniciar" após o fim do jogo.
- Resultado Esperado: Novo tabuleiro gerado, placar reiniciado, jogo recomeça.

### 6. Casos de Borda
**Caso 6.1: Navios sem Sobreposição**
- Passo: Verificar posicionamento inicial em múltiplos reinícios.
- Resultado Esperado: Nenhum navio sobreposto, todos dentro dos limites.

**Caso 6.2: Navios sem Saída do Tabuleiro**
- Passo: Validar que todos os navios estão contidos no tabuleiro 10x10.
- Resultado Esperado: Nenhuma parte do navio excede os limites.

**Caso 6.3: Tiro na Mesma Casa**
- Passo: Repetir tiros na mesma casa já atingida.
- Resultado Esperado: Nenhuma alteração de estado, feedback consistente.

**Caso 6.4: Fim de Jogo com Reinício**
- Passo: Reiniciar imediatamente após vitória/derrota.
- Resultado Esperado: Jogo reinicia sem erros, novo estado aleatório.

## Critérios de Aceitação
- Todos os casos de teste devem passar sem falhas.
- Interface deve ser responsiva e acessível.
- Desempenho deve ser estável, sem atrasos ou travamentos.
- Feedback visual/sonoro deve ser claro e consistente.