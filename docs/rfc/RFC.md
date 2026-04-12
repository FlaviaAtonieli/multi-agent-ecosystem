# RFC: Request for Comments — Projeto de Portfólio

**Engenharia de Software – Católica SC**

---

# Identificação

- **Título do Projeto:**  
  Arquitetura de Integração de Agentes Especialistas em Ambientes Corporativos Complexos

- **Linha do Projeto (Direction):**  
  Inteligência Artificial / Arquitetura de Software / Sistemas Distribuídos

- **Autor:**  
  Flavia Antonioli de Souza

- **Data da Proposta:**  
  <!-- preencher -->

- **Versão:**  
  1.0

---

Joinville  
2026

---

# 1. Visão do Produto e Impacto (O Problema)

Este cenário investiga um desafio crítico em ambientes corporativos de software: a fragmentação do conhecimento entre diferentes especialistas, tecnologias e domínios de negócio durante a execução de tarefas complexas. Essa dificuldade é acentuada em ecossistemas de grande porte, como os de plataformas de gestão empresarial (ERP), nos quais coexistem sistemas legados, arquiteturas modernas e diversas linguagens e frameworks.

Nessa situação, o desenvolvimento de funcionalidades deixa de ser uma tarefa puramente técnica para se tornar um desafio de integração. O gargalo central, portanto, não reside apenas na implementação do código, mas na necessidade de orquestrar conhecimentos distribuídos entre desenvolvedores, de diferentes gerações tecnológicas.

Como consequência direta dessa fragmentação, observam-se impactos negativos recorrentes, tais como o aumento no tempo de entrega (*lead time*), a dependência excessiva de especialistas isolados, a perda de contexto operacional e o retrabalho gerado por falhas de comunicação.

Neste contexto, propõe-se o desenvolvimento de uma arquitetura baseada em agentes especialistas. A solução consiste em agentes de software que representam domínios de conhecimento distintos e colaboram entre si via contratos técnicos e protocolos de comunicação, visando reduzir a dispersão de informações e otimizar a produtividade em ambientes corporativos complexos.

---

## 1.1 Contexto e Problema

O desenvolvimento de software em organizações de grande porte opera sob o paradigma de ecossistemas heterogêneos. Nesses cenários, a evolução tecnológica não ocorre de forma uniforme, resultando em um ambiente composto por sistemas legados monolíticos, microserviços modernos, regras de negócio ricas, porém distribuídas, e silos de especialização técnica.

A execução de tarefas críticas, como a modernização de funcionalidades ou a integração de fluxos complexos, exige uma síntese de domínios. Atualmente, para implementar uma única funcionalidade, é necessário orquestrar conhecimentos que variam da interpretação de lógica em linguagens legadas à arquitetura de interfaces contemporâneas, passando por validações funcionais rigorosas.

### O Gargalo da Integração Humana

Atualmente, a integração desses domínios depende quase exclusivamente de processos manuais e síncronos, os quais apresentam limitações significativas no contexto de ambientes corporativos complexos. Essas limitações podem ser observadas, principalmente, nos seguintes aspectos:

- **Consultas específicas:** dependência crítica de especialistas detentores de conhecimento especializado, gerando gargalos de disponibilidade.
- **Transferências de Contexto Ineficientes (*Hand-offs*):** a transferência de contexto entre analistas, arquitetos e desenvolvedores resulta em uma degradação progressiva da informação, caracterizando o efeito "telefone sem fio".
- **Análise de Impacto Difusa:** a falta de uma visão unificada sobre o impacto de mudanças em sistemas interdependentes eleva o risco de regressões e retrabalho.

### A Lacuna Estrutural

O problema central não é a falta de conhecimento, mas a sua fragmentação. Em projetos de modernização, o custo de "redescobrir" a regra de negócio embutida no legado frequentemente supera o custo da nova implementação. A ausência de um mecanismo que capture, interprete e integre esses fragmentos de forma estruturada cria um ambiente de alta carga cognitiva e baixa previsibilidade.

