# Recomendações de Acessibilidade para Jogo de Batalha Naval

## 1. Navegação por Teclado
- O tabuleiro deve ser totalmente acessível via teclado, usando `tab` para navegar entre as células.
- Implementar navegação com setas para mover um cursor sobre as células do tabuleiro do computador.
- Ações de atirar e reiniciar devem estar vinculadas a teclas de atalho (ex.: `Enter` para atirar, `R` para reiniciar).
- Foco visível deve ser claramente indicado com contorno de 2px e alto contraste.

## 2. Estados que Não Dependem Apenas de Cor
- **Acerto**: usar um ícone de "X" ou um caractere textual como "X" além de uma cor (ex.: verde). Para leitores de tela, anunciar "Acerto".
- **Erro**: usar um círculo ou um ponto de interrogação "?" e anunciar "Água" ou "Errou".
- **Navio afundado**: exibir o nome do navio afundado textualmente e anunciar "Navio [nome] afundado".
- **Vitória/Derrota**: mensagem textual clara, não apenas cor de fundo.

## 3. Contraste
- O tabuleiro e os elementos interativos devem ter contraste mínimo de 4.5:1 (WCAG AA).
- Células do tabuleiro: fundo azul claro (contraste com o texto branco).
- Células atingidas: fundo vermelho escuro com texto branco.
- Botões e links: contraste de pelo menos 3:1.

## 4. Textos para Leitor de Tela
- Cada célula do tabuleiro deve ter um `aria-label` descritivo, ex.: "Linha 3, Coluna 5, água".
- Ao clicar em uma célula, o foco deve mover para a célula e o leitor de tela deve anunciar o resultado.
- Mensagens de status devem ser colocadas em uma região `aria-live="polite"` para que sejam anunciadas sem interromper a navegação.

## 5. Mensagens de Status
- Todas as mudanças de estado devem ser announcedas via `aria-live`:
  - "Jogada realizada: acerto!"
  - "Jogada realizada: água!"
  - "Navio encouraçado afundado!"
  - "Você venceu! Jogo Reiniciado."
  - "Computador venceu. Jogo Reiniciado."
- O jogo deve parar de anunciar mensagens redundantes após a primeira ocorrência.

## 6. Verificabilidade
- Testar com navegação por teclado apenas, sem mouse, para garantir que todas as ações sejam possíveis.
- Usar leitores de tela (NVDA, VoiceOver) para verificar anúncios.
- Verificar contraste com ferramentas como WebAIM Contrast Checker.
- Validar que nenhuma informação crucial é transmitida apenas por cor.

## 7. Recomendações Adicionais
- Fornecer opção de pausar o jogo para leitores de tela que precisam de mais tempo.
- Permitir que o jogador desative animações (ex.: transição de cores) via preferência de redução de movimento.
