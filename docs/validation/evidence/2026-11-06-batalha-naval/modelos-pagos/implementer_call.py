"""Uma chamada só do agente de programação, com o mesmo prompt que o orquestrador montaria.

Uso: python implementer_call.py <modelo> <pasta-de-saida>
Reaproveita os documentos já gerados (gpt-5-mini na rodada paga anterior; o de UX veio
do modelo gratuito, porque o agente de UX falhou na rodada paga) como entregas do time.
"""
import json
import os
import pathlib
import sys
import time

sys.path.insert(0, "C:/Users/Flavia/flav-fe/backend")
os.environ.setdefault("DATABASE_URL", "sqlite:///C:/Users/Flavia/fv12/implementer.db")

from app.core.config import Settings  # noqa: E402
from app.llm.providers.openrouter_provider import OpenRouterLLMProvider  # noqa: E402
from app.models import TechnicalRequest  # noqa: E402
from app.services import llm_service  # noqa: E402
from app.services.team_context import build_team_context  # noqa: E402

MODEL, OUT = sys.argv[1], pathlib.Path(sys.argv[2])
TEMP = pathlib.Path(os.environ["TEMP"])
sys.path.insert(0, "C:/Users/Flavia/flav-fe/backend/scripts")
from create_game_dev_clan import SKILLS  # noqa: E402

PROGRAMMER = next(skill for skill in SKILLS if skill["domain"] == "programacao_jogos")
PAID = TEMP / "bn-pago" / "rodada-1" / "docs"
FREE = TEMP / "bn-v2" / "rodada-2" / "docs"
entries = [
    ("Game Design", "", [("GDD.md", (PAID / "GDD.md").read_text(encoding="utf-8"))]),
    ("Metodologia de Desenvolvimento de Jogos", "", [("BACKLOG.md", (PAID / "BACKLOG.md").read_text(encoding="utf-8"))]),
    ("Qualidade e Testes de Jogos", "", [("PLANO_DE_TESTES.md", (PAID / "PLANO_DE_TESTES.md").read_text(encoding="utf-8"))]),
    ("UX e Acessibilidade de Jogos", "", [("ACESSIBILIDADE.md", (FREE / "ACESSIBILIDADE.md").read_text(encoding="utf-8"))]),
]
team_context = None if os.environ.get("NO_CONTEXT") else build_team_context(entries)

request = TechnicalRequest(
    id="req-batalha-naval",
    trace_id="TRC-IMPLEMENTADOR",
    title="Criar um jogo de batalha naval para navegador",
    problem="Precisamos de um jogo simples de batalha naval para validar o fluxo do time de jogos. "
    "Hoje não existe nenhum código.",
    objective="Gere o código-fonte completo e jogável (index.html, style.css e game.js) de uma batalha "
    "naval contra o computador, além da documentação de cada área.",
    context="Jogo para navegador, só HTML, CSS e JavaScript puro, sem bibliotecas, abrindo o index.html "
    "direto. Tabuleiro 10x10 para o jogador e para o computador. Frota: porta-aviões (5), encouraçado (4), "
    "cruzador (3), submarino (3) e destróier (2), posicionados aleatoriamente sem sobreposição. O jogador "
    "atira clicando no tabuleiro do computador; o computador responde com um tiro aleatório em casa ainda "
    "não atingida. Mostrar acerto, erro e navio afundado, e anunciar vitória ou derrota com opção de reiniciar.",
    restrictions=["Não executar alterações automaticamente"],
)
request.attachments = []
safe_request, _, truncated, _ = llm_service._build_safe_request(
    request,
    analysis_domain_label=PROGRAMMER["domain"],
    persona_instructions=PROGRAMMER["persona_instructions"],
    team_context=team_context,
)

if os.environ.get("DRY"):
    from app.llm.prompts import build_technical_planner_prompt

    prompt = build_technical_planner_prompt(safe_request)
    print("prompt chars:", len(prompt), "| contexto do time:", len(team_context or ""), "| truncado:", truncated)
    print(prompt[-1500:])
    sys.exit(0)

config = Settings(
    llm_enabled=True,
    llm_provider="openrouter",
    llm_model=MODEL,
    llm_allowed_models=MODEL,
    llm_timeout_seconds=300,
    openrouter_api_key=os.environ["OPENROUTER_API_KEY"],
    openrouter_base_url="http://127.0.0.1:9998/api/v1",
)
started = time.perf_counter()
result = OpenRouterLLMProvider(config).generate_plan(safe_request, llm_call_id=f"impl-{MODEL}", model=MODEL)
seconds = round(time.perf_counter() - started)

OUT.mkdir(parents=True, exist_ok=True)
for file in result.plan.generated_files:
    (OUT / pathlib.Path(file.filename).name).write_text(file.content, encoding="utf-8")
(OUT / "resumo.json").write_text(
    json.dumps(
        {
            "modelo": MODEL,
            "segundos": seconds,
            "tokens_entrada": result.usage.input_tokens,
            "tokens_saida": result.usage.output_tokens,
            "contexto_do_time_chars": len(team_context or ""),
            "entrada_truncada": truncated,
            "arquivos": [file.filename for file in result.plan.generated_files],
            "resumo": result.plan.summary,
        },
        ensure_ascii=False,
        indent=1,
    ),
    encoding="utf-8",
)
print(f"{MODEL}: {seconds}s, tokens {result.usage.input_tokens}+{result.usage.output_tokens}, "
      f"arquivos {[f.filename for f in result.plan.generated_files]}")