Dessa forma, identifica-se a necessidade de uma solução que transcenda a simples busca de informações, atuando na orquestração autônoma do conhecimento especializado para garantir a consistência funcional e arquitetural ao longo de todo o ciclo de vida do desenvolvimento de software.

O conceito de agentes de software é amplamente discutido na literatura de Inteligência Artificial e Sistemas Distribuídos. Segundo Russell e Norvig (2020), na obra *Artificial Intelligence: A Modern Approach*, agentes são entidades capazes de perceber o ambiente, tomar decisões e executar ações com o objetivo de atingir determinados resultados.

De acordo com Stuart Russell e Peter Norvig, um agente pode ser definido como qualquer entidade que percebe seu ambiente por meio de sensores e atua sobre esse ambiente por meio de atuadores, buscando maximizar a realização de seus objetivos (RUSSELL; NORVIG, 2020).

No contexto dos sistemas multiagentes, Michael Wooldridge (2009) os define como sistemas compostos por múltiplas entidades autônomas que interagem entre si, podendo cooperar ou competir, com o objetivo de resolver problemas complexos demais para serem tratados por um único agente.

Aplicando esses conceitos ao contexto deste trabalho, os agentes especialistas podem ser compreendidos como entidades de software que representam domínios específicos de conhecimento, como regras de negócio, código legado ou arquitetura, e, quando integrados, formam um sistema multiagente capaz de colaborar para resolver tarefas complexas em ambientes corporativos.

---

## 1.2 Origem da Demanda e Evidências

O desenvolvimento deste projeto não surge apenas de interesse acadêmico, mas a partir da observação de problemas reais relacionados ao desenvolvimento de software em ambientes corporativos complexos. Para fundamentar a relevância prática do problema investigado, nesta seção é apresentada a origem da demanda e as evidências coletadas que justificam a realização deste trabalho.

Com o objetivo de preservar o sigilo organizacional, os dados apresentados foram anonimizados e sintetizados, mantendo apenas as informações necessárias para a caracterização do problema e sua análise sob a perspectiva acadêmica.

### 1.2.1 Demanda Externa

#### Organização

O projeto foi contextualizado a partir da análise de uma empresa brasileira de grande porte do setor de desenvolvimento de software de gestão empresarial, que possui um ecossistema tecnológico composto por diversos sistemas, aplicações modernas e diferentes módulos de negócio integrados.

#### Contexto da Demanda

No ambiente analisado, são frequentes atividades relacionadas à manutenção de sistemas legados, modernização tecnológica, conversão de interfaces, integração entre backend e frontend e validações funcionais e técnicas em múltiplas etapas do processo.

Essas atividades exigem conhecimento distribuído entre diferentes especialistas, como desenvolvedores de tecnologias legadas e modernas, analistas de negócio e arquitetos de software.

#### Problema Relatado

A demanda identificada pode ser sintetizada nos seguintes pontos:

- Fragmentação de conhecimento entre especialistas
- Dependência de profissionais específicos para determinadas tecnologias
- Dificuldade na interpretação de regras de negócio implícitas em sistemas legados
- Perda de contexto entre etapas do desenvolvimento
- Retrabalho decorrente de desalinhamentos técnicos
- Aumento do tempo de desenvolvimento

### 1.2.2 Pesquisa com Usuários

#### Metodologia

A evidência empírica foi obtida por meio de análise documental qualitativa de uma matriz de competências de um time de produto, com o objetivo de compreender como o conhecimento técnico e de negócio está distribuído dentro da equipe.

#### Resultados Observados

A análise da matriz de competências revelou os seguintes padrões:

| Evidência Observada | Descrição |
|---|---|
| Concentração de conhecimento | Tecnologias críticas dominadas por poucos profissionais |
| Separação entre tecnologias | Baixa sobreposição entre tecnologias legadas e modernas |
| Conhecimento de negócio | Regras de negócio dominadas por poucos especialistas |
| Fragmentação entre áreas | Nenhum profissional domina negócios, processos e tecnologias de legado e modernas ao mesmo tempo |

