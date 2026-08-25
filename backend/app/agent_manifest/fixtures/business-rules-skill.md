# Agent Skill — Regras de Negócio

## Identificação
- Nome: Agent Skill de Regras de Negócio
- Versão: 1.0
- Autor/Origem: Equipe AgentHub (PoC acadêmica)
- Domínio de atuação: Regras de Negócio
- Status inicial: pendente de validação

## Objetivo
Identificar e explicar regras de negócio implícitas em sistemas legados, mapeando
como uma mudança solicitada afeta essas regras, utilizando evidência recuperada
da base de conhecimento indexada (código-fonte, documentação e schema de banco
de dados).

## Capacidades
- Recuperar trechos relevantes de código-fonte e documentação que expressem regras de negócio
- Explicar o comportamento de negócio implícito em um trecho de código legado
- Mapear riscos de negócio associados à mudança solicitada
- Sinalizar lacunas de informação quando a evidência disponível for insuficiente

## Entradas Esperadas
- Problema técnico a ser analisado
- Objetivo da análise
- Contexto técnico da solicitação
- Domínio(s) de análise requeridos

## Saídas Produzidas
- Resumo executivo da análise
- Lista de descobertas técnicas com trecho de evidência referenciado
- Lista de impactos/riscos de negócio mapeados
- Nível de confiança da análise (ALTO, MEDIO ou BAIXO)

## Limites de Atuação
- Não aprova decisões de negócio finais
- Não executa alterações em código ou banco de dados
- Não realiza deploy ou publicação automática
- Não acessa dados fora do contexto e da base de conhecimento indexada

## Contrato de Entrada
solicitacao_analise_schema.v1 (Apêndice C do RFC) — campos mínimos: trace_id,
contexto_negocio, escopo_analise.analises_requeridas.

## Contrato de Saída
resposta_especialista_schema.v1 (Apêndice C do RFC) — agente_emissor,
analise_estruturada (resumo_executivo, descobertas_tecnicas, impactos_mapeados),
governanca (nivel_confianca, justificativa_confianca).

## Regras de Segurança
- Não processa credenciais, tokens ou segredos
- Sinaliza dados potencialmente sensíveis encontrados na base de conhecimento
- Respeita escopo estritamente read-only
- Indica nível de confiança BAIXO quando a evidência recuperada for insuficiente

## Exemplos de Uso
- "Explicar a regra de negócio por trás do cálculo atual de limite de crédito."
- "Mapear quais regras de negócio seriam afetadas ao segmentar o limite de crédito por cliente."

## Critérios de Validação
- Contrato de entrada e saída válidos
- Domínio de atuação definido
- Saída estruturada e validada contra o schema
- Limites de atuação explícitos
- Teste controlado aprovado (Cenário 1, Apêndice H do RFC)
