# PLANO DE TESTES – BATALHA NAVAL (TRC-20261107-7FD42D)

## 1. Objetivo
Validar a qualidade e a jogabilidade do jogo de Batalha Naval contra o computador, garantindo que todos os requisitos sejam atendidos e que o fluxo de jogo funcione corretamente.

## 2. Escopo
- Tabuleiro 10×10 para jogador e computador.
- Frota: porta-aviões (5), encouraçado (4), cruzador (3), submarino (3), destróier (2).
- Posicionamento aleatório sem sobreposição e dentro dos limites.
- Jogador atira por clique; computador responde com tiro aleatório em casa não atingida.
- Feedback de acerto, erro, afundamento e vitória/derrota.
- Opção de reiniciar.

## 3. Requisitos Funcionais
1. Gerar tabuleiro 10×10 para cada lado.
2. Posicionar navios aleatoriamente sem sobreposição.
3. Permitir ao jogador selecionar casa no tabuleiro do computador.
4. Verificar acerto/erro e atualizar estado da casa.
5. Detectar afundamento de navio.
6. Computador realizationa tiro aleatório em casa não atingida.
7. Verificar condição de vitória/derrota.
8. Oferecer botão de reiniciar.

## 4. Requisitos Não Funcionais
- Jogabilidade fluida em navegadores modernos.
- Interface clara e intuitiva.
- Tempo de resposta do computador < 100ms.

## 5. Arquitetura
- index.html: estrutura básica.
- style.css: estilização dos tabuleiros e componentes.
- game.js: lógica de jogo, estado, posicionamento, ataques.

## 6. Fluxo de Jogo
1. Inicialização: gerar frotas aleatórias.
2. Turno do jogador: clique na casa → processar ataque.
3. Atualizar visualmente acerto/erro/afundamento.
4. Verificar vitória.
5. Turno do computador: escolher casa aleatoriamente não atingida.
6. Atualizar tabuleiro do jogador.
7. Verificar derrota.
8. Repetir até vitória/derrota.
9. Exibir resultado e opção de reiniciar.

## 7. Regras de Negócio
- Navios não podem se sobrepor.
- Navios devem estar totalmente dentro do tabuleiro.
- Tiro repetido na mesma casa deve ser ignorado ou exibir mensagem.
- Computador não atira em casa já atingida.

## 8. Plano de Testes

### 8.1 Casos de Teste Funcionais
**TC01: Inicialização do jogo**
- Passos: Abrir index.html.
- Esperado: Dois tabuleiros 10×10 exibidos, frotas posicionadas aleatoriamente.

**TC02: Ataque do jogador em casa vazia**
- Passos: Clicar em uma casa sem navio.
- Esperado: Casa marcada como "erro", cor visual adequada.

**TC03: Ataque do jogador em casa com navio**
- Passos: Clicar em uma casa que contém um navio.
- Esperado: Casa marcada como "acerto", navio atualizado.

**TC04: Ataque que afunda um navio**
- Passos: Atacar todas as casas de um navio de tamanho N.
- Esperado: Último acerto exibe mensagem de afundamento.

**TC05: Ataque do computador**
- Passos: Após ataque do jogador, aguardar ataque automático.
- Esperado: Casa no tabuleiro do jogador é marcada como acerto/erro.

**TC06: Vitória do jogador**
- Passos: Afundar todos os navios do computador.
- Esperado: Mensagem de vitória exibida, botão de reiniciar visível.

**TC07: Derrota do jogador**
- Passos: Computador afunda todos os navios do jogador.
- Esperado: Mensagem de derrota exibida, botão de reiniciar visível.

**TC08: Reiniciar jogo**
- Passos: Clicar em "Reiniciar".
- Esperado: Novo jogo iniciado, tabuleiros limpos e novas frotas geradas.

### 8.2 Casos de Teste de Borda
**TC09: Tiro repetido na mesma casa**
- Passos: Clicar duas vezes na mesma casa do tabuleiro do computador.
- Esperado: Segundo clique é ignorado ou exibe "Já atacou esta casa".

**TC10: Navio não se sobrepõe**
- Passos: Verificar posicionamento aleatório por múltiplas inicializações.
- Esperado: Nenhum navio sobreposto.

**TC11: Navio não sai do tabuleiro**
- Passos: Verificar que todas as casas dos navios estão dentro do limite 10×10.
- Esperado: Nenhuma parte do navio ultrapassa o tabuleiro.

**TC12: Ataque do computador em casa já atingida**
- Passos: Forçar computador a atacar mesma casa (simular).
- Esperado: Computador escolhe outra casa não atingida.

### 8.3 Casos de Teste de Fim de Jogo
**TC13: Fim de jogo por vitória**
- Passos: Simular afundamento de todos os navios inimigos.
- Esperado: Jogo termina com vitória.

**TC14: Fim de jogo por derrota**
- Passos: Simular afundamento de todos os navios do jogador.
- Esperado: Jogo termina com derrota.

### 8.4 Casos de Teste de Reinício
**TC15: Reinício após vitória**
- Passos: Vencer jogo, clicar em reiniciar.
- Esperado: Estado resetado, novo jogo.

**TC16: Reinício após derrota**
- Passos: Perder jogo, clicar em reiniciar.
- Esperado: Estado resetado, novo jogo.

## 9. Critérios de Aceitação
- Todos os casos de teste devem passar sem erros.
- Interface deve estar consistente em todos os estados.
- Nenhum navio deve ser posicionado incorretamente.
- O jogo deve ser responsivo e sem atrasos perceptíveis.

---
*Plano elaborado sob domínio qualidade_jogos, com foco em cobertura de casos de borda e fluxo completo de jogo.*