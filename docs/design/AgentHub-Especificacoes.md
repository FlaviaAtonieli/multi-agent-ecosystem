# AgentHub — Especificações de Redesign

Este documento descreve, tela por tela, o redesign do AgentHub para ser implementado (React, Vue, HTML/CSS puro, etc). Cobre design system, layout compartilhado, estrutura de cada página, estados, conteúdo de exemplo e as animações/microinterações propostas. Cole este arquivo inteiro (ou seção por seção) para o Claude implementar.

> **Stack de referência dos protótipos**: HTML + CSS inline, fontes Google Fonts `Manrope` (peso 500–800, usada em títulos/números) e `IBM Plex Sans` (peso 400–600, usada no corpo). Cores em hex/rgba conforme listado abaixo. Adapte para a stack real do projeto (styled-components, Tailwind, CSS Modules etc.) mantendo os valores.

---

## 1. Design system

### 1.1 Cores

| Token | Valor | Uso |
|---|---|---|
| `bg-app` | `#0a0a10` | Fundo geral da aplicação |
| `bg-sidebar` | `#0c0c13` | Fundo da sidebar |
| `bg-card` | `#111119` | Fundo de cards, tabelas, toolbars |
| `bg-input` | `#0d0d15` | Fundo de inputs, chips neutros, mini-diagramas |
| `border-subtle` | `rgba(255,255,255,0.06)` a `0.09` | Bordas padrão de cards/inputs |
| `border-strong` | `rgba(255,255,255,0.15)` a `0.22` | Bordas de hover/estado neutro mais visível |
| `text-primary` | `#f2f2f5` / `#fff` / `#f0f0f2` | Texto principal, títulos |
| `text-secondary` | `#9294a6` | Subtítulos, descrições |
| `text-tertiary` | `#6b6d80` / `#8688a0` | Texto de apoio, timestamps, placeholders |
| `text-muted` | `#5c5e70` / `#4b4d5e` | Labels de seção, texto desabilitado |
| Violeta (marca) | `#8b5cf6` – `#6366f1` (gradiente 135deg) | Botão primário, item de nav ativo, avatar, logo |
| Violeta claro | `#a78bfa` / `#c4b5fd` | Ícones ativos, chips selecionados |
| Ciano (destaque) | `#22d3ee` / `#2dd4bf` / `#67e8f9` | Links, eyebrows de seção ("VISÃO GERAL", "RASTREABILIDADE"), caixa de dica |
| Âmbar (atenção/aguardando) | `#f59e0b` / `#fbbf24` / `#fcd34d` | Status "Aguardando contexto", banner de ação, badge "Beta" |
| Verde (sucesso/ativo) | `#22c55e` / `#4ade80` / `#86efac` | Status "Concluída", "Ativa", indicador operacional, check |
| Azul-céu (em execução) | `#38bdf8` / `#7dd3fc` | Status "Em execução" |
| Vermelho (erro) | `#ef4444` / `#fca5a5` | Status "Erro", "Falha detectada" |

Padrão de badge/pill de status: fundo `rgba(<cor>,0.14)`, borda `1px solid rgba(<cor>,0.3)`, texto na cor sólida correspondente, `border-radius:999px`, `padding:4px 10px`, `font-size:11.5px`, `font-weight:600`, com um dot de `5px` à esquerda.

### 1.2 Tipografia

- **Manrope** (700–800): títulos (`h1`, nomes de card, números de estatística, logo).
- **IBM Plex Sans** (400–600): todo o restante (corpo, labels, tabelas, botões).
- Escala aproximada: eyebrow/label de seção `10–11px` (bold, `letter-spacing: 0.08–0.1em`, uppercase); corpo de tabela/descrição `12–13.5px`; título de card `14.5–16px`; H1 de página `27–29px` (Manrope 800); números de estatística `26–27px` (Manrope 800).

### 1.3 Espaçamento e forma

