# RFC: Request for Comments - Projeto de Portfólio

## Arquitetura de Integração de Agentes Especialistas em Ambientes Corporativos

**Linha do Projeto:** Inteligência Artificial / Arquitetura de Software / Sistemas Distribuídos  
**Autor:** Flavia Antonioli de Souza  
**Data da proposta:** 25/05/2026  
**Versão:** 3.0  
**Local:** Joinville, 2026

---

# 1. Visão de Produto e Impactos (O Problema)

O desenvolvimento de software em ecossistemas corporativos de grande dimensão, como plataformas de gestão empresarial (ERP), enfrenta um desafio crítico: a fragmentação do conhecimento. Em ambientes onde coexistem sistemas legados, arquiteturas modernas e múltiplos domínios de negócio, a execução de tarefas complexas deixa de ser um desafio estritamente técnico e torna-se um gargalo de orquestração e integração de saberes.

Para preencher esta lacuna estrutural, este documento propõe o desenvolvimento de um **Ecossistema de Integração de Agentes Especialistas**, concebido sob uma arquitetura modular e **plug & play**. Mais do que a simples automação de tarefas, a solução estabelece uma linha de trabalho dinâmica e extensível.

A principal proposta de valor reside na sua arquitetura preparada para o crescimento contínuo. Por meio de um Orquestrador de Processos central, o ecossistema é capaz de receber dinamicamente novos agentes artificiais e integrar novas **Agent Skills** (capacidades modulares). Esta visão garante que o ambiente não seja estático; pelo contrário, permite que a organização acople novos especialistas e integre conhecimentos distribuídos para responder a novas necessidades tecnológicas, mitigando a dependência excessiva de recursos humanos isolados e reduzindo substancialmente o lead time operacional.

## 1.1 Contexto e Problema

A evolução tecnológica em grandes organizações não ocorre de forma uniforme. A execução de tarefas críticas, como a modernização de funcionalidades, exige a síntese de domínios variados. Atualmente, a integração desses ecossistemas depende de processos humanos manuais e síncronos, o que gera ambientes rígidos e difíceis de escalar.

As limitações severas incluem:

- **Gargalos de Disponibilidade e Rigidez:** dependência crítica de poucos especialistas, criando pontos únicos de falha. Quando uma nova tecnologia é introduzida, o gargalo aumenta, pois não há uma forma estruturada de acoplar esse novo conhecimento ao fluxo de trabalho.
- **Degradação de Contexto:** perda progressiva de informações vitais durante hand-offs manuais entre analistas, arquitetos e desenvolvedores.
- **Análise de Impacto Difusa:** ausência de uma visão unificada, elevando o risco de regressões, retrabalho e inconsistências arquitetônicas em sistemas interdependentes.

## 1.2 Origem da Demanda e Evidências

A demanda originou-se da análise de uma empresa brasileira de grande porte do setor de desenvolvimento de software ERP. Observou-se que a fragmentação do conhecimento não é apenas uma percepção, mas uma inconsistência estrutural da rede de desenvolvimento.

A análise detalhada da matriz de competências do time de produto permitiu identificar a severidade dessa fragmentação por meio de indicadores de lacuna (GAPs). A tabela abaixo categoriza os riscos operacionais identificados, servindo como justificativa direta para a necessidade de um ecossistema extensível de agentes.

| Categoria de Evidência | Status Identificado (Cenário Atual) | Impacto no Ciclo de Desenvolvimento | Necessidade da Solução |
|---|---|---|---|
| Concentração de Conhecimento (GAPs nos Experts) | Competências críticas dominadas por apenas um indivíduo, caracterizando ponto único de falha. | Interrupção de fluxos e aumento do lead time devido à indisponibilidade do especialista. | Acoplar agentes que emulem o conhecimento do expert para responder a consultas de baixa e média complexidade. |
| Lacuna de Prática (GAPs nos Praticantes) | Ausência de profissionais com nível inicial/intermediário em tecnologias específicas. | Sobrecarga dos especialistas e ausência de redundância técnica no time. | Agentes atuando na linha de trabalho como validadores de código para desenvolvedores em transição. |
| Isolamento de Domínio | Baixa sobreposição entre conhecimentos de negócio, processos e tecnologias legadas/modernas. | Erros de implementação e retrabalho por falta de contexto funcional ou técnico cruzado. | Orquestração dinâmica por um Project Manager artificial que coordene agentes de diferentes domínios e garanta o cumprimento de contratos técnicos. |