Esses padrões indicam dependência de especialistas e necessidade constante de comunicação para integração de conhecimento.

### 1.2.3 Evidência Concreta do Problema

A análise da matriz de competências demonstra que a fragmentação do conhecimento é uma característica estrutural da equipe, e não apenas uma percepção subjetiva. A execução de tarefas complexas exige integração constante e transferência manual de contexto, o que demanda um contínuo realinhamento de expectativas e normas entre os envolvidos. Como consequência, observa-se um elevado esforço de coordenação, maior risco de interpretações divergentes e potenciais inconsistências na execução das atividades.

#### 1.2.3.1 Detalhamento da Matriz de Competências e Riscos Operacionais

A análise detalhada da matriz de competências do time de produto permitiu identificar a severidade da fragmentação do conhecimento por meio de indicadores de lacuna (*gaps*). A tabela abaixo categoriza os riscos identificados, servindo como base para a definição das responsabilidades dos agentes especialistas na arquitetura proposta:

| Categoria de Evidência | Status Identificado (2026) | Impacto no Ciclo de Desenvolvimento | Necessidade da Solução |
|---|---|---|---|
| Gargalo em Especialistas (Experts) | Competências críticas dominadas por apenas um indivíduo (ponto único de falha) | Interrupção de fluxos e aumento do *lead time* devido à indisponibilidade de especialistas | Agentes capazes de emular o conhecimento do expert para consultas de baixa e média complexidade |
| Gaps de Prática (Praticantes) | Ausência de profissionais com nível inicial e intermediário em tecnologias específicas | Sobrecarga dos especialistas e falta de redundância técnica no time | Agentes atuando como tutores ou validadores técnicos para desenvolvedores em transição |
| Isolamento de Domínio | Baixa sobreposição entre conhecimentos de negócio, processos e tecnologias | Erros de implementação por falta de contexto funcional ou técnico cruzado | Orquestração de agentes que garantam o cumprimento de contratos técnicos entre domínios distintos |

#### Análise dos GAPs Estruturais

A análise documental revelou que a organização apresenta um cenário de "GAPs nos Experts" em áreas fundamentais, o que significa que o conhecimento mais profundo sobre o sistema não está apenas fragmentado, mas em risco de perda ou inacessibilidade. Além disso, a recorrência de "GAPs nos Praticantes" indica uma barreira de entrada alta para novos desenvolvedores em domínios legados ou complexos.

Esse cenário ratifica que a integração humana manual, através de reuniões e consultas a especialistas, é insuficiente para sustentar a escala de um ERP complexo. A arquitetura de agentes proposta surge, portanto, como uma camada de resiliência cognitiva, em que os agentes de IA especialistas reduzem a dependência direta dos experts humanos, permitindo que estes se concentrem em tarefas de alta complexidade enquanto a IA orquestra o conhecimento distribuído.

### 1.2.4 Evidência de Interesse

A relevância prática da solução foi reforçada por:

- Interesse de profissionais na proposta de agentes especialistas
- Reconhecimento da dificuldade em tarefas de modernização tecnológica
- Validação conceitual inicial da proposta

---

## 1.3 Análise de Soluções Existentes (Benchmark)

Com o avanço dos modelos de linguagem e da inteligência artificial generativa, surgiram diversas plataformas e frameworks voltados para a criação de agentes inteligentes e sistemas multiagentes. Essas soluções buscam permitir que executem tarefas, utilizem ferramentas externas, acessem bases de conhecimento e, em alguns casos, colaborem entre si para resolver problemas mais complexos.

Embora essas soluções permitam a criação de agentes e até mesmo a comunicação entre eles, dentro de um mesmo ecossistema, muitas delas não foram projetadas com foco em ambientes corporativos complexos, nos quais são necessários requisitos adicionais, como integração estruturada, contratos técnicos, governança, segurança, rastreabilidade e entendimento referente a sistemas legados.

A seguir são apresentadas algumas das principais soluções existentes relacionadas a agentes e sistemas multiagente.