- Sidebar: `240px` fixa. Topbar: `64px` de altura.
- Conteúdo principal: `padding: 28px 32px 40px`.
- Cards: `border-radius: 12–14px`, borda `1px solid rgba(255,255,255,0.07)`, fundo `#111119`.
- Botões: `border-radius: 8–10px`.
- Grids de tabela: sempre definir `gap` explícito (`10–12px`) entre colunas — nunca deixar `grid-template-columns` sem gap (bug já corrigido no protótipo: colunas coladas sem espaçamento).
- Largura de referência do artboard: `1440px`.

### 1.4 Animações e microinterações

Todas sutis, sem exagero — nada de bounce forte ou durações longas.

- **Entrada de seção** (`fade-up`): `opacity 0→1` + `translateY(10px→0)`, `0.5s ease`, aplicada em blocos principais da página (header, banner, stat row, corpo) com pequenos `animation-delay` escalonados (ex.: `0.02s`, `0.09s`, `0.16s`, `0.22s`) para um efeito de cascata leve ao carregar a página.
- **Pulso em indicador "ao vivo"** (`pulse-dot` / `pulse-dot-green`): `box-shadow` expandindo de um ring sólido para transparente, `2–2.4s ease-out infinite` — usado no dot do status "Aguardando contexto" (âmbar) e no indicador "Ecossistema operacional" da sidebar (verde).
- **Hover de botões**: `transform: translateY(-1px)` + `filter: brightness(1.1)` (botão primário) ou leve mudança de fundo/borda (botão ghost/outline), `0.15s ease`.
- **Hover de linha de tabela / item de nav / chip de filtro**: fundo sobe para `rgba(255,255,255,0.025–0.06)`, `0.15s ease`.
- **Hover de card de skill**: `translateY(-2px)`, borda vira `rgba(139,92,246,0.35)`, fundo levemente mais claro, `0.18s ease`.
- **Check/avanço de etapa no wizard** (`pop-in`): elemento nasce em `scale(0.4)` opaco 0, passa por um leve overshoot em `scale(1.15)` e assenta em `scale(1)` — `0.4s ease` — usado no círculo numerado do step ativo e nos checkmarks do checklist ao vivo quando um campo é considerado preenchido.

Nenhuma animação deve durar mais que ~0.5s nem repetir com frequência menor que ~2s (evitar poluição visual).

---

## 2. Layout compartilhado (todas as páginas internas)

### 2.1 Sidebar (240px, fixa à esquerda)

1. **Cabeçalho da marca** (padding `22px 20px`, borda inferior sutil): ícone quadrado `32×32px`, `border-radius:8px`, gradiente violeta, letra "A" em branco (Manrope 800) + texto "AgentHub" (Manrope 700, 14.5px) e subtítulo "Ecossistema de Agent Skills" (11px, cor terciária).
2. **Navegação** (padding `16px 12px`), duas seções com label uppercase (10px, `#4b4d5e`):
   - **PRINCIPAL**: Visão geral (ícone grid 2×2), Nova solicitação (ícone +), Orquestrações (ícone camadas/fluxo).
   - **ECOSSISTEMA**: Agent Skills (ícone losango), Auditoria (ícone escudo com check).
   - Cada item: ícone `18×18px`, texto `13.5px`. Item ativo: fundo `rgba(139,92,246,0.16)`, ícone e texto em cor clara/violeta clara, `font-weight:600`. Itens inativos: ícone/texto em cinza (`#6b6d80` / `#9294a6`), `font-weight:500`. Hover: fundo `rgba(255,255,255,0.045)`.
3. **Card de status do sistema** (rodapé, `margin:16px`, fundo verde translúcido `rgba(34,197,94,0.08)`, borda `rgba(34,197,94,0.18)`): dot verde pulsante + "Ecossistema operacional" (12px, 600) + "Base de orquestração v1" (11px, cinza) abaixo.

### 2.2 Topbar (64px, topo da área de conteúdo)