O detalhamento metodológico desta análise encontra-se no [Apêndice A](#apêndice-a--evidências-do-problema-detalhamento-da-matriz-de-competências-e-riscos-operacionais).

Além da análise documental da matriz de competências, a relevância prática da proposta também foi reforçada pelo interesse observado entre profissionais envolvidos em atividades de desenvolvimento, manutenção e modernização tecnológica. Esse interesse decorre, principalmente, do reconhecimento das dificuldades recorrentes associadas à interpretação de sistemas legados, à dependência de especialistas humanos específicos e à perda de contexto entre etapas do desenvolvimento.

## 1.3 Análise de Soluções Existentes (Benchmark)

Embora o mercado ofereça frameworks robustos para IA generativa, a maioria foca em automação de tarefas isoladas ou pipelines, carecendo de governança e contratos formais exigidos por ambientes corporativos.

| Solução | Pontos fortes | Limitações no contexto deste projeto |
|---|---|---|
| LangChain | Integrações, RAG e tools. | Foco maior em pipelines sequenciais do que em colaboração estruturada entre múltiplos agentes autônomos. |
| AutoGPT | Autonomia orientada a objetivos genéricos. | Baixo controle de fluxo, baixa previsibilidade e pouca adequação a ecossistemas corporativos seguros. |
| CrewAI | Simulação de equipes com papéis definidos. | Comunicação baseada em texto livre, sem contratos técnicos formais rígidos. |
| Microsoft AutoGen | Colaboração entre agentes e execução de código. | Foco acadêmico/experimental e pouca ênfase em observabilidade corporativa. |
| Gemini Code Assist / Assistentes de IDE | Aceleração do desenvolvimento individual. | Atuação como copilots individuais, não como ecossistema de orquestração de conhecimento distribuído. |

### O Diferencial da Proposta

A lacuna identificada não reside na falta de Inteligência Artificial, mas na ausência de uma arquitetura de integração robusta. Este projeto estrutura os agentes como componentes de software interoperáveis, via Arquitetura Orientada a Serviços e contratos, assegurando rastreabilidade, validação de resultados e governança técnica.

## 1.4 Público-Alvo

A solução destina-se a equipes técnicas de nível intermediário a avançado que atuam na manutenção e evolução de ecossistemas organizacionais heterogêneos.

- **Desenvolvedores de Software:** utilizam o ecossistema para acionar especialistas artificiais, como agentes de código legado, contribuindo para reduzir o esforço cognitivo e o tempo de espera na busca por contexto de regras de negócio embutidas em sistemas antigos.
- **Analistas de Sistemas:** apoiam-se na orquestração dos agentes para mitigar interpretações divergentes, validando regras funcionais e apoiando o mapeamento de processos técnicos com maior precisão.
- **Arquitetos de Software:** utilizam a visão integrada do ecossistema para apoiar decisões estruturais e análise de impacto entre sistemas interdependentes. Também atuam de forma estratégica na extensão da plataforma, definindo quais novos agentes e skills devem ser acoplados.

O sistema não é direcionado a usuários leigos, mas a profissionais com nível técnico intermediário ou avançado. Espera-se familiaridade com conceitos como APIs, integração de sistemas, leitura de código-fonte, documentação técnica, arquitetura de software e análise de impacto.

## 1.5 Objetivos e Hipóteses

### 1.5.1 Objetivo Geral

Definir e validar um modelo arquitetural escalável, modular e plug-and-play para integração e orquestração de especialistas artificiais, fundamentado em **Spec-Driven Development (SDD)**, visando estabelecer uma linha de trabalho completa e contínua para a resolução de tarefas complexas em ambientes corporativos heterogêneos.

### 1.5.2 Objetivos Específicos

1. **Especificar os Contratos de Comunicação:** mapear e padronizar interfaces de comunicação, baseadas em protocolos como MCP, para viabilizar o acoplamento dinâmico de novas Agent Skills sem dependência de fornecedores.
2. **Modelar o Motor de Orquestração:** desenvolver a lógica do componente central (Project Manager) responsável por interpretar solicitações complexas, decompor o problema em subtarefas e gerenciar a linha de trabalho dos agentes.
3. **Estruturar a Camada de Validação:** desenhar o mecanismo de validação cruzada (Software Architect e Advisory Agent) para garantir consistência técnica e qualidade das respostas parciais.
4. **Implementar e Avaliar a PoC:** construir um protótipo funcional aplicado a um cenário de análise de sistemas legados corporativos para medir o desempenho do ecossistema frente aos KPIs estabelecidos.

### 1.5.3 Hipóteses de Pesquisa

- **H1 - Eficiência Temporal:** a orquestração estruturada de agentes especialistas em uma linha de trabalho contínua contribui para reduzir o tempo de análise de processos técnicos complexos.
- **H2 - Resiliência Cognitiva:** a disponibilização e descentralização do conhecimento especializado por Agent Skills modulares e acopláveis mitiga a dependência direta de especialistas humanos isolados.
- **H3 - Qualidade e Precisão:** a validação técnica cruzada e iterativa entre diferentes domínios de especialistas artificiais amplia a precisão, completude e qualidade das recomendações analíticas consolidadas.
- **H4 - Extensibilidade e Governança:** a adoção de contratos formais rígidos e orquestração centralizada viabiliza a inclusão de novos agentes sem refatoração do núcleo, buscando assegurar rastreabilidade integral das interações e decisões registradas.

## 1.6 Métricas de Sucesso (KPIs)

| KPI | Descrição | Meta |
|---|---|---|
| Redução do Tempo de Análise | Comparação do lead time analítico tradicional vs. fluxo com agentes. | Redução >= 30% |
| Tempo de Resposta | Tempo médio de resposta nos cenários controlados da PoC, considerando fluxos sintéticos e número limitado de especialistas. | <= 10 segundos |
| Taxa de Sucesso (End-to-End) | Percentual de fluxos concluídos com respostas válidas, aprovadas pelo mecanismo de validação e sem inconsistências críticas. | >= 80% |
| Articulação de Domínios | Capacidade de integrar agentes diferentes no mesmo fluxo. | Mínimo de 3 agentes |
| Rastreabilidade | Capacidade de auditar qual agente tomou qual decisão técnica. | 100% de logs registrados |

---

# 2. Engenharia de Requisitos

Esta seção define o comportamento esperado do ecossistema de especialistas artificiais, conectando o problema da fragmentação do conhecimento às funcionalidades e restrições arquiteturais da solução.

## 2.1 Personas e Casos de Uso

| Persona | Contexto e Dificuldades | Casos de Uso Principais |
|---|---|---|
| Aragorn (Desenvolvedor) | Lida com código legado e integrações. Sofre com a perda de contexto e dependência de experts. | Submeter solicitação técnica; analisar funcionalidade legada; interpretar regra de negócio. |
| Galadriel (Analista) | Traduz requisitos de negócio. Sofre com ambiguidades e informações dispersas. | Interpretar regra de negócio; avaliar impacto de alteração. |
| Elrond (Arquiteto) | Define padrões arquiteturais. Sofre com falta de visão consolidada e dificuldade de análise de impacto global. | Solicitar recomendação arquitetural; avaliar impacto de alteração; visualizar fluxo de colaboração e rastreabilidade. |

Para ilustrar como essas interações disparam a orquestração interna entre as capacidades do sistema e as skills dos agentes, o diagrama abaixo detalha os limites do ecossistema e as relações de uso.

![Figura 1 - Diagrama de casos de uso do sistema proposto](docs/assets/figura-1-casos-de-uso.png)

**Figura 1 - Diagrama de casos de uso do sistema proposto**  
Fonte: Elaborado pela autora (2026).

## 2.2 Requisitos Funcionais (RF)

| ID | Descrição do Requisito Funcional |
|---|---|
| RF01 | O sistema deve permitir que o usuário submeta uma solicitação técnica contendo o contexto do problema, artefatos e restrições. |
| RF02 | O sistema deve interpretar a demanda, decompor o problema e coordenar dinamicamente múltiplos especialistas artificiais para resolver a solicitação. |
| RF03 | O sistema deve realizar análises técnicas delegando a execução para agentes modulares especializados. |
| RF04 | O sistema deve possuir uma interface ou registro que permita acoplar novas capacidades ou especialistas artificiais sem refatorar o núcleo de orquestração. |
| RF05 | O sistema deve permitir a visualização em tempo real do fluxo de orquestração, evidenciando quais especialistas foram acionados e como colaboraram. |
| RF06 | O sistema deve registrar e disponibilizar o histórico completo de interações, decisões e outputs gerados durante o processo. |
| RF07 | O sistema deve permitir integração contínua com plataformas externas de governança de agentes, utilizando contratos técnicos e protocolos padronizados, como MCP. |

## 2.3 Requisitos Não Funcionais (RNF)

| ID | Descrição do Requisito Não Funcional |
|---|---|
| RNF01 | O sistema deve ser modular, permitindo inclusão de novos especialistas, conectores, fontes de contexto e plataformas externas sem reestruturação do núcleo. |
| RNF02 | A integração com fontes de dados, sistemas externos e novos agentes deve ocorrer via interfaces formais e protocolos estruturados, como MCP. |
| RNF03 | A arquitetura deve suportar a adição contínua de novas Agent Skills sem degradação significativa no desempenho global. |
| RNF04 | O ecossistema deve registrar 100% das interações, validações cruzadas e decisões tomadas durante o processamento. |
| RNF05 | O tempo médio de resposta deve ser inferior a 10 segundos em fluxos analíticos com múltiplos especialistas. |
| RNF06 | O sistema deve garantir autenticação, controle de acesso e segurança no tráfego de contexto técnico sensível. |
| RNF07 | A plataforma deve manter disponibilidade adequada durante os cenários de demonstração e fornecer interface estruturada e intuitiva. |

## 2.4 Regras de Negócio

| ID | Regra de Negócio |
|---|---|
| RN01 | O ecossistema não possui permissão para executar alterações diretas em código-fonte, banco de dados ou pipelines de CI/CD. A atuação dos agentes é analítica e recomendatória. |
| RN02 | Todas as respostas e recomendações arquiteturais geradas devem referenciar catálogos e padrões técnicos pré-aprovados, acompanhadas de justificativas. |
| RN03 | O Advisory Agent detém autoridade arquitetural final e deve rejeitar respostas que violem diretrizes de negócio ou padrões de segurança. |
| RN04 | Artefatos com dados sensíveis, PII ou credenciais devem ser anonimizados ou mascarados antes do processamento, especialmente no roteamento para skills externas. |
| RN05 | A delegação de tarefas entre agentes deve respeitar um limite máximo de iterações; caso o limite seja atingido, o Orquestrador deve suspender o processamento e reportar erro. |
| RN06 | O acoplamento de novas Agent Skills ou a comunicação com plataformas externas deve ocorrer por contratos estruturados, como MCP, reduzindo vendor lock-in. |

## 2.5 Fora do Escopo

- Substituição da autoridade humana.
- Automação de CI/CD, deploys, aprovação automática de Pull Requests ou alterações ativas em produção.
- Garantia de zero alucinação nativa.
- Cobertura universal de tecnologias na PoC.

---

# 3. Arquitetura da Solução

A arquitetura proposta foi desenhada para transformar a análise técnica de ecossistemas complexos em uma linha de trabalho contínua, integrada e auditável. A solução estrutura-se como um ambiente descentralizado de microsserviços cognitivos orientados a contratos.

## 3.1 Visão Geral e Fundamentos

O ecossistema fundamenta-se na coordenação estruturada de agentes especialistas artificiais que operam sobre domínios de conhecimento historicamente fragmentados, como código legado, arquitetura corporativa e regras de negócio.

A arquitetura extensível é sustentada por quatro pilares:

1. **Engenharia de Contexto Estruturada:** o contexto deixa de ser texto livre e passa a ser tratado como ativo estruturado, via JSON Schemas.
2. **Orquestração Inteligente:** o componente central interpreta a demanda, decompõe o problema em subtarefas e coordena a colaboração entre papéis.
3. **Capacidades Modulares:** diretrizes de comportamento e integrações com tools são encapsuladas como módulos reutilizáveis e independentes.
4. **Extensibilidade Externa e Desacoplamento:** interfaces padronizadas e adaptadores agnósticos reduzem vendor lock-in.

![Figura 2 - Diagrama de contexto da arquitetura proposta (C4 - Nível 1)](docs/assets/figura-2-c4-contexto.png)

**Figura 2 - Diagrama de contexto da arquitetura proposta (C4 - Nível 1)**  
Fonte: Elaborado pela autora (2026).

## 3.2 Estrutura Arquitetural e Papéis

A arquitetura organiza o ecossistema separando coordenação operacional, execução analítica especializada e validação de qualidade.

| Camada | Papel / Componente | Responsabilidade Principal |
|---|---|---|
| Orquestração | Project Manager | Recebe a demanda técnica, interpreta a intenção do usuário, decompõe o problema e gerencia a estratégia de roteamento dinâmico. |
| Orquestração | Software Architect | Consolida análises parciais, avalia impactos estruturais e garante coerência arquitetural da entrega final. |
| Validação | Advisory Agent | Atua como Quality Gate, revisando lógicas, mitigando alucinações e emitindo parecer de aprovação ou rejeição. |
| Especialistas | Agent Skills de Negócio | Interpretam fluxos funcionais, documentações corporativas e regras de negócio tácitas ou explícitas. |
| Especialistas | Agent Skills de Legado | Mapeiam dependências, fluxos de controle e lógicas obscuras em sistemas antigos. |
| Especialistas | Agent Skills de Integração | Analisam contratos de APIs, payloads e compatibilidade de fluxos entre aplicações. |
| Integração Externa | Adaptador de Plataforma | Interface desacoplada e agnóstica para consumir novos agentes e capacidades externas. |

![Figura 3 - Diagrama de contêineres da arquitetura proposta (C4 - Nível 2)](docs/assets/figura-3-c4-conteineres.png)

**Figura 3 - Diagrama de contêineres da arquitetura proposta (C4 - Nível 2)**  
Fonte: Elaborado pela autora (2026).

## 3.3 Fluxo Cognitivo e Operacional

A dinâmica interna do sistema afasta-se de pipelines lineares e baseia-se no paradigma agêntico estruturado **ReAct (Reason + Act)**, combinado com ciclos de autoavaliação iterativa (**Self-Reflection**).

![Figura 4 - Diagrama de componentes da API de orquestração (C4 - Nível 3)](docs/assets/figura-4-c4-componentes-api.png)

**Figura 4 - Diagrama de componentes da API de orquestração (C4 - Nível 3)**  
Fonte: Elaborado pela autora (2026).

A Figura 5 ilustra o fluxo principal de processamento da solicitação técnica. A partir da entrada do usuário, o sistema estrutura o contexto, define a estratégia de orquestração, aciona os agentes especialistas, encaminha as respostas para validação transversal e consolida o resultado.

![Figura 5 - Fluxo principal de processamento](docs/assets/figura-5-fluxo-principal.png)

**Figura 5 - Fluxo principal de processamento**  
Fonte: Elaborado pela autora (2026).

### 3.3.1 Tratamento de Exceções e Fluxos Alternativos

| Situação de Risco | Descrição | Tratamento e Recuperação |
|---|---|---|
| Contexto Insuficiente | Prompt original não possui artefatos ou clareza mínima. | Orquestrador solicita refinamento do contexto ao usuário. |
| Respostas Divergentes | Especialistas geram recomendações conflitantes. | Acionamento automático do Conselheiro para desempate lógico ou escalonamento humano. |
| Falha de Contrato | Mensagem via MCP devolvida fora do contrato JSON exigido. | Rejeição imediata, log de erro estrutural e retentativa orientada. |
| Baixa Confiança | Incerteza cognitiva do agente ao inferir lógicas obscuras. | Flag de baixa confiabilidade na resposta final e indicação de revisão humana. |

## 3.4 Princípios e Alinhamento ao Spec-Driven Development (SDD)

O comportamento dos nós do ecossistema é orientado e limitado por especificações contratuais preestabelecidas, como schemas de API e contratos MCP.

- A demanda técnica é tratada como uma especificação.
- Os agentes operam por fronteiras explícitas, encapsulados por System Prompts limitadores.
- A base contratual viabiliza a escalabilidade do ecossistema e a inclusão futura de novos domínios tecnológicos.

---

# 4. Mockups e Experiência do Usuário (UX)

## 4.1 Visão Geral e Fluxo de Navegação

A interface do usuário atua como painel de controle do ecossistema de especialistas. Considerando que o sistema é voltado a um público técnico, a UI prioriza clareza, objetividade e transparência das informações.

![Figura 6 - Diagrama unificado de fluxo de navegação do usuário](docs/assets/figura-6-fluxo-navegacao.png)

**Figura 6 - Diagrama unificado de fluxo de navegação do usuário**  
Fonte: Elaborado pela autora (2026).

## 4.2 Estrutura das Interfaces (Wireframes)

| Tela | Objetivo na Jornada do Usuário | Ações Principais |
|---|---|---|
| Login | Garantir acesso restrito ao ambiente. | Autenticação via SSO ou credenciais. |
| Dashboard | Prover visão centralizada da operação e saúde do ecossistema. | Visualizar status de análises, métricas e Agent Skills online/acopladas. |
| Nova Solicitação Técnica | Ponto de entrada do contexto. | Inserir problema, contexto, artefatos técnicos e escopo analítico. |
| Acompanhamento | Prover transparência sobre o fluxo dinâmico dos agentes. | Visualizar linha do tempo, especialistas acionados e validações. |
| Resposta Consolidada | Apresentar síntese estruturada aprovada pelo Quality Gate. | Consultar recomendações, riscos e copiar a saída consolidada. |
| Histórico e Rastreabilidade | Permitir auditoria técnica e reaproveitamento do conhecimento. | Filtrar solicitações e auditar decisões. |

As Figuras E.1 a E.7, que representam os mockups detalhados, encontram-se no [Apêndice E](#apêndice-e--protótipos-e-telas-complementares-uiux).

## 4.3 Fluxo de Interação do Usuário

O fluxo de interação descreve como as telas se articulam durante a utilização da aplicação, desde o acesso inicial até a consulta posterior da rastreabilidade. O cenário principal considera um usuário técnico submetendo uma solicitação relacionada à análise de uma funcionalidade existente em sistema legado.

A interação inicia-se na autenticação, segue para o dashboard, avança para a tela de nova solicitação técnica, passa pelo acompanhamento da orquestração, chega à resposta consolidada e permanece disponível no histórico e rastreabilidade.

## 4.4 Feedback Inicial de Usuários

Após a elaboração dos wireframes e do fluxo de interação, foi realizada uma avaliação inicial qualitativa com usuários representativos. O objetivo foi verificar se a experiência proposta estava coerente com as necessidades do público-alvo e se as telas permitiam compreender o funcionamento do ecossistema.

Os participantes reconheceram valor na possibilidade de acompanhar o processo de orquestração, em vez de receber apenas uma resposta final sem explicação do caminho percorrido. Também foi destacada a importância da tela de histórico e rastreabilidade em cenários corporativos nos quais decisões técnicas precisam ser auditadas, reaproveitadas ou justificadas posteriormente.

---

# 5. Modelagem Técnica e Implementação da PoC

Esta seção delimita como os fundamentos arquiteturais serão implementados em ambiente controlado por meio de uma Prova de Conceito (PoC).

## 5.1 Escopo da Prova de Conceito

A PoC focará em um caminho feliz representativo: análise de impacto e documentação de uma funcionalidade em ecossistema legado.

| Etapa do Fluxo | Componente / Agente Acionado | Ação Esperada na PoC |
|---|---|---|
| Entrada | Interface Web | Submissão de código legado e contexto de negócio em formato estruturado. |
| Orquestração | Project Manager | Geração do Trace ID, decomposição da intenção e roteamento via contratos MCP. |
| Análise 1 | Agent Skill de Código Legado | Identificação de lógicas obscuras e dependências no código. |
| Análise 2 | Agent Skill de Regras de Negócio | Extração e tradução de regras funcionais implícitas. |
| Análise 3 | Agent Skill de Arquitetura | Avaliação de impacto e recomendação de estratégias de modernização. |
| Validação | Advisory Agent | Revisão cruzada em busca de alucinações, conflitos lógicos ou quebras de contrato. |
| Saída | Consolidador de Respostas | Entrega de artefato final em JSON/Markdown, unificado e auditável. |

## 5.2 Conjunto Tecnológico (Stack)

| Camada | Tecnologia Escolhida | Justificativa |
|---|---|---|
| Frontend / UX | React.js / TypeScript | SPA reativa para observabilidade em tempo real. |
| Backend / API | Python / FastAPI | Ecossistema nativo para IA e processamento assíncrono. |
| Motor de Orquestração | Camada própria em Python | Implementação do fluxo de orquestração com validação por contratos e regras próprias. |
| Banco de Dados | PostgreSQL | Persistência relacional para integridade entre requests, logs e contextos. |
| Comunicação e Contratos | HTTP/REST e MCP | Comunicação padronizada entre frontend, backend, agentes e contratos estruturados. |

## 5.3 Modelo de Dados

Como a governança é um pilar estrutural da solução, o banco de dados relacional foi modelado para assegurar que a resposta final nunca perca o vínculo de rastreabilidade com o prompt inicial e com os logs transicionais.

O detalhamento do modelo conceitual encontra-se na Figura D.1 no [Apêndice D](#apêndice-d--modelagem-de-dados-e-arquitetura-de-componentes).

Entidades centrais:

- **Solicitação Técnica:** tabela agregadora que gera o Trace ID único para a sessão.
- **Contexto:** armazena o payload inicial e as camadas de enriquecimento.
- **Interação (Logs):** registra cada passo atômico do roteamento.
- **Resposta Parcial e Validação:** isola outputs individuais de cada agente e armazena o parecer técnico do Conselheiro.

## 5.4 Critérios de Avaliação e Limitações

A avaliação técnica do sucesso da PoC será baseada no alcance das metas definidas pelos KPIs, focando em redução de tempo de análise, taxa de sucesso e rastreabilidade.

Delimitações:

1. Atuação read-only.
2. LLMs mockados ou modelos menores para reduzir custo de inferência.
3. Ambiente de teste sintético com bases de dados sintéticas ou códigos open-source.

---

# 6. Segurança, Governança e Privacidade

A adoção de especialistas artificiais em ambientes corporativos exige controle rigoroso sobre o fluxo de informações. O ecossistema trata segurança e governança como requisitos transversais de design.

## 6.1 Segurança da Arquitetura

| Princípio de Controle | Aplicação na Arquitetura | Mitigação de Risco |
|---|---|---|
| Autenticação e Acesso | Login obrigatório, tokens e isolamento por usuário. | Prevenção contra acesso não autorizado. |
| Restrição de Domínio | Contratos rígidos; agentes atuam exclusivamente em seu escopo. | Evita sobreposição de papéis e decisões fora da especialidade. |
| Validação Cruzada | Advisory Agent como Quality Gate obrigatório. | Mitigação de inconsistências e respostas contraditórias. |
| Proteção de Contexto | Fragmentação inteligente do payload. | Reduz exposição desnecessária de dados aos modelos. |
| Ação Read-Only | Bloqueio para ações autônomas destrutivas. | Garante human-in-the-loop em decisões críticas. |

## 6.2 Observabilidade e Rastreabilidade (Auditoria)

- **Trace ID Único:** toda solicitação recebe um identificador global que transita por toda a cadeia de delegação.
- **Logs Estruturados e Contratos:** registro obrigatório de timestamps, contratos de entrada/saída, quebras de schema e status de confiança.
- **Isolamento de Falhas:** se um agente externo falhar, o Orquestrador isola a requisição, registra a anomalia e devolve erro controlado.

## 6.3 Privacidade de Dados e Conformidade (LGPD)

| Categoria do Dado | Exemplo | Finalidade e Base Legal Conceitual |
|---|---|---|
| Dados de Usuário | Nome, e-mail corporativo, credenciais. | Autenticação, gestão de acessos e rastreabilidade individual. |
| Dados Técnicos | Regras de negócio, snippets de código-fonte, arquitetura. | Insumo para análise cognitiva; anonimização obrigatória de PII embutida. |
| Metadados (Logs) | IP, timestamps, rotas, latência. | Auditoria, observabilidade, prevenção de fraudes e manutenção preditiva. |

---

# 7. Planejamento do Projeto

O desenvolvimento metodológico apoia-se em abordagem incremental fundamentada em metodologias ágeis. A gestão do escopo, rastreamento das tarefas e governança documental são conduzidos através de quadros Kanban no Jira.

## 7.1 Estratégia de Planejamento e Gestão

![Figura 7 - Roadmap do projeto e evolução das etapas do TCC](docs/assets/figura-7-roadmap.png)

**Figura 7 - Roadmap do projeto e evolução das etapas do TCC**  
Fonte: Elaborado pela autora (2026).

| Marco | Etapa do Projeto | Descrição Estratégica | Entregáveis Principais |
|---|---|---|---|
| M1 | Fundamentação e Visão do Produto | Consolidação do problema, benchmark, objetivos e KPIs. | Problema validado, benchmark, objetivos e hipóteses. |
| M2 | Engenharia de Requisitos | Mapeamento das interações dos usuários e definição de RFs, RNFs e regras. | Personas, casos de uso, RFs/RNFs e regras consolidadas. |
| M3 | Concepção Arquitetural | Modelagem do ecossistema distribuído e adoção do MCP. | Diagramas C4, fundamentos técnicos e design system. |
| M4 | UX e Prototipação | Fluxo de observabilidade, wireframes e avaliação inicial. | Fluxograma, wireframes e feedback inicial. |
| M5 | Modelagem Técnica da PoC | Delimitação do Happy Path, stack e modelo de dados. | Escopo de validação, stack e MER/DER. |
| M6 | Implementação da PoC | Codificação do motor de orquestração, skills e Quality Gate. | Protótipo funcional, APIs e banco instanciado. |
| M7 | Validação e Avaliação | Execução de testes e medição dos KPIs. | Evidências de execução, métricas e análise de viabilidade. |
| M8 | Consolidação Acadêmica | Revisão final, apêndices e preparação da defesa. | RFC final, slides de defesa e repositórios. |

---

# 8. Referências

## Livros e Capítulos de Livros

RUSSELL, Stuart J.; NORVIG, Peter. *Artificial intelligence: a modern approach*. 4. ed. Upper Saddle River: Pearson, 2020.

WOOLDRIDGE, Michael. *An introduction to multiagent systems*. 2. ed. Chichester: John Wiley & Sons, 2009.

ERL, Thomas. *Service-Oriented Architecture: Concepts, Technology, and Design*. Upper Saddle River: Prentice Hall, 2005.

TAULLI, Tom; DESHMUKH, Gaurav. CrewAI. In: TAULLI, Tom; DESHMUKH, Gaurav. *Building Generative AI Agents: Using LangGraph, AutoGen, and CrewAI*. Berkeley, CA: Apress, 2025. p. 103-145.

## Teses e Dissertações

NASCIMENTO, Arthur Henrique Casals do. *Engenharia de SMA: integrando sistemas distribuídos e avanços em Inteligência Artificial*. 2024. Tese (Doutorado em Engenharia de Computação) - Escola Politécnica, Universidade de São Paulo, São Paulo, 2024.

QUESADA, Christian Jhulian Braga. *Inteligência artificial: a relevância para a arquitetura*. 2024. Tese (Doutorado em Arquitetura e Urbanismo) - Faculdade de Arquitetura e Urbanismo, Universidade de São Paulo, São Paulo, 2024.

## Artigos e Trabalhos Acadêmicos

IABAGATA, Tatiana Yukari Sekiya et al. Aplicação de ferramentas baseadas em inteligência artificial para minimização de desafios e otimização de processos na engenharia de software. [S. l.: s. n.], 2025.

SILVA, Rui. Interoperabilidade em sistemas multiagentes: princípios éticos e morais na inteligência artificial. [S. l.: s. n.], 2024.

WALKER, Clinton et al. Forensic Analysis of Artifacts from Microsoft’s Multi-Agent LLM Platform AutoGen. In: INTERNATIONAL CONFERENCE ON AVAILABILITY, RELIABILITY AND SECURITY, 19., 2024. Proceedings [...]. [S. l.]: ACM, 2024. p. 1-9.

YANG, Hui; YUE, Sifu; HE, Yunzhong. Auto-GPT for online decision making: benchmarks and additional opinions. *arXiv preprint arXiv:2306.02224*, 2023.

BRITO, Erick Roberto Furst. Projeto e implantação de agentes de inteligência artificial plug-and-play utilizando arquiteturas serverless. *Lumen et Virtus*, v. 17, n. 56, p. e11798-e11798, 2026.

PAPAZOGLOU, Mike P.; GEORGAKOPOULOS, Dimitrios. Service-oriented computing. *Communications of the ACM*, 2003.

PERREY, Randall; LYCETT, Mark. Service-oriented architecture. In: SYMPOSIUM ON APPLICATIONS AND THE INTERNET WORKSHOPS, 2003. Proceedings [...]. IEEE, 2003. p. 116-119.

## Leis e Normas

BRASIL. Lei nº 13.709, de 14 de agosto de 2018. Lei Geral de Proteção de Dados Pessoais (LGPD). Brasília, DF: Presidência da República, 2018. Disponível em: https://www.planalto.gov.br/ccivil_03/_Ato2015-2018/2018/Lei/L13709.htm. Acesso em: 23 maio 2026.

## Documentação Técnica e Sites

LANGCHAIN. LangChain Documentation. [S. l.]: LangChain, 2026. Disponível em: https://docs.langchain.com/. Acesso em: 23 maio 2026.

MODEL CONTEXT PROTOCOL. What is the Model Context Protocol (MCP)? 2026. Disponível em: https://modelcontextprotocol.io/docs/getting-started/intro. Acesso em: 23 maio 2026.

MICROSOFT. AutoGen Documentation. 2024. Disponível em: https://microsoft.github.io/autogen/stable/. Acesso em: 23 maio 2026.

CREWAI. CrewAI Documentation. 2026. Disponível em: https://docs.crewai.com/. Acesso em: 23 maio 2026.

SIGNIFICANT GRAVITAS. AutoGPT: Build, Deploy, and Run AI Agents. GitHub, 2026. Disponível em: https://github.com/Significant-Gravitas/AutoGPT. Acesso em: 23 maio 2026.

GOOGLE CLOUD. Gemini Code Assist Standard and Enterprise overview. Google Cloud Documentation, 2026. Disponível em: https://docs.cloud.google.com/gemini/docs/codeassist/overview. Acesso em: 23 maio 2026.

FASTAPI. FastAPI Documentation. 2026. Disponível em: https://fastapi.tiangolo.com/. Acesso em: 23 maio 2026.

POSTGRESQL GLOBAL DEVELOPMENT GROUP. PostgreSQL Documentation. 2026. Disponível em: https://www.postgresql.org/docs/. Acesso em: 23 maio 2026.

REACT. React Documentation. 2026. Disponível em: https://react.dev/. Acesso em: 23 maio 2026.

MICROSOFT. TypeScript Documentation. 2026. Disponível em: https://www.typescriptlang.org/docs/. Acesso em: 23 maio 2026.

OPENAI. ChatGPT. 2026. Disponível em: https://chatgpt.com/. Acesso em: 23 maio 2026.

---

# 9. Apêndices e Materiais Complementares

Os apêndices reúnem artefatos visuais, detalhamentos teóricos e evidências práticas que fundamentam as decisões arquiteturais apresentadas no corpo deste RFC.

## Apêndice A - Evidências do Problema: Detalhamento da Matriz de Competências e Riscos Operacionais

A evidência empírica que originou este projeto foi obtida por meio da análise documental qualitativa de uma matriz de competências de um time de produto atuante no desenvolvimento de um sistema ERP corporativo.

![Figura A.1 - Matriz de competência anonimizada](docs/assets/figura-a1-matriz-competencia.png)

**Figura A.1 - Matriz de competência anonimizada**  
Fonte: Elaborado pela autora (2026).

## Apêndice B - Estudo Aprofundado de Ferramentas Multiagentes (Benchmark)

A concepção da arquitetura exigiu a avaliação crítica das soluções de inteligência generativa disponíveis no mercado. A lacuna metodológica identificada não está na falta de modelos de linguagem inteligentes, mas na ausência de um padrão arquitetural que aplique princípios de Governança e Arquitetura Orientada a Serviços ao roteamento de agentes.

## Apêndice C - Contratos de Comunicação e Especificações Técnicas (MCP)

Este apêndice documenta schemas JSON e especificações dos contratos baseados no paradigma do Model Context Protocol.

![Figura C.1 - Diagrama de comunicação via MCP e contratos técnicos](docs/assets/figura-c1-mcp-contratos.png)

**Figura C.1 - Diagrama de comunicação via MCP e contratos técnicos**  
Fonte: Elaborado pela autora (2026).

### Schema de Entrada: `solicitacao_analise_schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SolicitacaoAnaliseTecnica",
  "description": "Contrato rígido para submissão de demandas de análise técnica no ecossistema.",
  "type": "object",
  "properties": {
    "trace_id": {
      "description": "Identificador único global da sessão para fins de rastreabilidade (UUID v4).",
      "type": "string",
      "pattern": "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "usuario_id": { "type": "string" },
        "timestamp_criacao": { "type": "string", "format": "date-time" },
        "sistema_origem": { "type": "string", "example": "ERP-Financeiro" }
      },
      "required": ["usuario_id", "timestamp_criacao"]
    },
    "contexto_negocio": {
      "description": "Detalhamento funcional da regra de negócio ou processo técnico associado.",
      "type": "string",
      "minLength": 10
    },
    "artefatos": {
      "description": "Lista de componentes técnicos, códigos ou documentações submetidos para varredura.",
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "properties": {
          "nome_arquivo": { "type": "string", "example": "stateSon.js" },
          "tipo_artefato": { "type": "string", "enum": ["codigo_fonte", "documentacao_api", "requisito_funcional"] },
          "conteudo": { "type": "string", "description": "Conteúdo bruto ou trecho de código isolado." },
          "linguagem": { "type": "string", "example": "javascript" }
        },
        "required": ["nome_arquivo", "tipo_artefato", "conteudo"]
      }
    },
    "escopo_analise": {
      "type": "object",
      "properties": {
        "analises_requeridas": {
          "type": "array",
          "items": { "type": "string", "enum": ["legado", "negocio", "arquitetura", "impacto"] }
        },
        "profundidade": { "type": "string", "enum": ["superficial", "detalhada"], "default": "detalhada" }
      },
      "required": ["analises_requeridas"]
    }
  },
  "required": ["trace_id", "metadata", "contexto_negocio", "artefatos", "escopo_analise"],
  "additionalProperties": false
}
```

### Schema de Saída Intermediária/Final: `resposta_especialista_schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "RespostaEspecialistaArtificil",
  "description": "Contrato de saída estruturada para tráfego via MCP entre especialistas e orquestradores.",
  "type": "object",
  "properties": {
    "trace_id": { "type": "string" },
    "agente_emissor": {
      "type": "object",
      "properties": {
        "nome": { "type": "string", "example": "Agent-Skill-Codigo-Legado" },
        "versao_prompt": { "type": "string", "example": "v1.4.2" },
        "dominio": { "type": "string", "enum": ["codigo_legado", "regras_negocio", "arquitetura_software"] }
      },
      "required": ["nome", "dominio"]
    },
    "analise_estruturada": {
      "type": "object",
      "properties": {
        "resumo_executivo": { "type": "string" },
        "descobertas_tecnicas": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "item_identificado": { "type": "string" },
              "descricao_detalhada": { "type": "string" },
              "trecho_referenciado": { "type": "string", "description": "Snippet de código ou texto associado à descoberta." }
            },
            "required": ["item_identificado", "descricao_detalhada"]
          }
        },
        "impactos_mapeados": {
          "type": "array",
          "items": { "type": "string", "description": "Riscos de regressão ou acoplamentos identificados." }
        }
      },
      "required": ["resumo_executivo", "descobertas_tecnicas", "impactos_mapeados"]
    },
    "governanca": {
      "type": "object",
      "properties": {
        "nivel_confianca": { "type": "string", "enum": ["ALTO", "MEDIO", "BAIXO"] },
        "justificativa_confianca": { "type": "string" },
        "referencias_catalogo": {
          "type": "array",
          "items": { "type": "string", "description": "Padrões arquiteturais oficiais referenciados." }
        }
      },
      "required": ["nivel_confianca", "justificativa_confianca"]
    }
  },
  "required": ["trace_id", "agente_emissor", "analise_estruturada", "governanca"],
  "additionalProperties": false
}
```

## Apêndice D - Modelagem de Dados e Arquitetura de Componentes

Apresenta-se a visão de persistência relacional e a topologia de classes/componentes da solução.

![Figura D.1 - Modelo conceitual de dados da prova de conceito (MER/DER)](docs/assets/figura-d1-mer-der.png)

**Figura D.1 - Modelo conceitual de dados da prova de conceito (MER/DER)**  
Fonte: Elaborado pela autora (2026).

## Apêndice E - Protótipos e Telas Complementares (UI/UX)

Conforme referenciado na Seção 4.2, este espaço destina-se ao registro visual dos protótipos de média/alta fidelidade.

![Figura E.1 - Wireframe da tela inicial](docs/assets/figura-e1-tela-inicial.png)

**Figura E.1 - Wireframe da tela inicial**  
Fonte: Elaborado pela autora (2026).

![Figura E.2 - Wireframe da tela de Login](docs/assets/figura-e2-login.png)

**Figura E.2 - Wireframe da tela de Login**  
Fonte: Elaborado pela autora (2026).

![Figura E.3 - Wireframe do Dashboard](docs/assets/figura-e3-dashboard.png)

**Figura E.3 - Wireframe do Dashboard**  
Fonte: Elaborado pela autora (2026).

![Figura E.4 - Wireframe da tela de Nova Solicitação Técnica](docs/assets/figura-e4-nova-solicitacao.png)

**Figura E.4 - Wireframe da tela de Nova Solicitação Técnica**  
Fonte: Elaborado pela autora (2026).

![Figura E.5 - Wireframe da tela de Acompanhamento da Orquestração](docs/assets/figura-e5-acompanhamento.png)

**Figura E.5 - Wireframe da tela de Acompanhamento da Orquestração**  
Fonte: Elaborado pela autora (2026).

![Figura E.6 - Wireframe da tela de Resposta Consolidada](docs/assets/figura-e6-resposta-consolidada.png)

**Figura E.6 - Wireframe da tela de Resposta Consolidada**  
Fonte: Elaborado pela autora (2026).

![Figura E.7 - Wireframe da tela de Histórico e Rastreabilidade](docs/assets/figura-e7-historico-rastreabilidade.png)

**Figura E.7 - Wireframe da tela de Histórico e Rastreabilidade**  
Fonte: Elaborado pela autora (2026).

## Apêndice F - Gestão Ágil e Rastreabilidade do Projeto

Em conformidade com a Seção 7, constam abaixo evidências extraídas da ferramenta de gestão Jira.

![Figura F.1 - Quadro Kanban utilizado para gestão ágil do projeto](docs/assets/figura-f1-kanban-jira.png)

**Figura F.1 - Quadro Kanban utilizado para gestão ágil do projeto**  
Fonte: Elaborado pela autora (2026).

---

# 10. Parecer do Comitê de Avaliação

## Avaliador 1

**Status:** [ ] Aprovado [ ] Ajustar  
**Observações:**

---

## Avaliador 2

**Status:** [ ] Aprovado [ ] Ajustar  
**Observações:**

---

## Avaliador 3

**Status:** [ ] Aprovado [ ] Ajustar  
**Observações:**

