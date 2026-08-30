from app.llm.schemas import LLMPlanRequest

TECHNICAL_PLANNER_INSTRUCTIONS = (
    "Você é o agente planejador técnico do AgentHub. "
    "Responda estritamente no schema solicitado e marque aprovação humana como obrigatória."
)


def build_technical_planner_prompt(request: LLMPlanRequest) -> str:
    lines = [
        "Crie somente um plano técnico estruturado para a solicitação abaixo. "
        "Não execute ferramentas, não altere código, não publique documentos e não invente evidências.",
        "",
        f"Trace ID: {request.trace_id}",
        f"Título: {request.title}",
        f"Problema: {request.problem}",
        f"Objetivo: {request.objective}",
        f"Contexto: {request.context or 'Não informado'}",
        f"Restrições: {request.restrictions or ['Não informadas']}",
    ]

    if request.analysis_domain_label:
        lines.append(
            f"Domínio de análise: {request.analysis_domain_label}. Analise a solicitação "
            "exclusivamente sob essa perspectiva de especialidade -- não avalie nem opine "
            "sobre aspectos de outros domínios fora da sua competência."
        )

    if request.retrieved_context:
        lines.append(f"Trechos recuperados da base de conhecimento:\n{request.retrieved_context}")

    if request.additional_question:
        lines.append(
            f"Pergunta de acompanhamento do usuário: {request.additional_question}. "
            "Responda especificamente a essa pergunta, além do já analisado acima."
        )

    return "\n".join(lines)
