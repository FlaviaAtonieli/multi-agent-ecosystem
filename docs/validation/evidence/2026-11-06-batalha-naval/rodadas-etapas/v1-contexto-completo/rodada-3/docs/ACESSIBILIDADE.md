# Plano de Acessibilidade e UX para Jogo de Batalha Naval

Este documento define as diretrizes de acessibilidade e experiência do usuário (UX) para o jogo de Batalha Naval, garantindo que ele seja jogável por usuários com deficiências visuais, motoras e de attention deficit, além de oferecer uma experiência de alta qualidade para todos.

## 1. Diretrizes de Navegação por Teclado (Teclado Acessível)

O jogo deve ser totalmente jogável usando apenas o teclado, sem depender do mouse.

- **Navegação no Tabuleiro:**
  - O foco deve alternar entre as células do tabuleiro do computador usando as teclas de direção (Setas) ou a tecla `Tab` para ciclar entre as células ativas.
  - Para cada célula, a tecla `Enter` ou `Espaço` deve disparar o tiro.
- **Controles Gerais:**
  - O botão "Reiniciar Jogo" deve estar acessível via `Tab` e ativado com `Enter` ou `Espaço`.
  - O menu de instruções ou ajuda (se houver) deve ser facilmente acessível e fechável com a tecla `Esc`.

## 2. Feedback Não Visual e Estados Não Dependentes de Cores

Não use apenas cores para diferenciar acertos, erros e navios afundados.

- **Acerto (Hit):**
  - besides a cor (ex: verde), use um ícone de acerto (ex: ✔ ou um diamante) e um texto oculto para leitor de tela como "Acerto!".
- **Erro (Miss):**
  - Além da cor (ex: vermelho), use um ícone de água/erro (ex: ✖ ou um círculo com X) e o texto oculto "Água!".
- **Navio Afundado (Sunk):**
  - Use um ícone de navio afundado (ex: ⚓ ou um símbolo de submersor) e anuncie via leitor de tela: "Navio [Nome] afundado!".
- **Tabuleiro do Jogador:**
  - O tabuleiro do jogador deve indicar visualmente os locais onde ele foi atingido (ex: ícone de explosão) e onde colocou seus navios (ex: ícone de navio), com textos alternativos correspondentes.

## 3. Contraste e Estética Visual

- **Contraste de Cores:**
  - O contraste entre o texto e o fundo deve ser de pelo menos **4.5:1** (ex: texto branco em fundo azul escuro).
  - Os indicadores de acerto, erro e navios no tabuleiro devem ter um contraste de pelo menos **3:1** contra o fundo da célula para que usuários com baixa visão consigam distinguir os estados.
- **Foco Visível (Focus Indicator):**
  - O contorno de foco para as células do tabuleiro e botões deve ser visível e ter uma largura mínima de 2px, com cor de alto contraste.

## 4. Textos Alternativos e Leitores de Tela (Screen Readers)

- **Células do Tabuleiro:**
  - Cada célula deve ter um `aria-label` descritivo. Exemplo: `aria-label="Linha 3, Coluna D, água, ainda não atingida"` ou `aria-label="Linha 5, Coluna B, acerto!"`.
- **Regiões de Anúncio (Live Regions):**
  - Utilize um elemento com `aria-live="polite"` para anunciar mudanças de estado sem interromper o fluxo do usuário.
  - Exemplos de anúncios:
    - "Sua vez. Digite a coordenada para atirar."
    - "Computador atingiu a linha 2, coluna F."
    - "Parabéns! Você afundou todos os navios e venceu o jogo!"
    - "Fim de jogo. O computador venceu. Clique em Reiniciar para jogar novamente."

## 5. Mensagens de Status e Feedback de Ação

- **Ação de Tiro:**
  - Ao realizar um tiro, força uma atualização imediata na região `aria-live` informando o resultado (acerto, erro ou afundamento).
- **Anúncio de Vitória/Derrota:**
  - O anúncio final deve ser claro, conciso e destacado visualmente (ex: um modal com botão de fechar e reiniciar, focado automaticamente para leitores de tela e navegação por teclado).

## 6. Testes de Verificação (Checklist)

- [ ] O jogo é jogável 100% via teclado (Tab, Setas, Enter, Espaço).
- [ ] Os estados de acerto, erro e afundamento são distinguíveis apenas por forma/texto, sem depender exclusivamente de cor.
- [ ] Todas as células interativas e imagens possuem textos alternativos (`alt` ou `aria-label`).
- [ ] As mensagens de mudança de vez e resultado de tiro são announceadas por leitores de tela (usando `aria-live`).
- [ ] O contraste de cores atende aos padrões WCAG 2.1 AA.
- [ ] O foco do teclado é visível em todos os elementos interativos.