### 1.3.1 LangChain

- **Nome do produto:** LangChain
- **Link:** https://www.langchain.com/
- **Público-alvo:** Desenvolvedores de aplicações baseadas em LLM, chatbots, sistemas de automação, aplicações com Retrieval Augmented Generation (RAG) e sistemas que utilizam modelos de linguagem integrados a ferramentas externas.

**Funcionalidades principais:**

- Criação de agentes baseados em modelos de linguagem
- Integração com ferramentas externas (*tools*), APIs e bancos de dados
- Implementação de RAG (*Retrieval Augmented Generation*)
- Memória de conversação
- Criação de fluxos e pipelines de processamento com LLM
- Orquestração de chamadas para modelos de linguagem

**Limitações:**

- Foco maior em pipelines de execução do que em colaboração estruturada entre múltiplos agentes especialistas
- Comunicação entre agentes baseada em troca de mensagens, sem contratos técnicos formais
- Pouco foco em governança, segurança e isolamento entre agentes
- Não é uma arquitetura pensada especificamente para ambientes corporativos complexos

### 1.3.2 AutoGPT

- **Nome do produto:** AutoGPT
- **Link:** https://github.com/Significant-Gravitas/AutoGPT
- **Público-alvo:** Pesquisadores, desenvolvedores e entusiastas de agentes autônomos e automação baseada em IA.

**Funcionalidades principais:**

- Execução autônoma de tarefas a partir de um objetivo
- Planejamento automático de ações
- Uso de ferramentas externas
- Memória de longo prazo
- Execução contínua baseada em objetivos

**Limitações:**

- Foco em um agente autônomo, e não em múltiplos agentes especialistas
- Dificuldade de controle e previsibilidade das ações
- Pouco controle de fluxo e governança
- Não possui foco em integração entre agentes especialistas com papéis bem definidos
- Não foi projetado para ambientes corporativos com requisitos de segurança e rastreabilidade

### 1.3.3 CrewAI

- **Nome do produto:** CrewAI
- **Link:** https://www.crewai.com/
- **Público-alvo:** Desenvolvedores que desejam criar sistemas multiagentes com papéis definidos, simulando equipes de trabalho compostas por agentes.

**Funcionalidades principais:**

- Definição de papéis para agentes
- Execução de tarefas em sequência ou de forma colaborativa
- Compartilhamento de contexto entre agentes
- Simulação de equipes de trabalho compostas por agentes
- Coordenação de tarefas entre múltiplos agentes

**Limitações:**

- Comunicação entre agentes baseada principalmente em troca de mensagens e contexto textual
- Falta de contratos técnicos formais entre agentes
- Pouco foco em governança, segurança e isolamento entre agentes
- Não define uma arquitetura corporativa de integração entre agentes
- Pouco foco em observabilidade e rastreabilidade das ações dos agentes

### 1.3.4 Microsoft AutoGen

- **Nome do produto:** Microsoft AutoGen
- **Link:** https://github.com/microsoft/autogen
- **Público-alvo:** Pesquisadores e desenvolvedores que desejam construir sistemas multiagentes colaborativos baseados em modelos de linguagem.

**Funcionalidades principais:**

- Comunicação entre múltiplos agentes
- Definição de diferentes papéis para agentes
- Execução colaborativa de tarefas
- Integração com ferramentas externas e execução de código
- Simulação de conversas entre agentes para resolução de problemas

**Limitações:**

- Foco maior em pesquisa e experimentação
- Comunicação baseada principalmente em mensagens, não em APIs ou contratos formais
- Não aborda profundamente questões de governança, segurança e observabilidade
- Não define claramente uma arquitetura corporativa para integração de agentes

### 1.3.5 Comparação das Soluções

| Solução | Pontos Fortes | Limitações |
|---|---|---|
| LangChain | Integração com ferramentas, RAG, memória | Não foca em colaboração estruturada entre agentes |
| AutoGPT | Autonomia e planejamento | Pouco controle e foco em agente único |
| CrewAI | Multiagente com papéis definidos | Falta de contratos técnicos e governança |
| AutoGen | Comunicação entre agentes | Foco mais acadêmico e experimental |

