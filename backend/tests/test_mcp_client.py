"""O cliente MCP só chama a ferramenta que o servidor da skill anuncia."""

import asyncio

import pytest

from app.agent_catalog import mcp_client
from app.agent_catalog.tool_interface import SkillToolCall
from app.core.config import settings
from app.models import AgentSkill


def test_does_not_call_a_tool_the_server_does_not_list(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_skill_transport", "memory")
    monkeypatch.setattr(mcp_client, "_TOOL_NAME", "ferramenta_inexistente")
    tool_call = SkillToolCall(trace_id="TRC-1", technical_request_id="r1", user_id="u1", agent_skill_id="s1")

    with pytest.raises(mcp_client.SkillMCPError, match="não expõe a ferramenta"):
        asyncio.run(mcp_client.call_skill_tool(AgentSkill(), tool_call))
