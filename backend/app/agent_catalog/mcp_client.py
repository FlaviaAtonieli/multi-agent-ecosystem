"""MCP client side of the Orchestrator: connects to a skill's real MCP server
and invokes it, over either transport supported by the SDK.

Domain -> server module mapping replaces the old in-process `_EXECUTORS` dict.
"""

import importlib
import os
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters, stdio_client
from pydantic import SecretStr

from app.agent_catalog.tool_interface import SkillToolCall, SkillToolResult
from app.core.config import Settings, settings

_DOMAIN_SERVER_MODULES: dict[str, str] = {
    "codigo_legado": "app.agent_catalog.mcp_servers.legacy_code_server",
    "regras_negocio": "app.agent_catalog.mcp_servers.business_rules_server",
    "arquitetura_software": "app.agent_catalog.mcp_servers.architecture_server",
}

_TOOL_NAME = "executar"


class SkillMCPError(RuntimeError):
    pass


class SkillServerNotImplementedError(SkillMCPError):
    pass


def _backend_root() -> Path:
    import app as app_package

    return Path(app_package.__file__).resolve().parent.parent


def _subprocess_env(config: Settings) -> dict[str, str]:
    """Builds the child process environment from the *live* Settings object,
    not just os.environ.

    Settings can be overridden at runtime (tests do this via
    `monkeypatch.setattr(settings, ...)`, which mutates the singleton without
    touching any real environment variable). A subprocess started fresh only
    sees actual env vars, so forwarding bare `os.environ` would silently give
    it stale/default config — e.g. LLM_ENABLED back to False even though the
    parent process has it on. Every current field is re-serialized here so the
    child always sees the same effective config as its parent, regardless of
    where that config came from.
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
    domain: str,
    tool_call: SkillToolCall,
    *,
    config: Settings = settings,
) -> SkillToolResult:
    module_path = _DOMAIN_SERVER_MODULES.get(domain)
    if module_path is None:
        raise SkillServerNotImplementedError(
            f"Não há servidor MCP implementado para o domínio '{domain}' nesta PoC."
        )

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
        # Real discovery, not decorative: proves the server actually exposes
        # what the catalog says it should before we call it.
        await client.list_tools()
        result = await client.call_tool(_TOOL_NAME, {"entrada": tool_call.model_dump(mode="json")})

    if result.is_error:
        first_block = result.content[0] if result.content else None
        message = getattr(first_block, "text", None) or "Falha desconhecida na Agent Skill."
        raise SkillMCPError(message)

    return SkillToolResult.model_validate(result.structured_content)