### Lacuna não resolvida pelas soluções existentes

A partir do benchmark realizado, observa-se que as soluções existentes apresentam algumas limitações quando analisadas sob a perspectiva de arquitetura de software e integração corporativa. Entre as principais lacunas identificadas, destacam-se:

- Ausência de contratos técnicos formais entre agentes
- Comunicação entre agentes baseada principalmente em mensagens textuais, e não em interfaces bem definidas
- Falta de uma arquitetura de integração voltada para ambientes corporativos
- Pouca abordagem sobre governança, segurança e isolamento entre agentes
- Ausência de mecanismos formais de observabilidade e rastreabilidade das decisões dos agentes
- Foco maior em automação de tarefas e não em integração de conhecimento entre especialistas

Dessa forma, identifica-se uma lacuna relacionada à arquitetura de integração e orquestração de agentes especialistas, especialmente em cenários que envolvem múltiplos domínios de conhecimento, sistemas legados e arquiteturas corporativas complexas.

### 1.3.6 Diferencial do Projeto

A análise das soluções disponíveis demonstra que já existem diversas ferramentas e frameworks que permitem a criação de agentes baseados em modelos de linguagem, capazes de utilizar aplicações externas e até mesmo estabelecer comunicação entre si. No entanto, essas soluções foram desenvolvidas, em sua maioria, com foco na automação de tarefas, na construção de assistentes inteligentes ou em contextos de experimentação acadêmica, não sendo projetadas especificamente para a integração estruturada de agentes especialistas em ambientes corporativos complexos.

Nesse contexto, observa-se que a principal lacuna não está na ausência de tecnologias para criação de agentes, mas na inexistência de uma arquitetura que trate agentes especialistas como componentes de software integrados, com definição clara de comunicação, contratos técnicos, governança e rastreabilidade.

Em ambientes corporativos complexos, o desafio central não se limita à execução de tarefas isoladas, mas envolve a necessidade de integrar conhecimentos distribuídos entre diferentes domínios, manter o contexto técnico ao longo do processo e garantir a colaboração estruturada entre especialistas, sejam eles humanos ou artificiais.

Dessa forma, o objetivo deste projeto não é propor um novo framework de agentes, mas sim um modelo arquitetural que possibilite a integração estruturada de agentes especialistas, com definição clara de papéis, responsabilidades, contratos de comunicação e mecanismos de orquestração, aproximando o comportamento desses agentes ao funcionamento de equipes de especialistas em ambientes corporativos.

O sistema proposto está voltado ao apoio de tarefas técnicas complexas em ambientes corporativos de desenvolvimento de software, especialmente em cenários que envolvem integração entre sistemas legados e modernos, conversão de funcionalidades entre diferentes tecnologias, interpretação de regras de negócio existentes, apoio à tomada de decisão técnica e arquitetural e integração de conhecimento entre diferentes áreas especializadas.

Assim, o diferencial deste projeto reside na proposição de uma arquitetura de integração de agentes especialistas orientada a ambientes corporativos, na qual os agentes são tratados como componentes especializados que colaboram entre si por meio de contratos técnicos e mecanismos de orquestração, com foco na integração de conhecimento e não apenas na execução de tarefas isoladas.

---

## 1.4 Público-Alvo

O sistema proposto neste projeto é voltado para profissionais que atuam em ambientes corporativos de desenvolvimento de software de alta complexidade. O foco reside em ecossistemas que envolvem múltiplas tecnologias, sistemas legados e a necessidade de integração entre diferentes áreas técnicas.

Diferentemente de sistemas voltados ao público geral, este ecossistema multiagente tem como alvo equipes técnicas que lidam com tarefas nas quais o conhecimento é distribuído, exigindo constante transferência de contexto e alinhamento entre especialistas.

### Perfil dos Usuários

Os principais usuários do sistema são:

