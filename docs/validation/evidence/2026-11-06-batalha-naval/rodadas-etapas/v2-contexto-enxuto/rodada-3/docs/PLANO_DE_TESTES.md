# PLANO DE TESTES - Batalha Naval

## 1. Casos de Teste

### TC-01: Inicialização do jogo
- **Passos:** 1. Carregar index.html. 2. Verificar se o tabuleiro 10x10 está desenhado para jogador e computador.
- **Resultado Esperado:** Ambos os tabuleiros exibidos, botão "Iniciar" ou similar disponível.

### TC-02: Posicionamento aleatório das naves
- **Passos:** 1. Iniciar jogo. 2. Verificar que cada navio está posicionado sem sobreposição e dentro dos limites.
- **Resultado Esperado:** Cada navio ocupa células distintas, todas as células dentro do range 0‑9.

### TC-03: Ataque do jogador em célula vazia
- **Passos:** 1. Clicar em uma célula do tabuleiro do computador que não contém navio.
- **Resultado Esperado:** A célula marcada como "Água", tabuleiro do computador atualizado.

### TC-04: Ataque do jogador em célula com navio
- **Passos:** 1. Clicar em uma célula que contém parte de um navio.
- **Resultado Esperado:** A célula marcada como "Acerto", e se o navio for afundado, exibir mensagem de "Navio afundado".

### TC-05: Ataque repetido na mesma célula
- **Passos:** 1. Clicar em uma célula já atacada. 2. Tentar clicar novamente.
- **Resultado Esperado:** Nenhuma ação adicional, mensagem de "Célula já atacada".

### TC-06: Ataque do computador
- **Passos:** 1. Após ataque do jogador, verificar que o computador escolhe uma célula não atacada no tabuleiro do jogador.
- **Resultado Esperado:** Célula marcada como "Acerto" ou "Água" de acordo com a presença de navio.

### TC-07: Afundamento de todos os navios
- **Passos:** 1. Simular ataques até que todos os navios do computador sejam afundados.
- **Resultado Esperado:** Mensagem "Vitória!" exibida, botão "Reiniciar" disponível.

### TC-08: Derrota do jogador
- **Passos:** 1. Simular ataques do computador até afundar todos os navios do jogador.
- **Resultado Esperado:** Mensagem "Derrota!" exibida, botão "Reiniciar" disponível.

### TC-09: Reinício do jogo
- **Passos:** 1. Clicar em "Reiniciar" após vitória ou derrota.
- **Resultado Esperado:** Tabuleiros limpos, novas posições aleatórias de navios, placar reiniciado.

### TC-10: Casos de borda - Navio fora do tabuleiro
- **Passos:** 1. Verificar que a função de posicionamento não permite coordenadas negativas ou maiores que 9.
- **Resultado Esperado:** Nenhum navio posicionado fora dos limites.

### TC-11: Casos de borda - Sobreposição de navios
- **Passos:** 1. Executar posicionamento múltiplas vezes e verificar que não há sobreposição.
- **Resultado Esperado:** Nenhuma célula contém mais de um navio.

### TC-12: Casos de borda - Ataque em célula já atingida pelo computador
- **Passos:** 1. Forçar que o computador tente atacar uma célula já atacada.
- **Resultado Esperado:** O computador escolhe outra célula não atacada.

## 2. Critérios de Aceitação
- O jogo deve funcionar em navegadores modernos sem dependências externas.
- A interface deve ser responsiva e acessível.
- Todas as regras de batalha naval devem ser aplicadas corretamente.
- O código deve estar livre de erros de sintaxe e de lógica.

## 3. Aprovação Humana
- Requer aprovação do revisor antes da implementação.

