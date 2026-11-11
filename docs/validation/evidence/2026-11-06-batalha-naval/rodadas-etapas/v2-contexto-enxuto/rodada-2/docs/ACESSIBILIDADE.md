# Acessibilidade - Jogo Batalha Naval

## 1. Navegação por Teclado
- O tabuleiro deve ser totalmente acessível via teclado, usando `Tab` para navegar entre as células.
- As células devem ter `tabindex="0"` e `role="button"` para serem focáveis.
- O jogo deve permitir a seleção de célula com `Enter` ou `Barra de espaço`.
- Controles alternativos: teclas de atalho (ex: `1-0` para linha, `a-j` para coluna) para selecionar posição.

## 2. Feedbacks que Não Dependem de Cor
- **Acerto**: ícone de "X" ou texto "Acerto" + som (opcional).
- **Erro**: ícone de "O" ou texto "Erro" + som.
- **Afundado**: exibir o nome do navio afundado e um ícone de "Navio afundado".
- Não use apenas cores (ex: verde para acerto, vermelho para erro). Sempre inclua texto ou ícone.

## 3. Contraste
- O tabuleiro deve ter contraste mínimo de 4.5:1 entre o fundo e os elementos.
- Use variáveis CSS para cores, permitindo tema de alto contraste.
- Fornecer botão de alternância de alto contraste.

## 4. Textos para Leitor de Tela
- Cada célula deve ter um `aria-label` descritivo, ex: "Linha 3, coluna 5, ainda não atingida".
- Ao acertar: "Acerto! Célula H3 atingida".
- Ao errar: "Erro! Célula C7 não atingida".
- Ao afundar navio: "Navio Encouraçado afundado".
- Mensagens de status do jogo (ex: "Sua vez", "Vitória!", "Derrota!") devem ser announcements via `aria-live="polite"`.

## 5. Mensagens de Status
- Use uma região `aria-live` para anunciar mudanças de estado.
- Exemplo: <div id="status" aria-live="polite" role="status"></div>
- Ao iniciar: "Jogo iniciado. Sua vez. Selecione uma célula no tabuleiro do computador."
- Ao final: "Parabéns, você venceu!" ou "O computador venceu. Jogue novamente?"

## 6. Navegação e Foco
- Ao recarregar o jogo, o foco deve ir para o botão "Iniciar" ou "Reiniciar".
- O tabuleiro deve ser organizado em regiões semânticas: <fieldset> com <legend> para cada tabuleiro.
- Exemplo:
  <fieldset>
    <legend>Tabuleiro do Jogador</legend>
    <div role="grid" aria-label="Tabuleiro do jogador">
      ...
    </div>
  </fieldset>

## 7. Configurações de Acessibilidade
- Permitir desativar sons (caso existam).
- Permitir ajuste de velocidade de animação (para usuários com vestibular).
- Fornecer opção de "Modo de alto contraste" e "Modo de redução de movimento".

## 8. Testes
- Testar com leitores de tela (NVDA, JAWS).
- Testar navegação apenas com teclado.
- Verificar contraste com ferramentas como Lighthouse.

Essas diretrizes garantem que o jogo seja inclusivo e atenda às diretrizes de acessibilidade WCAG 2.1 AA.