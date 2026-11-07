# Plano de Testes para Jogo de Batalha Naval

## Objetivo
Validar a qualidade do jogo de batalha naval, garantindo que todas as regras, feedbacks e estados do jogo sejam corretamente implementados.

## Casos de Teste

### CT01: Posicionamento dos Navios sem Sobreposição
**Passos:**
1. Inicializar o jogo.
2. Verificar a posição de cada navio no tabuleiro do jogador e do computador.
**Resultado Esperado:**
- Nenhum navio deve sobrepor outro.
- Cada navio deve estar inteiramente dentro do tabuleiro.

### CT02: Navios Dentro do Tabuleiro
**Passos:**
1. Inicializar o jogo.
2. Verificar as coordenadas de cada navio.
**Resultado Esperado:**
- Todas as casas dos navios devem estar entre (0,0) e (9,9).

### CT03: Tiro Repetido na Mesma Casa
**Passos:**
1. Escolher uma casa no tabuleiro do computador e atirar.
2. Atirar novamente na mesma casa.
**Resultado Esperado:**
- O segundo tiro deve ser ignorado ou exibir uma mensagem de que a casa já foi atingida.

### CT04: Acerto de Tiro
**Passos:**
1. Escolher uma casa que contém um navio no tabuleiro do computador e atirar.
**Resultado Esperado:**
- A casa deve ser marcada como acerto.
- O jogo deve exibir uma mensagem de acerto.

### CT05: Erro de Tiro
**Passos:**
1. Escolher uma casa vazia no tabuleiro do computador e atirar.
**Resultado Esperado:**
- A casa deve ser marcada como erro.
- O jogo deve exibir uma mensagem de erro.

### CT06: Afundamento de Navio
**Passos:**
1. Atirar em todas as casas de um navio específico.
**Resultado Esperado:**
- Quando o último acerto for feito, o jogo deve anunciar que o navio foi afundado.

### CT07: Vitória por Afundar Todos os Navios Inimigos
**Passos:**
1. Afundar todos os navios do computador.
**Resultado Esperado:**
- O jogo deve exibir uma mensagem de vitória e oferecer a opção de reiniciar.

### CT08: Derrota por Afundar Todos os Navios do Jogador
**Passos:**
1. Deixar o computador afundar todos os navios do jogador.
**Resultado Esperado:**
- O jogo deve exibir uma mensagem de derrota e oferecer a opção de reiniciar.

### CT09: Reinício do Jogo
**Passos:**
1. Após o fim do jogo, clicar em reiniciar.
**Resultado Esperado:**
- O tabuleiro deve ser limpo.
- Os navios devem ser posicionados aleatoriamente novamente.
- O jogo deve recomeçar.

### CT10: Caso de Borda - Tiro na Mesma Casa (Repetição)
**Passos:**
1. Atirar em uma casa.
2. Atirar novamente na mesma casa.
3. Verificar a mensagem de feedback.
**Resultado Esperado:**
- O jogo deve impedir que o tiro seja repetido ou exibir uma mensagem de alerta.

### CT11: Caso de Borda - Navios sem Sobreposição e Dentro do Tabuleiro
**Passos:**
1. Inicializar o jogo múltiplas vezes.
2. Verificar que em nenhuma iteração há sobreposição ou navios fora do tabuleiro.
**Resultado Esperado:**
- O posicionamento deve ser sempre válido.

## Conclusão
Este plano de testes cobre os aspectos principais do jogo, incluindo posicionamento, tiros, afundamento, fim de jogo e reinício, além de casos de borda para garantir a robustez da implementação.
