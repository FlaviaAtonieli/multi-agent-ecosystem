"""Real MCP server exposing the generic (persona-driven) Agent Skill tool.

Every user-created skill ("rede de agentes" fase 1) routes here regardless of
which domain it declares -- unlike the 4 official skills, which each have
their own dedicated server module. See mcp_client._route_module_for_skill for
the routing rule (owner_id is not None -> here).
"""

from mcp.server.mcpserver import MCPServer

from app.agent_catalog.tool_interface import GenericSkillExecutor, SkillToolCall, SkillToolResult
from app.core.database import SessionLocal
from app.models import AgentSkill, TechnicalRequest, User

mcp = MCPServer(
    "agenthub-generic-skill",
    instructions=(
        "Executa uma Agent Skill criada por um usuário, guiada pela persona/instruções "
        "declaradas no seu manifesto, usando o mesmo Model Gateway e pipeline de RAG "
        "das skills oficiais."
    ),
)

_executor = GenericSkillExecutor()


@mcp.tool()
def executar(entrada: SkillToolCall) -> SkillToolResult:
    """Executa uma Agent Skill de usuário sobre uma solicitação já qualificada."""
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
            db,
            skill=skill,
            technical_request=technical_request,
            user=user,
            tool_call=entrada,
        )
        db.commit()
        return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