- Fundo transparente, borda inferior sutil, `padding: 0 32px`, `display:flex; justify-content:space-between`.
- Esquerda: eyebrow fixo "MULTI-AGENT ECOSYSTEM" (11px, bold, `letter-spacing:0.1em`, cinza).
- Direita: nome do usuário + cargo (alinhado à direita, duas linhas: "Paulo Guilherme Richeski Padilha" 13px/600 e "Usuário técnico" 11px cinza) + avatar circular `34×34px` com gradiente violeta e inicial "P" + botão "Sair" (outline neutro).

Este bloco (sidebar + topbar) é idêntico em todas as 7 páginas internas — implementar como componente de layout único (`<AppShell>`) que recebe o conteúdo da página e o item de nav ativo.

---

## 3. Página: Visão Geral (Dashboard / Home)

**Rota sugerida**: `/` ou `/dashboard`. Item de nav ativo: Visão geral.

### 3.1 Header da página
- Eyebrow "VISÃO GERAL" (ciano, 11px). H1 "Olá, {primeiroNome}." (Manrope 800, 29px). Subtítulo "Acompanhe solicitações, estados e eventos do ecossistema de agentes." (13.5px, cinza).
- Botão primário à direita, alinhado à base do bloco: "+ Nova solicitação" (gradiente violeta, ícone de +, `box-shadow` violeta suave) — navega para o wizard.

### 3.2 Banner de ação (condicional)
Exibido **somente quando existir ao menos 1 solicitação com status "Aguardando contexto"**. Fundo âmbar translúcido (`rgba(245,158,11,0.08)`, borda `rgba(245,158,11,0.28)`), `border-radius:12px`, `padding:16px 20px`.
- Esquerda: ícone de alerta (triângulo) em box `34×34px` + texto: título dinâmico "{N} solicitação(ões) aguardando complementação" (bold, âmbar) e descrição "'{título da solicitação}' precisa de mais detalhes técnicos antes de seguir para o Orientador de Interação." (cinza claro).
- Direita: botão outline âmbar "Completar agora →" que leva direto para a tela de complementação da solicitação mais antiga pendente (ou para a lista filtrada por "Aguardando", se houver mais de uma).
- Se não houver pendências, o banner não é renderizado (não usar estado vazio "tudo certo" — apenas omitir).

### 3.3 Linha de estatísticas (4 cards, grid `repeat(4, 1fr)`, gap 16px)
Cada card: ícone em box `28×28px` colorido + label (12px) + número grande (Manrope 800, 27px) + descrição de apoio (11.5px).
1. **Orquestrações em execução** (ícone camadas, violeta) — número = contagem de status "Em execução". Apoio: "Qualificadas ou em processamento".
2. **Aguardando contexto** (ícone relógio, âmbar — card com fundo/borda âmbar translúcidos quando > 0) — número = contagem status "Aguardando contexto". Apoio: "Dependem de complementação".
3. **Solicitações registradas** (ícone documento, ciano) — total geral. Apoio: "Cada uma possui Trace ID".
4. **Taxa de sucesso** (ícone check em círculo, verde) — percentual de concluídas / total finalizado. Apoio: "Calculada após fluxos concluídos".

### 3.4 Corpo: tabela + coluna lateral (grid `1fr 348px`, gap 20px)

**Card "Solicitações técnicas" (esquerda)**:
- Header do card: eyebrow "FLUXOS RECENTES" (ciano) + título "Solicitações técnicas" (Manrope 16px/700) à esquerda; link "Ver todas →" à direita (leva para Orquestrações).
- Toolbar: campo de busca (placeholder "Buscar por título ou Trace ID...") + dropdown "Todos os status".
- Tabela compacta, **4 colunas** com `grid-template-columns: 2.6fr 1.5fr 1.3fr 0.9fr; gap: 12px` (⚠️ gap é obrigatório — sem ele o Trace ID cola visualmente na Data):
  - **SOLICITAÇÃO**: título (13.5px/600) + descrição curta (12px, cinza) empilhados; container com `min-width:0` para permitir truncamento/wrap seguro.
  - **STATUS**: pill de status (ver §1.1) — usar `white-space:nowrap` para não quebrar em duas linhas.
  - **TRACE ID**: fonte monoespaçada, `white-space:nowrap`.
  - **DATA**: `white-space:nowrap`, apenas texto (sem botão de ação embutido nesta versão compacta — a ação "Completar" já está coberta pelo banner acima; ação completa fica na tela de Orquestrações).
  - Mostrar no máximo as ~5 solicitações mais recentes; abaixo da última linha, texto centralizado "Novas solicitações registradas aparecerão nesta lista." quando a lista estiver vazia ou curta.

