"""Lado cliente do MCP no orquestrador: sobe o servidor da Agent Skill e chama a
ferramenta `executar`, por stdio (um processo por chamada) ou em memória (testes).
"""

import importlib
import os
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters, stdio_client
from pydantic import SecretStr

from app.agent_catalog.tool_interface import SkillToolCall, SkillToolResult
from app.core.config import Settings, settings
from app.models import AgentSkill

SKILL_SERVER_MODULE = "app.agent_catalog.mcp_servers.skill_server"


def _module_for_skill(skill: AgentSkill) -> str:
    # Toda skill usa o mesmo servidor: o que muda entre elas está nos dados
    # (persona e área), então uma área nova não precisa de código novo.
    return SKILL_SERVER_MODULE


_TOOL_NAME = "executar"


class SkillMCPError(RuntimeError):
    pass


def _backend_root() -> Path:
    import app as app_package

    return Path(app_package.__file__).resolve().parent.parent


def _subprocess_env(config: Settings) -> dict[str, str]:
    """Monta o ambiente do processo filho a partir do Settings vivo, não só do os.environ.

    O Settings pode mudar em execução (os testes usam monkeypatch), e um processo novo
    só enxerga variáveis de ambiente reais. Sem isso, o filho voltaria aos valores
    padrão, por exemplo com LLM_ENABLED desligado enquanto o pai está ligado.
    """
    env = dict(os.environ)
    for field_name in type(config).model_fields:
        value = getattr(config, field_name)
        if value is None:
            continue
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
            if not value:
                continue
        env[field_name.upper()] = "true" if value is True else "false" if value is False else str(value)
    return env


async def call_skill_tool(
    skill: AgentSkill,
    tool_call: SkillToolCall,
    *,
    config: Settings = settings,
) -> SkillToolResult:
    module_path = _module_for_skill(skill)

    if config.mcp_skill_transport == "memory":
        server_module = importlib.import_module(module_path)
        transport = server_module.mcp
    else:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", module_path],
            cwd=str(_backend_root()),
            env=_subprocess_env(config),
        )
        transport = stdio_client(params)

    async with Client(transport) as client:
        # Descoberta real: confere que o servidor expõe a ferramenta que o catálogo promete
        # antes de chamá-la.
        await client.list_tools()
        result = await client.call_tool(_TOOL_NAME, {"entrada": tool_call.model_dump(mode="json")})

    if result.is_error:
        first_block = result.content[0] if result.content else None
        message = getattr(first_block, "text", None) or "Falha desconhecida na Agent Skill."
        raise SkillMCPError(message)

    return SkillToolResult.model_validate(result.structured_content)