- **Desenvolvedores de Software:** profissionais responsáveis pela implementação e manutenção de sistemas. Frequentemente enfrentam dificuldades para analisar rapidamente lógicas elaboradas ou códigos legados e dependem da integração com outros profissionais para concluir tarefas. O sistema auxilia na redução do esforço manual de busca por contexto técnico.
- **Analistas de Sistemas:** responsáveis por mapear processos e documentar funcionalidades. Atuam na intersecção entre o negócio e a técnica, sendo diretamente impactados pela fragmentação das informações. O sistema apoia a mitigação de interpretações divergentes e ajuda no realinhamento de expectativas sobre as regras de negócio.
- **Arquitetos de Software:** responsáveis por decisões estruturais e evolução das plataformas. Lidam com o desafio de integrar sistemas de diferentes gerações e podem se beneficiar de agentes especialistas para análise de impacto e definição de padrões, reduzindo inconsistências na execução das diretrizes arquiteturais.

### Nível de Conhecimento Técnico Esperado

O sistema não é voltado para usuários leigos. O público-alvo possui conhecimento técnico intermediário ou avançado, o que permite que a interface e as funcionalidades assumam familiaridade com conceitos como:

- APIs e integração de sistemas
- Arquiteturas de banco de dados
- Leitura e interpretação de código-fonte
- Documentação técnica e diagramação

O sistema atua, portanto, como uma ferramenta de apoio técnico e integração de conhecimento, visando diminuir o custo de coordenação entre esses diferentes perfis em ambientes corporativos.

---

## 1.5 Objetivos do Projeto

### 1.5.1 Objetivo Geral

Propor e validar uma arquitetura estruturada de integração de agentes especialistas, baseada nos princípios de *Spec-Driven Development* (SDD), para orquestrar a colaboração entre múltiplos agentes de inteligência artificial no desenvolvimento e manutenção de aplicações em ambientes corporativos complexos, considerando a coordenação entre papéis especializados, diferentes domínios de conhecimento e diretrizes de engenharia de software.

### 1.5.2 Objetivos Específicos

Para atingir o objetivo geral, foram definidos os seguintes objetivos específicos:

1. **Estudar e consolidar a base teórica sobre arquitetura de software e a integração de sistemas multiagentes.**  
   Este objetivo visa construir a fundamentação teórica do projeto, relacionando conceitos de sistemas multiagente, sistemas distribuídos, arquitetura orientada a serviços e agentes baseados em modelos de linguagem.

2. **Analisar soluções existentes relacionadas a agentes e sistemas multiagente, identificando suas limitações em ambientes corporativos.**  
   Este objetivo corresponde ao benchmark do projeto, no qual serão analisadas plataformas e frameworks existentes, como LangChain, AutoGen e CrewAI, com o objetivo de identificar lacunas relacionadas à integração estruturada entre agentes.

3. **Definir uma arquitetura de integração de agentes especialistas, incluindo comunicação, contratos, orquestração e governança.**  
   Este é um dos principais objetivos técnicos do projeto, no qual será proposta uma arquitetura que trate agentes como componentes de software especializados, capazes de se comunicar por meio de interfaces e contratos bem definidos.

4. **Desenvolver uma prova de conceito (PoC) do ecossistema multiagente aplicada a um cenário de desenvolvimento de software corporativo.**  
   A prova de conceito terá como objetivo demonstrar, na prática, o funcionamento da arquitetura proposta, por meio da simulação de agentes especialistas colaborando para resolver uma tarefa técnica complexa.

5. **Avaliar os benefícios e limitações da arquitetura proposta no apoio a tarefas complexas em ambientes corporativos.**  
   Este objetivo visa analisar os resultados da prova de conceito, avaliando aspectos como colaboração entre agentes, organização do fluxo de trabalho, reaproveitamento de conhecimento e viabilidade da solução em ambientes corporativos.

6. **Avaliar como os GAPs de conhecimento do squad foram encadeados ao decorrer da utilização da aplicação.**  
   Este objetivo visa analisar os resultados comparativos referentes ao desenvolvimento do time com base no apoio que a aplicação terá, avaliando aspectos como a rápida associação da tarefa com ajuda da rede de agentes.

