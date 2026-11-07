from pydantic import BaseModel


class RetrievalEvalCase(BaseModel):
    """Uma pergunta e os documentos que de fato a respondem, para medir a busca contra
    um gabarito real.
    """

    query: str
    relevant_artifacts: set[str]


def _ranked_artifacts(retrieved_artifacts: list[str]) -> list[str]:
    """Junta nomes repetidos na primeira ocorrência, a mais bem colocada. Um arquivo rende
    vários trechos, mas precisão e revocação contam documentos, não trechos.
    """
    seen: list[str] = []
    for name in retrieved_artifacts:
        if name not in seen:
            seen.append(name)
    return seen


def precision_at_k(retrieved_artifacts: list[str], relevant_artifacts: set[str], k: int) -> float:
    ranked = _ranked_artifacts(retrieved_artifacts)[:k]
    if not ranked:
        return 0.0
    hits = sum(1 for name in ranked if name in relevant_artifacts)
    return hits / len(ranked)


def recall_at_k(retrieved_artifacts: list[str], relevant_artifacts: set[str], k: int) -> float:
    if not relevant_artifacts:
        return 0.0
    ranked = set(_ranked_artifacts(retrieved_artifacts)[:k])
    hits = sum(1 for name in relevant_artifacts if name in ranked)
    return hits / len(relevant_artifacts)


def reciprocal_rank(retrieved_artifacts: list[str], relevant_artifacts: set[str]) -> float:
    for position, name in enumerate(_ranked_artifacts(retrieved_artifacts), start=1):
        if name in relevant_artifacts:
            return 1 / position
    return 0.0


# Gabarito tirado do conteúdo real de app/rag/fixtures/legacy_billing/.
LEGACY_BILLING_GROUND_TRUTH: list[RetrievalEvalCase] = [
    RetrievalEvalCase(
        query="Qual é o valor do limite de crédito hoje e em qual classe ele está definido?",
        relevant_artifacts={"CreditLimitService.java", "business-rules.md"},
    ),
    RetrievalEvalCase(
        query="O campo SEGMENTO do cliente é considerado no cálculo do limite de crédito?",
        relevant_artifacts={
            "CreditLimitService.java",
            "CustomerRepository.java",
            "business-rules.md",
            "schema.sql",
        },
    ),
    RetrievalEvalCase(
        query=(
            "Quais pontos do sistema dependem do limite de crédito atual e "
            "precisam ser atualizados se a regra mudar?"
        ),
        relevant_artifacts={"business-rules.md", "CreditLimitService.java"},
    ),
    RetrievalEvalCase(
        query="Como o repositório calcula o total de pedidos em aberto de um cliente?",
        relevant_artifacts={"CustomerRepository.java"},
    ),
    RetrievalEvalCase(
        query="Existe uma tabela no banco de dados dedicada ao limite de crédito por segmento?",
        relevant_artifacts={"schema.sql"},
    ),
    RetrievalEvalCase(
        query="Quais são os valores possíveis do campo SEGMENTO na tabela CUSTOMER?",
        relevant_artifacts={"schema.sql"},
    ),
    RetrievalEvalCase(
        query="O CustomerRepository usa algum ORM para acessar o banco de dados?",
        relevant_artifacts={"CustomerRepository.java"},
    ),
    RetrievalEvalCase(
        query="Qual método decide se um pedido pode ser aprovado com base no limite disponível do cliente?",
        relevant_artifacts={"CreditLimitService.java"},
    ),
]


# Gabarito de Regras de Negócio (app/rag/fixtures/business_rules/). Os documentos
# falam do mesmo sistema do legacy_billing, então a busca precisa separar pelo assunto,
# não só reconhecer "limite de crédito".
BUSINESS_RULES_GROUND_TRUTH: list[RetrievalEvalCase] = [
    RetrievalEvalCase(
        query=(
            "Existe alguma decisão de negócio aprovada para diferenciar o "
            "limite de crédito por segmento de cliente?"
        ),
        relevant_artifacts={"change-request-history.md"},
    ),
    RetrievalEvalCase(
        query="Qual é a regra de desconto aplicada hoje a pedidos de alto valor?",
        relevant_artifacts={"pricing-policy.md"},
    ),
    RetrievalEvalCase(
        query="O desconto comercial concedido a um pedido depende do segmento do cliente?",
        relevant_artifacts={"pricing-policy.md"},
    ),
    RetrievalEvalCase(
        query=(
            "Por que a proposta de alçada de aprovação manual acima do "
            "limite de crédito foi rejeitada?"
        ),
        relevant_artifacts={"change-request-history.md"},
    ),
    RetrievalEvalCase(
        query=(
            "Quais solicitações de mudança de negócio já foram registradas "
            "envolvendo o limite de crédito do cliente, e qual o status de "
            "cada uma?"
        ),
        relevant_artifacts={"change-request-history.md"},
    ),
]