**Coluna lateral (direita, 348px)**:
- **Card "Atividade recente"** (eyebrow "RASTREABILIDADE"): timeline vertical (linha conectando os dots) com os eventos mais recentes de TODAS as solicitações, mais recente no topo. Cada item: dot colorido por origem (âmbar = sistema/guia de interação, violeta = usuário/registro inicial, azul = usuário/ação), título do evento (12.5px/600), descrição (11.5px, cinza, até 2 linhas), e rodapé "{ORIGEM} · {data, hora}" (10.5px, `#5c5e70`). Limitar a ~4 itens mais recentes.
- **Card "Como o ecossistema decide"** (eyebrow "ARQUITETURA", card demotado/secundário — é referência, não a ação principal da tela): frase curta do fluxo ("Solicitação → contexto → planejamento → agentes → validação") + um mini-diagrama horizontal com 3 nós (Orientador → Orquestrador destacado → Quality Gate) ligados por setas finas. Link "Ver diagrama →" no canto para abrir a versão completa (modal ou página separada, fora do escopo deste redesign).

---

## 4. Página: Orquestrações (Histórico de solicitações)

**Rota sugerida**: `/orquestracoes`. Item de nav ativo: Orquestrações.

### 4.1 Header
- Eyebrow "ORQUESTRAÇÕES", H1 "Histórico de solicitações" (27px), subtítulo "Consulte estados, Trace IDs e o histórico de eventos de cada fluxo." Botão primário "+ Nova solicitação" à direita.

### 4.2 Toolbar
- Campo de busca (max-width 340px, placeholder "Buscar por título ou Trace ID...").
- **Chips de filtro por status** (grupo com fundo neutro `#111119`, padding 4px): "Todas · {total}" (selecionado, fundo violeta translúcido), "Aguardando · {n}" (âmbar), "Em execução · {n}" (azul), "Concluída · {n}" (verde), "Erro · {n}" (vermelho). Clique filtra a tabela abaixo; contadores sempre refletem os dados reais.
- Dropdown de ordenação à direita: "Mais recentes" (padrão) / outras opções de ordenação conforme necessidade do backend.

### 4.3 Tabela completa
Card único, `grid-template-columns: 2.4fr 1.2fr 1.4fr 1fr 1.1fr; gap: 10px` (gap obrigatório, mesmo motivo do §3.4). Colunas: **SOLICITAÇÃO** (título + descrição), **STATUS** (pill), **TRACE ID** (mono), **DATA**, **AÇÕES**.

Comportamento da coluna AÇÕES varia por status:
- **Aguardando contexto** — botão outline âmbar "Completar contexto" (leva à tela/modal de complementação).
- **Em execução / Concluída / Erro** — link "Ver detalhes →" (leva à página de detalhe do fluxo, com timeline completa de eventos — reaproveitar o componente de timeline do §3.4).

Linhas de exemplo de referência (para popular estados durante o desenvolvimento):
| Título | Descrição | Status | Trace ID | Data |
|---|---|---|---|---|
| teste | quero criar uma página de mensagens simples | Aguardando contexto | TRC-20260826-79A756 | 25/08, 22:41 |
| Refatorar client HTTP | validar retry exponencial no serviço de billing | Em execução | TRC-20260825-3C1F02 | 25/08, 14:12 |
| Migração de cache Redis | avaliar impacto de TTL customizado | Concluída | TRC-20260824-9B8A10 | 24/08, 09:30 |
| Webhook duplicando eventos | investigar causa raiz de replays | Erro | TRC-20260823-114DAE | 23/08, 18:05 |

