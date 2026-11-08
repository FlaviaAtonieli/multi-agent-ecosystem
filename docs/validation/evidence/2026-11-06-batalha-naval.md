# Cenário de teste: clã de jogos gerando uma batalha naval, 06/11/2026

Este cenário pede ao ecossistema o código-fonte de um jogo simples e verifica, jogando de verdade no navegador, se o jogo funciona. Ele mede a qualidade do que é entregue, e não só se a orquestração termina.

Os arquivos ficam em [`2026-11-06-batalha-naval/`](2026-11-06-batalha-naval/):
- o jogo gerado: `jogo-gerado/`;
- os documentos de cada agente;
- o teste automatizado: `playtest.js`;
- as telas.

## Montagem

- **Clã "Desenvolvimento de Jogos"**, criado por [`backend/scripts/create_game_dev_clan.py`](../../../backend/scripts/create_game_dev_clan.py), com 5 Agent Skills:

| Skill | Entrega pedida na persona |
|---|---|
| Programação de Jogos Web | `index.html`, `style.css` e `game.js`, jogáveis abrindo o HTML. **Só ela escreve código.** |
| Game Design | `GDD.md` com regras, turnos, feedback e vitória |
| Metodologia de Desenvolvimento de Jogos | `BACKLOG.md` com histórias e critérios de aceite |
| Qualidade e Testes de Jogos | `PLANO_DE_TESTES.md` com casos de borda |
| UX e Acessibilidade de Jogos | `ACESSIBILIDADE.md` com teclado, cor e leitor de tela |

- **Por que dividir o trabalho nas personas:** as skills não conversam entre si, e cada uma recebe a mesma solicitação. Se todas escrevessem o jogo, sairiam 5 versões concorrentes.
- **Solicitação:**
  - pede o código-fonte completo de uma batalha naval contra o computador;
  - tabuleiros 10x10 e frota 5, 4, 3, 3, 2 sem sobreposição;
  - tiro do computador aleatório em casa ainda não atingida;
  - acerto, erro, afundado, vitória, derrota e reinício.
- **Ambiente:**
  - backend local, com cada skill em um processo MCP separado, como em produção;
  - modelo gratuito `dots-studio/dots-3-note-preview:free`;
  - RAG desligado, porque a base de conhecimento não tem documentos de jogos.

## Resultado da orquestração

- Terminou em **80 s**, com os 5 agentes respondendo e **7 arquivos** gerados. A divisão foi respeitada: o código veio só da skill de programação.
- **As 5 respostas tiveram confiança BAIXA**, e o Quality Gate mandou o resultado para revisão humana. O motivo é a regra de confiança: ela se baseia em trechos recuperados da base de conhecimento, e não houve nenhum.
- Dois agentes puseram o prefixo `generated_files/` no nome do arquivo (`generated_files/GDD.md`).

## O jogo funciona? 16 de 19 verificações

`playtest.js` abre o `index.html` no Chrome e joga partidas inteiras.

| Verificação | Resultado |
|---|---|
| Abre sem erro no console | ✅ |
| Dois tabuleiros de 100 casas | ✅ |
| Frota 5, 4, 3, 3, 2, com 17 casas de navio visíveis só no tabuleiro do jogador | ✅ |
| Posicionamento válido (sem sobreposição e dentro do tabuleiro) em 200 partidas | ✅ |
| Tiro na água marcado como erro | ✅ |
| Tiro repetido na mesma casa é ignorado | ✅ |
| Afundar a frota inteira dá vitória | ✅ |
| Perder a frota inteira dá derrota | ✅ |
| Botão de reiniciar aparece no fim e zera a partida | ✅ |
| Depois do fim, não dá para atirar | ✅ |
| Nenhum erro de JavaScript na partida inteira | ✅ |
| **O jogador vê o resultado do próprio tiro** | ❌ A mensagem "Acerto! Navio afundado!" é trocada na hora pela jogada do computador |
| **O erro do computador no tabuleiro do jogador aparece como erro** | ❌ Aparece com a mesma marca de acerto (`hit`) |
| **Dá para jogar com o teclado** | ❌ As casas são `div` sem foco: só o mouse funciona |

## O que isso mostra sobre a arquitetura

1. **O resultado é utilizável.** Um jogo funcional, em 80 s e com modelo gratuito, com regras corretas e sem erros de execução. Os 3 defeitos são de feedback e acessibilidade, não de lógica.
2. **Os agentes não leem uns aos outros.** O `ACESSIBILIDADE.md` pede casas focáveis e navegação por teclado, e o `PLANO_DE_TESTES.md` tem casos que pegariam o feedback sobrescrito. Mas o código foi escrito ao mesmo tempo, sem ver esses documentos. É o limite de executar as skills em paralelo e de forma independente. Uma segunda etapa, com a skill de programação recebendo os documentos das outras, provavelmente evitaria 2 dos 3 defeitos. Isso não foi testado.
3. **A confiança penaliza áreas sem base de conhecimento.** Para temas fora da base, como jogos, a confiança sempre sai BAIXA, mesmo quando a entrega funciona. A regra mede se há evidência documental, não se a resposta é boa.
4. **A revisão humana foi acionada corretamente.** O Quality Gate não aprovou sozinho um código que tinha defeitos.

## O que não foi feito

- O cenário não rodou em produção. Pode ser repetido com o script do clã e uma conta real.
- Foi uma execução só: com outro sorteio, o modelo pode gerar outro jogo.
- A segunda etapa com os documentos das outras skills não foi implementada.