# Gabarito de Arquitetura de Software (app/rag/fixtures/architecture/).
ARCHITECTURE_GROUND_TRUTH: list[RetrievalEvalCase] = [
    RetrievalEvalCase(
        query=(
            "Quais módulos dependem diretamente do serviço de limite de "
            "crédito e por que isso é um risco arquitetural?"
        ),
        relevant_artifacts={"module-dependency-map.md"},
    ),
    RetrievalEvalCase(
        query="Existe alguma camada de abstração entre o CreditLimitService e os módulos que o consomem?",
        relevant_artifacts={"module-dependency-map.md"},
    ),
    RetrievalEvalCase(
        query=(
            "Onde o job noturno de recálculo de risco roda, e ele compete "
            "por recursos com o fluxo de aprovação de pedidos?"
        ),
        relevant_artifacts={"deployment-topology.md"},
    ),
    RetrievalEvalCase(
        query=(
            "O processamento em lote do limite de crédito roda em uma fila "
            "ou worker separado da aplicação web?"
        ),
        relevant_artifacts={"deployment-topology.md"},
    ),
    RetrievalEvalCase(
        query=(
            "O serviço de domínio do limite de crédito está acoplado "
            "diretamente ao schema do banco de dados?"
        ),
        relevant_artifacts={"module-dependency-map.md", "CustomerRepository.java"},
    ),
]


# Gabarito de Segurança da Informação (app/rag/fixtures/security/).
SECURITY_GROUND_TRUTH: list[RetrievalEvalCase] = [
    RetrievalEvalCase(
        query="As consultas do CustomerRepository são vulneráveis a SQL injection?",
        relevant_artifacts={"access-control-notes.md", "CustomerRepository.java"},
    ),
    RetrievalEvalCase(
        query="Existe log de auditoria para consultas ao limite de crédito de um cliente?",
        relevant_artifacts={"access-control-notes.md"},
    ),
    RetrievalEvalCase(
        query="O campo EMAIL do cliente é considerado dado pessoal sensível para fins de LGPD?",
        relevant_artifacts={"data-classification.md"},
    ),
    RetrievalEvalCase(
        query="O relatório financeiro mensal expõe o e-mail do cliente sem necessidade para o caso de uso?",
        relevant_artifacts={"data-classification.md"},
    ),
    RetrievalEvalCase(
        query="A credencial de banco usada pelo job noturno de risco tem permissões restritas de leitura?",
        relevant_artifacts={"access-control-notes.md"},
    ),
]


# Gabarito dos seis domínios novos. Cada pergunta é escrita como uma pessoa
# perguntaria, sem as palavras do documento, e lista todos os arquivos que a respondem.
TEST_QUALITY_GROUND_TRUTH: list[RetrievalEvalCase] = [
    RetrievalEvalCase(
        query="Quais cenários do cálculo do limite de crédito têm teste automatizado hoje?",
        relevant_artifacts={"CreditLimitServiceTest.java", "test-coverage-audit.md"},
    ),
    RetrievalEvalCase(
        query="Existe algum teste para clientes do segmento corporativo?",
        relevant_artifacts={"CreditLimitServiceTest.java", "test-coverage-audit.md"},
    ),
    RetrievalEvalCase(
        query="Por que um teste de integração do fluxo de pedidos falha de vez em quando no pipeline?",
        relevant_artifacts={"test-coverage-audit.md"},
    ),
    RetrievalEvalCase(
        query="O job noturno de risco e o relatório financeiro têm testes próprios?",
        relevant_artifacts={"test-coverage-audit.md"},
    ),
    RetrievalEvalCase(
        query="Que rede de segurança criar antes de mudar a regra de cálculo do limite?",
        relevant_artifacts={"test-coverage-audit.md"},
    ),
]

OBSERVABILITY_GROUND_TRUTH: list[RetrievalEvalCase] = [
    RetrievalEvalCase(
        query="Por que ninguém percebeu durante quase uma semana que o processamento noturno parou?",
        relevant_artifacts={"incident-postmortem-riskbatchjob.md"},
    ),
    RetrievalEvalCase(
        query="Quais componentes do módulo de crédito têm métricas, dashboards ou alertas?",
        relevant_artifacts={"logging-metrics-gaps.md"},
    ),
    RetrievalEvalCase(
        query="Os logs da aprovação de pedidos permitem correlacionar as linhas de uma mesma requisição?",
        relevant_artifacts={"logging-metrics-gaps.md"},
    ),
    RetrievalEvalCase(
        query="O que causou a falha de conexão do job e como foi corrigida?",
        relevant_artifacts={"incident-postmortem-riskbatchjob.md"},
    ),
    RetrievalEvalCase(
        query="Que instrumentação mínima foi recomendada antes de alterar a regra de negócio?",
        relevant_artifacts={"logging-metrics-gaps.md", "incident-postmortem-riskbatchjob.md"},
    ),
]