Rodapé da tabela: nota discreta (11.5px, centralizada) — remover em produção, era apenas explicativa do protótipo.

---

## 5. Fluxo: Nova solicitação (wizard de 3 etapas)

**Rota sugerida**: `/nova-solicitacao/1`, `/2`, `/3` (ou estado local de step em uma única rota `/nova-solicitacao`). Item de nav ativo: Nova solicitação. Container do formulário: `max-width: 1180px`.

### 5.1 Estrutura comum às 3 etapas
- Eyebrow "NOVA SOLICITAÇÃO", H1 "Qualifique uma demanda técnica" (27px), subtítulo "Esses dados formarão o contexto inicial entregue ao Orientador de Interação."
- **Stepper horizontal** (max-width 640px): 3 círculos numerados conectados por linhas.
  - Etapa **futura**: círculo `30×30px`, borda `1.5px solid rgba(255,255,255,0.15)`, número em cinza (`#5c5e70`), label em cinza (`#5c5e70`, 500).
  - Etapa **atual**: círculo com gradiente violeta preenchido, número branco (Manrope 700), label branca (600) — anima com `pop-in` ao entrar na etapa.
  - Etapa **concluída**: círculo verde translúcido com borda sólida `#22c55e` e ícone de check (em vez do número), label em cinza claro (`#8688a0`, 500, sem tachado). Linha conectora à direita de uma etapa concluída fica verde (`opacity:0.4`); as demais linhas ficam cinza translúcido.
- Layout de 2 colunas abaixo do stepper: `grid-template-columns: 1fr 320px; gap:20px`.
  - **Coluna esquerda — card de formulário** (fundo `#111119`, padding `26px 26px 22px`): campos específicos da etapa (ver 5.2–5.4). Campo em foco/preenchimento ativo tem borda violeta + glow (`box-shadow: 0 0 0 3px rgba(139,92,246,0.12)`), placeholder em `#5c5e70`.
  - **Coluna direita — painel de orientação**, dois blocos empilhados:
    - **"CHECKLIST DE CONTEXTO"**: lista de 5 itens (Título, Problema descrito, Objetivo claro, Contexto técnico completo, Restrições informadas). Estado de cada item muda ao vivo conforme o preenchimento:
      - **pendente**: círculo vazio com borda cinza, texto cinza.
      - **atual/em foco**: círculo com borda violeta, fundo da linha levemente violeta, texto branco/600 — indica o que a etapa corrente está preenchendo.
      - **concluído**: círculo preenchido verde com checkmark (anima com `pop-in`), texto tachado em cinza (`text-decoration: line-through`, cor do tracejado `rgba(255,255,255,0.2)`).
    - **Caixa "Dica"** (fundo ciano translúcido, ícone "i" circular): texto curto e específico da etapa (ver abaixo), reforçando boas práticas para reduzir retrabalho.
- **Rodapé de navegação**: botão "Voltar" (ghost, com seta esquerda — ausente na etapa 1) à esquerda; botão primário à direita, texto muda por etapa: etapa 1 e 2 = "Continuar →"; etapa 3 = "Registrar e gerar Trace ID" (sem seta, ação final que cria a solicitação e devolve o Trace ID). Etapa 1 tem também "Cancelar" (ghost) no lugar de "Voltar".

### 5.2 Etapa 1 — Identificação
- Campo **Título** (obrigatório, input de texto simples): placeholder "Ex.: Erro de timeout no serviço de pagamentos". Apoio: "Uma identificação curta e específica — evite títulos genéricos como 'teste'." (reforça, com humor sutil, o problema real observado no uso atual do sistema).
- Campo **Tipo de solicitação** (opcional, badge "opcional" ao lado do label): chips selecionáveis de escolha única — "Dúvida técnica" (selecionado por padrão no protótipo), "Bug", "Nova funcionalidade", "Refatoração", "Outro". Apoio: "Ajuda o Orientador de Interação a rotear a solicitação mais rápido."
- Checklist nesta etapa: apenas "Título" fica marcado como atual/preenchendo.
- Dica: "Um título específico (ex.: 'Erro de timeout no serviço de pagamentos') ajuda o Orientador a rotear a demanda mais rápido — e reduz idas e voltas por falta de contexto."

