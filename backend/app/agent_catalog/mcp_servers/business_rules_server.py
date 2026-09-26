"""Real MCP server exposing the "Regras de Negócio" Agent Skill as a single tool.

Runnable two ways:
  - imported directly, the module-level `mcp` object can be wrapped by
    `Client(mcp)` for an in-process (no subprocess) transport — used by tests;
  - as `python -m app.agent_catalog.mcp_servers.business_rules_server`, it speaks
    real MCP JSON-RPC over stdio to whatever spawned it.

The tool itself does not receive the orchestrator's SQLAlchemy Session: MCP is a
process boundary (even the in-memory transport goes through real protocol
messages), so this server opens its own session per call and re-fetches the
rows it needs by the IDs it was given. It is spawned directly by the trusted
orchestrator process (never exposed to the network), so it inherits trust from
its parent instead of implementing MCP's OAuth 2.1 Authorization framework,
which targets remote/untrusted access.
"""

from mcp.server.mcpserver import MCPServer

from app.agent_catalog.tool_interface import BusinessRulesSkillExecutor, SkillToolCall, SkillToolResult
from app.core.database import SessionLocal
from app.models import AgentSkill, TechnicalRequest, User

mcp = MCPServer(
    "agenthub-business-rules-skill",
    instructions=(
        "Analisa regras de negócio implícitas em sistemas legados usando retrieval sobre "
        "a base de conhecimento indexada e o Model Gateway configurado."
    ),
)

_executor = BusinessRulesSkillExecutor()


@mcp.tool()
def executar(entrada: SkillToolCall) -> SkillToolResult:
    """Executa a Agent Skill de Regras de Negócio sobre uma solicitação já qualificada."""
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
