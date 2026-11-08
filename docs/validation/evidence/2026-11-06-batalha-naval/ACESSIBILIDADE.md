# Acessibilidade - Jogo Batalha Naval

## 1. Navegação por Teclado
- O tabuleiro deve ser composto por elementos focáveis (botões, links ou divs com `tabindex="0"`).
- O jogador deve poder mover-se entre as células com as teclas de direção (Setas) ou com Tab/Shift+Tab.
- O botão "Reiniciar" e qualquer outro controle devem ser acessíveis via teclado.
- Ordem de foco lógica: tabuleiro do jogador, tabuleiro do computador, controles.

## 2. Estados que Não Dependem Apenas de Cor
- **Acerto:** além de uma cor (ex.: verde), usar um ícone (ex.: "X") ou texto alternativo.
- **Erro:** além de uma cor (ex.: vermelho), usar um ícone (ex.: "O") ou texto alternativo.
- **Navio Afundado:** usar um ícone específico ou uma animação de "explosão" que não dependa apenas de cor.
- As células devem ter `aria-label` ou `title` descrevendo o estado (ex.: "Acerto", "Erro", "Navio Afundado").

## 3. Contraste
- O contraste entre o fundo e o texto/ícone deve ser no mínimo 4.5:1 para texto normal e 3:1 para ícones grandes.
- Use ferramentas como WebAIM Contrast Checker para validação.
- Evite cores claras em fundos claros ou escuras em fundos escuros.

## 4. Textos para Leitor de Tela
- Cada célula do tabuleiro deve ter um `aria-label` descritivo (ex.: "Linha 3, Coluna 5 - Água", "Linha 3, Coluna 5 - Acerto").
- Os controles devem ter rótulos claros (ex.: botão "Reiniciar Jogo" com `aria-label`).
- Mensagens de status devem ser announcements via `aria-live="polite"` ou `role="status"`.

## 5. Mensagens de Status
- Ao initiate o jogo, anunciar "Jogo iniciado. Sua vez de jogar."
- Ao jogador acertar: "Acerto!" e se afundar um navio: "Navio afundado!".
- Ao errar: "Água!".
- Ao computador jogar: "O computador jogou na posição X, Y."
- Vitória ou derrota devem ser announcements claramente, com opção de reiniciar.

## 6. Estrutura Semântica
- Use elementos HTML semânticos: `<nav>`, `<main>`, `<section>`, `<button>`.
- O tabuleiro pode ser uma `<table>` ou uma `<div>` com `role="grid"` e `aria-label`.

## 7. Testes de Acessibilidade
- Verificar navegação apenas com teclado.
- Usar leitor de tela (NVDA, VoiceOver) para confirmar anúncios.
- Validar contraste com ferramentas de desenvolvedor.
- Testar em diferentes navegaadores e dispositivos.

## 8. Recomendações Finais
- Fornecer modo de alto contraste.
- Permitir ajuste de velocidade de animações para usuários com sensibilidade.
- Documentar os controles de teclado em uma seção de ajuda.