### 5.3 Etapa 2 — Problema & objetivo
- Campo **Problema a ser analisado** (textarea, obrigatório, min-height ~96px): placeholder "Descreva o comportamento atual, a divergência ou a dúvida técnica...". Abaixo, caixa de exemplo (ícone "i" cinza): *"Exemplo: 'O endpoint /checkout retorna 504 após ~30s quando o carrinho tem mais de 20 itens. Em produção acontece desde a última implantação.'"*
- Campo **Objetivo da análise** (textarea, obrigatório, min-height ~72px): placeholder "Informe qual resposta ou resultado você espera obter...". Exemplo: *"Exemplo: 'Identificar se o timeout vem do gateway de pagamento ou da nossa API, e propor um limite seguro.'"*
- Checklist: "Título" já concluído (tachado); "Problema descrito" e "Objetivo claro" ficam como atuais.
- Dica: "Descreva o comportamento ATUAL antes do esperado, e diferencie sintoma de causa provável — isso evita uma rodada extra de perguntas."

### 5.4 Etapa 3 — Contexto & restrições
- Campo **Contexto técnico** (textarea, obrigatório, min-height ~110px): placeholder "Inclua módulos, tecnologias, artefatos, dependências e comportamento esperado...". Abaixo, chips de sugestão clicáveis (preenchem/guiam o campo, não são obrigatórios): "Módulos", "Tecnologias", "Dependências", "Comportamento esperado".
- Campo **Restrições** (input de tags, opcional): usuário digita e cria tags removíveis (ex. tag de exemplo "Não executar alterações automaticamente" com "×" para remover) + affordance "+ Adicionar restrição". Apoio: "Separe restrições por linha ou vírgula — cada uma vira uma tag independente."
- Checklist: todos os 4 itens anteriores já concluídos (tachados); "Contexto técnico completo" e "Restrições informadas" ficam como atuais.
- Dica: "Cite arquivos, módulos ou serviços pelo nome. Solicitações sem isso costumam voltar como 'aguardando contexto'."
- Ação final "Registrar e gerar Trace ID": cria a solicitação, gera o Trace ID (formato `TRC-AAAAMMDD-XXXXXX`) e redireciona para a Visão Geral ou para a página de detalhe da solicitação recém-criada.

---

## 6. Página: Agent Skills

**Rota sugerida**: `/agent-skills`. Item de nav ativo: Agent Skills.

> ⚠️ **Nota de conteúdo**: esta tela não existia no app original — o conteúdo abaixo foi inferido a partir do nome do produto ("Ecossistema de Agent Skills") e dos nós do diagrama de arquitetura (Orientador, Legado, Orquestrador, Negócio, Quality Gate). Ajuste os campos/skills reais conforme o modelo de dados do backend.

### 6.1 Header
- Eyebrow "AGENT SKILLS", H1 "Habilidades do ecossistema" (27px), subtítulo "Catálogo de skills disponíveis para os agentes do AgentHub — o que cada uma faz e quem a utiliza." Botão primário "+ Nova skill" à direita.

### 6.2 Toolbar
- Busca por nome da skill (max-width 340px).
- Chips de filtro por status: "Todas · {total}" (padrão), "Ativas · {n}" (verde), "Beta · {n}" (âmbar). (Extensível para "Descontinuada" se o modelo real tiver esse estado.)

### 6.3 Grid de cards (3 colunas, `repeat(3, 1fr)`, gap 16px)
Cada **card de skill** (`skill-card`, hover eleva e ilumina a borda — ver §1.4):
- Topo: ícone `38×38px` em box colorido (cor por categoria do agente responsável) à esquerda + badge de status à direita ("Ativa" verde ou "Beta" âmbar).
- Nome da skill (Manrope 15px/700).
- Descrição curta, 1–2 linhas (12.5px, cinza).
- Rodapé do card: badge do **agente responsável** (pill neutra, ex. "Orientador", "Legado", "Orquestrador", "Negócio", "Quality Gate") à esquerda + **versão** em mono (ex. `v2.1`) à direita.