### 1.5.3 Hipóteses de Pesquisa

Baseando-se no problema identificado e na proposta de solução, são definidas as seguintes hipóteses de pesquisa:

- **H1 — Redução do tempo de execução**  
  A utilização de uma arquitetura baseada em agentes especialistas reduz o tempo necessário para execução de tarefas complexas em ambientes corporativos, quando comparado ao modelo tradicional baseado em comunicação manual entre especialistas.

- **H2 — Redução da dependência de especialistas**  
  A integração de agentes especialistas permite reduzir a dependência direta de profissionais específicos, ao disponibilizar conhecimento estruturado e acessível de forma automatizada.

- **H3 — Melhoria na qualidade técnica das soluções**  
  A orquestração de múltiplos agentes especializados contribui para a melhoria da qualidade técnica das soluções propostas, ao permitir a validação cruzada entre diferentes domínios de conhecimento.

Para sustentar as hipóteses apresentadas, fundamenta-se a proposta nos princípios de integração de sistemas e arquiteturas distribuídas.

A integração de sistemas é um dos pilares fundamentais em ambientes corporativos de grande porte, especialmente em cenários que envolvem múltiplas tecnologias, sistemas legados e arquiteturas distribuídas.

Segundo o paradigma de *Service-Oriented Architecture* (SOA), sistemas devem ser estruturados como serviços independentes que se comunicam por meio de interfaces bem definidas, permitindo maior flexibilidade, reutilização e escalabilidade.

Nesse contexto, o uso de *Application Programming Interface* (APIs) torna-se essencial para a comunicação entre componentes, permitindo que diferentes sistemas e módulos troquem informações de forma padronizada.

Além disso, a definição de contratos de comunicação, como *schemas* de dados e interfaces formais, é fundamental para garantir a interoperabilidade entre sistemas, reduzindo ambiguidades e assegurando consistência na troca de informações.

No contexto deste projeto, esses conceitos são aplicados à integração entre agentes especialistas, que passam a se comportar como serviços independentes dentro de uma arquitetura distribuída, comunicando-se por meio de contratos técnicos bem definidos e orquestrados por um componente central.

---

## 1.6 Métricas de Sucesso (KPIs)

Para avaliar o sucesso do projeto, foram definidos indicadores que medem tanto o desempenho técnico da arquitetura proposta quanto o impacto da utilização de agentes no apoio a tarefas complexas em ambientes corporativos.

As métricas foram definidas com o objetivo de avaliar se a utilização de um ecossistema multiagente organizado, por meio de uma arquitetura de integração estruturada, pode melhorar a execução de tarefas que envolvem múltiplos domínios de conhecimento.

### 1.6.1 Redução do Tempo de Execução de Tarefas Complexas

Uma das principais hipóteses do projeto é que a utilização de agentes especialistas colaborando entre si pode reduzir o tempo necessário para executar tarefas que exigem conhecimento distribuído entre diferentes áreas.

Dessa forma, será medida a diferença entre:

- O tempo estimado para execução de uma tarefa complexa de forma tradicional
- O tempo estimado para execução da mesma tarefa com apoio do ecossistema multiagente

**Meta:** redução de pelo menos 30% no tempo de execução da tarefa.

### 1.6.2 Tempo de Resposta do Sistema

O tempo de resposta corresponde ao tempo estimado para que o sistema receba uma solicitação, orquestre os agentes necessários e retorne uma resposta consolidada ao usuário.

**Meta:** tempo médio de resposta inferior a 10 segundos para tarefas que envolvam múltiplos agentes.

### 1.6.3 Taxa de Sucesso na Execução de Tarefas

Essa métrica avalia se o sistema consegue completar corretamente o fluxo de execução entre agentes, desde a solicitação inicial até a geração da resposta final.

Será medida a porcentagem de execuções em que:

- O fluxo entre agentes foi concluído
- Os agentes conseguiram se comunicar corretamente
- A resposta final foi gerada

