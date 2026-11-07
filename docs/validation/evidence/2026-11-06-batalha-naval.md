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
2. **Os agentes não leem uns aos outros.** O `ACESSIBILIDADE.md` pede casas focáveis e navegação por teclado, e o `PLANO_DE_TESTES.md` tem casos que pegariam o feedback sobrescrito. Mas o código foi escrito ao mesmo tempo, sem ver esses documentos. Isso levou à segunda etapa, descrita abaixo.
3. **A confiança penaliza áreas sem base de conhecimento.** Para temas fora da base, como jogos, a confiança sempre sai BAIXA, mesmo quando a entrega funciona. A regra mede se há evidência documental, não se a resposta é boa.
4. **A revisão humana foi acionada corretamente.** O Quality Gate não aprovou sozinho um código que tinha defeitos.

## Segunda etapa: o programador recebe os requisitos do time (06 e 07/11/2026)

Implementado no PR do `team_context`. Quando a solicitação pede arquivos:
- as skills que entregam código rodam **depois** das outras;
- elas recebem as **linhas de requisito** dos documentos dos outros agentes (até 2.500 caracteres);
- se o programador não entregar código, tenta de novo uma vez sem esse contexto.

### Teste de caixa-preta

O `playtest-caixa-preta.js` só olha a tela e clica, sem ler variáveis do jogo, porque cada geração usa nomes diferentes. Ele tem 17 verificações. Foi corrigido várias vezes, sempre a favor de não acusar o jogo por engano:
- espera a jogada do computador, que em alguns jogos leva 1 s;
- não conta a derrota "o computador venceu" como vitória;
- ignora os rótulos de coordenada (A1, J10) escritos nas casas e na borda da grade.

Com a versão final, o jogo original continua com 13 de 17.

### Resultados

| Programador | Requisitos do time | Nota | Custo |
|---|---|---|---|
| `dots-3-note:free`, uma etapa (o original) | não | 13 de 17 | grátis |
| `dots-3-note:free`, duas etapas, documentos inteiros (~6 mil caracteres), 3 rodadas | sim | jogo quebrado, plano em vez de código, nenhum arquivo | grátis |
| `dots-3-note:free`, duas etapas, só requisitos (~2.300 caracteres), 3 rodadas | sim | 2 jogos que não terminam a partida (o navegador travou) e 1 rodada sem código mesmo com a nova tentativa | grátis |
| `openai/gpt-5-mini` | **sim** | **17 de 17** | US$ 0,014 |
| `openai/gpt-5-mini` | não | 11 de 17 | US$ 0,014 |
| `openai/gpt-5.4-mini` | **sim** | **16 de 17** | US$ 0,019 |

As 3 chamadas pagas usaram só a skill de programação, com o mesmo prompt que o orquestrador monta ([`modelos-pagos/implementer_call.py`](2026-11-06-batalha-naval/modelos-pagos/implementer_call.py)). Os requisitos do time vieram dos documentos já gerados:
- GDD, backlog e plano de testes vieram do `gpt-5-mini`, na rodada paga anterior;
- o documento de acessibilidade veio do modelo gratuito, porque o agente de UX falhou na rodada paga.

**Falhas confirmadas à mão:**
- Jogo do `gpt-5-mini` sem requisitos: o tiro do jogador não aparece no tabuleiro do computador (a casa continua branca), e não há jogo pelo teclado. Os outros 4 FAILs desse jogo não foram confirmados na inspeção manual.
- Jogo do `gpt-5.4-mini`: a falha é real. O resultado do tiro aparece na casa (O ou X), mas a mensagem é trocada na hora pela jogada do computador.

### O que isso mostra

1. **Com um modelo capaz, a segunda etapa resolveu os defeitos que o time já tinha apontado.**
   - O mesmo `gpt-5-mini` fez 17 de 17 com os requisitos e 11 de 17 sem eles.
   - Teclado, feedback do tiro e marcação de acerto e erro aparecem quando o programador recebe o `ACESSIBILIDADE.md` e o plano de testes.
2. **Com o modelo gratuito, a orquestração não compensa o modelo.** Com ou sem a segunda etapa, ele entregou código quebrado ou nenhum código na maioria das rodadas. O limite ali é o modelo.
3. **É uma amostra pequena:** uma execução por condição no pago. Os números mostram a direção, não uma taxa.

### Achado de custo

A primeira rodada paga (orquestração completa) custou US$ 0,076. **4 respostas usaram 7 chamadas pagas**, e o programador não chegou a rodar:
- o cliente desistia aos 45 s e repetia sozinho;
- a chamada original continuava na OpenRouter e era cobrada.

A correção está no PR #113. Total pago nos testes de 07/11/2026: **US$ 0,122**.

## O que não foi feito

- O cenário completo não rodou em produção. Pode ser repetido com o script do clã e uma conta real.
- Não há repetições suficientes para medir taxa de acerto por modelo.