Skills de exemplo usadas no protótipo (para popular a tela em desenvolvimento):

| Skill | Descrição | Agente | Versão | Status |
|---|---|---|---|---|
| Qualificação de Contexto | Avalia se uma solicitação técnica tem contexto suficiente antes de prosseguir no fluxo. | Orientador | v2.1 | Ativa |
| Leitura de Legado | Analisa código e documentação de sistemas legados para levantar dependências. | Legado | v1.4 | Ativa |
| Roteamento de Demanda | Direciona a solicitação para o agente especializado com base no tipo e no contexto. | Orquestrador | v3.0 | Ativa |
| Validação de Regras de Negócio | Confere se a proposta de solução respeita regras e políticas internas. | Negócio | v1.2 | Ativa |
| Quality Gate Automatizado | Executa checklist de qualidade antes de liberar o fluxo como concluído. | Quality Gate | v0.9 | Beta |
| Geração de Trace ID | Cria um identificador único e rastreável para cada solicitação registrada. | Orquestrador | v1.0 | Ativa |

Clique no card — idealmente abre um painel/página de detalhe da skill (changelog de versão, agentes que a usam, exemplos de uso) — não prototipado nesta rodada, mas é o próximo passo natural de navegação.

---

## 7. Página: Auditoria

**Rota sugerida**: `/auditoria`. Item de nav ativo: Auditoria.

> ⚠️ Mesma ressalva do §6: tela nova, inferida — validar o modelo de dados real de eventos/logs com o time.

### 7.1 Header
- Eyebrow "AUDITORIA", H1 "Trilha de auditoria" (27px), subtítulo "Histórico completo de eventos do ecossistema, por agente e por solicitação, para conformidade e rastreabilidade." Botão **outline** (não primário — ação secundária) "Exportar CSV" à direita, com ícone de download.

### 7.2 Linha de estatísticas (4 cards, mesma estrutura do §3.3, mas números simples sem ícone):
1. Eventos registrados hoje.
2. Decisões automatizadas (ações tomadas por agentes, sem intervenção humana).
3. Intervenções manuais (ações do usuário, ex. complementar contexto).
4. Alertas de conformidade (destacar em verde quando 0; usar vermelho/âmbar se > 0 — indicar algo que precisa de atenção).

### 7.3 Toolbar
- Busca por evento ou Trace ID.
- Chips de filtro por **origem/agente**: "Todos os agentes" (padrão), "Interaction Guide", "Orquestrador", "Quality Gate" (extensível conforme os agentes reais do sistema).
- Dropdown de período à direita: "Últimos 7 dias" (padrão), com outras opções de range de data.

### 7.4 Tabela de eventos
`grid-template-columns: 2fr 1.3fr 1.8fr 1.4fr 1fr; gap: 10px` (gap obrigatório). Colunas: **EVENTO** (nome da ação, 13px/600), **ORIGEM** (badge colorida por tipo: `USER` azul, `INTERACTION_GUIDE` violeta, `ORQUESTRADOR` ciano, `QUALITY_GATE` verde), **SOLICITAÇÃO** (título da solicitação relacionada), **TRACE ID** (mono, truncado como `TRC-...79A756`), **DATA/HORA**.

Eventos de exemplo (9 linhas, cobrindo as 4 solicitações do histórico):
1. Solicitação registrada — USER — teste — 25/08, 22:41
2. Complementação necessária — INTERACTION_GUIDE — teste — 25/08, 22:41
3. Contexto complementado — USER — teste — 25/08, 22:42
4. Mais contexto necessário — INTERACTION_GUIDE — teste — 25/08, 22:42
5. Roteada para Orquestrador — ORQUESTRADOR — Refatorar client HTTP — 25/08, 14:11
6. Execução iniciada — ORQUESTRADOR — Refatorar client HTTP — 25/08, 14:12
7. Quality Gate aprovado — QUALITY_GATE — Migração de cache Redis — 24/08, 09:35
8. Fluxo concluído — ORQUESTRADOR — Migração de cache Redis — 24/08, 09:36
9. Falha detectada — QUALITY_GATE — Webhook duplicando eventos — 23/08, 18:07