**Meta:** taxa de sucesso superior a 80% das execuções.

### 1.6.4 Capacidade de Integração entre Agentes Especialistas

Essa métrica avalia a capacidade da arquitetura de integrar múltiplos agentes especialistas em um único fluxo de execução.

Será medida a quantidade de agentes diferentes que conseguem participar de um fluxo orquestrado, como por exemplo:

- Agente de regras de negócio
- Agente de código legado
- Agente de interface
- Agente de arquitetura

**Meta:** integração de pelo menos 3 agentes especialistas em um fluxo completo de execução.

### 1.6.5 Rastreabilidade e Registro das Interações

Uma das propostas da arquitetura é permitir rastreabilidade das decisões e interações entre agentes. Dessa forma, será avaliado se o sistema consegue registrar:

- Qual agente foi acionado
- Qual tarefa foi executada
- Qual foi o resultado
- Qual agente utilizou a resposta de outro agente

**Meta:** 100% das interações entre agentes registradas.

### 1.6.6 Resumo dos KPIs

| KPI | Descrição | Meta |
|---|---|---|
| Redução do tempo de execução | Comparação entre processo tradicional e com agentes | ≥ 30% |
| Tempo de resposta | Tempo para orquestrar agentes e retornar resposta | ≤ 10 s |
| Taxa de sucesso | Execuções concluídas com sucesso | ≥ 80% |
| Integração entre agentes | Número de agentes no fluxo | ≥ 3 agentes |
| Rastreabilidade | Registro das interações | 100% |

---

# 8. Referências

## Livros e Capítulos de Livros

RUSSELL, Stuart J.; NORVIG, Peter. *Artificial intelligence: a modern approach*. 4. ed. Upper Saddle River: Pearson, 2020.

TAULLI, Tom; DESHMUKH, Gaurav. CrewAI. In: TAULLI, Tom; DESHMUKH, Gaurav. *Building Generative AI Agents: Using LangGraph, AutoGen, and CrewAI*. Berkeley, CA: Apress, 2025. p. 103-145.

WOOLDRIDGE, Michael. *An introduction to multiagent systems*. 2. ed. Chichester: John Wiley & Sons, 2009.

## Teses e Dissertações

NASCIMENTO, Arthur Henrique Casals do. *Engenharia de SMA: integrando sistemas distribuídos e avanços em Inteligência Artificial*. 2024. Tese (Doutorado em Engenharia de Computação) – Escola Politécnica, Universidade de São Paulo, São Paulo, 2024.

QUESADA, Christian Jhulian Braga. *Inteligência artificial: a relevância para a arquitetura*. 2024. Tese (Doutorado em Arquitetura e Urbanismo) – Faculdade de Arquitetura e Urbanismo, Universidade de São Paulo, São Paulo, 2024.

## Artigos e Trabalhos Acadêmicos

IABAGATA, Tatiana Yukari Sekiya et al. *Aplicação de Ferramentas Baseadas em Inteligência Artificial para Minimização de Desafios e Otimização de Processos na Engenharia de Software*. [S. l.: s. n.], 2025.

SILVA, Rui. *Interoperabilidade em Sistemas multiagente: Princípios Éticos e Morais na Inteligência Artificial*. [S. l.: s. n.], 2024.

WALKER, Clinton et al. Forensic Analysis of Artifacts from Microsoft's Multi-Agent LLM Platform AutoGen. In: *INTERNATIONAL CONFERENCE ON AVAILABILITY, RELIABILITY AND SECURITY*, 19th., 2024. *Proceedings...* [S. l.]: ACM, 2024. p. 1-9.

YANG, Hui; YUE, Sifu; HE, Yunzhong. Auto-gpt for online decision making: Benchmarks and additional opinions. *arXiv preprint arXiv:2306.02224*, 2023.

## Documentação Técnica e Sites

MAVROUDIS, Vasilios. LangChain. [S. l.]: LangChain, 2024. Disponível em: <https://www.langchain.com/>. Acesso em: 8 abr. 2026.