PERFORMANCE_GROUND_TRUTH: list[RetrievalEvalCase] = [
    RetrievalEvalCase(
        query="Por que o job de risco fica mais lento a cada mês?",
        relevant_artifacts={"riskbatchjob-performance-profile.md"},
    ),
    RetrievalEvalCase(
        query="Quanto tempo o processamento em lote leva e qual é a janela noturna disponível?",
        relevant_artifacts={"riskbatchjob-performance-profile.md"},
    ),
    RetrievalEvalCase(
        query="Que consulta agregada e que índice resolveriam as idas repetidas ao banco?",
        relevant_artifacts={"riskbatchjob-performance-profile.md"},
    ),
    RetrievalEvalCase(
        query="O limite de crédito tem cache no caminho síncrono da aprovação?",
        relevant_artifacts={"capacity-planning-notes.md"},
    ),
    RetrievalEvalCase(
        query="Existe SLA de latência ou teste de carga para datas promocionais?",
        relevant_artifacts={"capacity-planning-notes.md"},
    ),
]

DATA_PRIVACY_GROUND_TRUTH: list[RetrievalEvalCase] = [
    RetrievalEvalCase(
        query="Por quanto tempo os dados de clientes inativos ficam guardados?",
        relevant_artifacts={"data-retention-notes.md", "lgpd-gap-audit.md"},
    ),
    RetrievalEvalCase(
        query="Como atender um titular que pede para ver ou apagar os próprios dados?",
        relevant_artifacts={"lgpd-gap-audit.md"},
    ),
    RetrievalEvalCase(
        query="Qual base legal justifica o tratamento dos dados de cada cliente?",
        relevant_artifacts={"lgpd-gap-audit.md"},
    ),
    RetrievalEvalCase(
        query="A consulta de clientes traz nome e e-mail mesmo quando só o segmento é necessário?",
        relevant_artifacts={"data-retention-notes.md"},
    ),
    RetrievalEvalCase(
        query="O relatório mensal de exposição identifica os clientes pelo nome?",
        relevant_artifacts={"lgpd-gap-audit.md"},
    ),
]

INFRASTRUCTURE_GROUND_TRUTH: list[RetrievalEvalCase] = [
    RetrievalEvalCase(
        query="Como uma nova versão do sistema chega ao servidor de produção?",
        relevant_artifacts={"deployment-process-notes.md"},
    ),
    RetrievalEvalCase(
        query="Dá para voltar para a versão anterior rapidamente se o deploy der errado?",
        relevant_artifacts={"deployment-process-notes.md"},
    ),
    RetrievalEvalCase(
        query="Onde fica guardada a senha do banco usada pelos componentes?",
        relevant_artifacts={"deployment-process-notes.md"},
    ),
    RetrievalEvalCase(
        query="Por que uma mudança aprovada no ambiente de teste quebrou em produção?",
        relevant_artifacts={"environment-parity-gaps.md"},
    ),
    RetrievalEvalCase(
        query="Quais diferenças existem entre o ambiente de homologação e o de produção?",
        relevant_artifacts={"environment-parity-gaps.md", "deployment-process-notes.md"},
    ),
]

API_INTEGRATION_GROUND_TRUTH: list[RetrievalEvalCase] = [
    RetrievalEvalCase(
        query="O que acontece com a aprovação se o serviço de score externo ficar lento?",
        relevant_artifacts={"external-score-integration-notes.md"},
    ),
    RetrievalEvalCase(
        query="A chamada ao bureau de crédito tem timeout e circuit breaker?",
        relevant_artifacts={"external-score-integration-notes.md"},
    ),
    RetrievalEvalCase(
        query="Como o fornecedor mudou o formato da resposta sem avisar e o que quebrou?",
        relevant_artifacts={"breaking-change-incident.md"},
    ),
    RetrievalEvalCase(
        query="Por que a falha de leitura da resposta externa passou despercebida por dias?",
        relevant_artifacts={"breaking-change-incident.md"},
    ),
    RetrievalEvalCase(
        query="A URL da integração externa tem versão e existe teste de contrato?",
        relevant_artifacts={"external-score-integration-notes.md"},
    ),
]


GROUND_TRUTH_BY_DOMAIN: dict[str, list[RetrievalEvalCase]] = {
    "Código Legado": LEGACY_BILLING_GROUND_TRUTH,
    "Regras de Negócio": BUSINESS_RULES_GROUND_TRUTH,
    "Arquitetura de Software": ARCHITECTURE_GROUND_TRUTH,
    "Segurança da Informação": SECURITY_GROUND_TRUTH,
    "Qualidade e Testes": TEST_QUALITY_GROUND_TRUTH,
    "Observabilidade e Monitoramento": OBSERVABILITY_GROUND_TRUTH,
    "Performance e Escalabilidade": PERFORMANCE_GROUND_TRUTH,
    "Dados e Privacidade (LGPD)": DATA_PRIVACY_GROUND_TRUTH,
    "Infraestrutura e DevOps": INFRASTRUCTURE_GROUND_TRUTH,
    "APIs e Integrações": API_INTEGRATION_GROUND_TRUTH,
}