Cada linha deve, idealmente, ser clicável e levar à página de detalhe da solicitação correspondente (Orquestrações → detalhe), reforçando a rastreabilidade ponta a ponta.

---

## 8. Tour de primeiro acesso (onboarding)

Exibido automaticamente **apenas na primeira vez** que um usuário acessa a Visão Geral (controlar por flag no perfil do usuário/localStorage, ex. `onboarding_dashboard_completo = true` após o último passo ou ao clicar em "Pular"). 4 passos, todos sobrepostos à própria tela de Visão Geral (não são páginas separadas — é um overlay).

### 8.1 Mecânica visual
- Um **spotlight**: a tela inteira escurece (`rgba(6,6,10,0.72)`) exceto uma área retangular com cantos arredondados ao redor do elemento em destaque, que ganha um anel violeta (`box-shadow: 0 0 0 3px rgba(139,92,246,0.65), 0 0 24px 2px rgba(139,92,246,0.35)`).
- Um **tooltip/card de instrução** próximo ao elemento destacado, contendo: contador "Passo {n} de 4", título curto, descrição (1–2 frases), e ações "Pular tour" (texto/ghost) + botão primário "Próximo" (ou "Concluir" no último passo).
- Transição entre passos: fade/leve slide, mesma duração das outras animações (~0.3–0.5s) — nada abrupto.

### 8.2 Roteiro dos 4 passos
1. **Navegação principal** (spotlight na sidebar/nav) — "Bem-vindo ao AgentHub": *"Aqui você acompanha todas as solicitações e o estado do ecossistema de agentes em tempo real."*
2. **Botão "Nova solicitação"** (spotlight no botão primário do header) — "Toda demanda começa aqui": *"Um assistente guiado em 3 passos garante que o Orientador de Interação receba contexto suficiente logo na primeira tentativa."*
3. **Banner de pendências** (spotlight no banner de ação âmbar, ou nos cards de estatística se não houver pendência no momento) — "Fique de olho nas pendências": *"Quando uma solicitação precisa de mais informações, ela aparece aqui com um atalho para completar rapidamente."*
4. **Coluna "Atividade recente"** (spotlight na timeline lateral) — "Acompanhe cada passo" (último passo, botão vira "Concluir"): *"Todo evento do fluxo — decisões automáticas e ações manuais — fica registrado aqui, com origem e horário."*

### 8.3 Regras de implementação
- Deve poder ser reaberto manualmente (ex. item "Rever tour" em um menu de ajuda/perfil), para usuários que queiram revisitar.
- "Pular tour" encerra o overlay imediatamente em qualquer passo e marca o onboarding como visto.
- Não bloquear scroll/clique fora da spotlight de forma permanente — apenas durante a exibição do tour.

---

## 9. Itens em aberto para validar com o time antes da implementação

1. **Agent Skills e Auditoria** (§6 e §7): conteúdo e modelo de dados inferidos — confirmar nomes reais de skills, agentes, categorias e estrutura de eventos de auditoria.
2. **Taxa de sucesso** (§3.3): confirmar a regra de cálculo exata (ex.: concluídas ÷ (concluídas + erro), ou concluídas ÷ total finalizado).
3. **Detalhe de solicitação**: as telas referenciam uma página de "detalhe" (links "Ver detalhes →", clique em linha de auditoria) que não foi desenhada nesta rodada — necessária para fechar a navegação ponta a ponta.
4. **Persistência do onboarding**: definir se o flag fica no backend (por usuário) ou local (localStorage) — recomendação: backend, para persistir entre dispositivos.
