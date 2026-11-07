# ACESSIBILIDADE – Batalha Naval

## 1. Navegação por teclado
- Todos os controles devem ser acessíveis via teclado (Tab, Enter, Espaço, Setas).
- Ordem de foco: tabuleiro do jogador → tabuleiro do computador → botão reiniciar.
- Indicador de foco visível (contorno de 2px, contraste mínimo 4.5:1).
- Atalhos: `R` para reiniciar, `Enter` em uma célula para atir.

## 2. Estados que não dependem apenas de cor
- **Acerto**: ícone ✖ + texto "Acerto" + som (opcional).
- **Erro**: ícone ❖ + texto "Erro" + padrão de ponto intercalado.
- **Afundado**: ícone ⚓ + texto "Navio afundado" + animação de desaparecimento.
- Nunca usar apenas cor (ex.: verde para acerto, vermelho para erro).

## 3. Contraste de cores
- Fundo das células: claro (#ffffff) ou escuro (#1a1a1a).
- Texto sobre fundo claro: contraste mínimo 4.5:1 (ex.: #000000).
- Texto sobre fundo escuro: contraste mínimo 4.5:1 (ex.: #ffffff).
- Indicadores de estado (ícones) devem ter contraste de pelo menos 3:1 com o fundo.

## 4. Textos para leitor de tela
- Cada célula do tabuleiro deve ter `aria-label` descritivo (ex.: "Célula A1, água").
- Ao acertar: "Acerto em A1".
- Ao errar: "Erro em B2".
- Ao afundar navio: "Navio destróier afundado".
- Botão reiniciar: `aria-label="Reiniciar jogo"`.
- Mensagens de status devem ser announcedas com `aria-live="polite"`.

## 5. Mensagens de status
- Início do jogo: "Jogo iniciado. Sua vez de atirar no tabuleiro inimigo."
- Vitoria: "Parabéns! Todos os navios foram afundados."
- Derrota: "Todos os seus navios foram afundados. Jogo terminado."
- Cada mensagem deve ser exibida em elemento com `role="status"` ou `aria-live`.

## 6. Testes de acessibilidade
- Verificar navegação por teclado em todos os estados.
- Usar ferramentas de contraste (ex.: Lighthouse, axe) para garantir níveis mínimos.
- Testar com leitores de tela (NVDA, VoiceOver) para anúncio correto de estados.
- Validar que nenhuma informação crucial é transmitida apenas por cor.