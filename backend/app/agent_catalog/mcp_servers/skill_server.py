"""Servidor MCP de verdade que expõe a ferramenta `executar` de qualquer Agent Skill.

O orquestrador sobe um processo deste servidor por chamada e conversa com ele por
JSON-RPC sobre stdio (ou, nos testes, pelo transporte em memória). Por ser uma
fronteira de processo, o servidor abre a própria sessão de banco e busca de novo,
pelos ids recebidos, o que precisa. É iniciado só pelo backend, nunca exposto à
rede, por isso não implementa a autorização OAuth do MCP, feita para acesso remoto.
"""

from mcp.server.mcpserver import MCPServer

from app.agent_catalog.tool_interface import SkillExecutor, SkillToolCall, SkillToolResult
from app.core.database import SessionLocal
from app.models import AgentSkill, TechnicalRequest, User

mcp = MCPServer(
    "agenthub-agent-skill",
    instructions=(
        "Executa uma Agent Skill do catálogo sobre uma solicitação já qualificada, com RAG "
        "sobre a base de conhecimento e o modelo configurado no Model Gateway."
    ),
)

_executor = SkillExecutor()


@mcp.tool()
def executar(entrada: SkillToolCall) -> SkillToolResult:
    """Executa a Agent Skill indicada sobre uma solicitação já qualificada."""
    with SessionLocal() as db:
        technical_request = db.get(TechnicalRequest, entrada.technical_request_id)
        if technical_request is None:
            raise ValueError(f"TechnicalRequest '{entrada.technical_request_id}' não encontrada.")
        user = db.get(User, entrada.user_id)
        if user is None:
            raise ValueError(f"User '{entrada.user_id}' não encontrado.")
        skill = db.get(AgentSkill, entrada.agent_skill_id)
        if skill is None:
            raise ValueError(f"AgentSkill '{entrada.agent_skill_id}' não encontrada.")

        result = _executor.execute(
            db, skill=skill, technical_request=technical_request, user=user, tool_call=entrada
        )
        db.commit()
        return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
