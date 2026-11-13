"""Mede se respostas repetidas do modelo dizem a mesma coisa, mesmo com texto diferente.

A comparação exata (hash) já mostrou que o texto muda a cada chamada. Aqui cada
resposta vira um embedding do resumo e dos riscos, e a similaridade entre repetições
da mesma pergunta é comparada com a similaridade entre respostas a perguntas
diferentes. Se as repetições ficam bem mais perto entre si que do controle, o
conteúdo se repete mesmo quando as palavras não.

Exige OPENROUTER_API_KEY e gera chamadas ao modelo. Uso:

    python scripts/measure_repeatability.py --model dots-studio/dots-3-note-preview:free --repeats 5
"""

import argparse
import hashlib
import itertools
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings  # noqa: E402
from app.llm.providers.openrouter_provider import OpenRouterLLMProvider  # noqa: E402
from app.llm.schemas import LLMPlan, LLMPlanRequest  # noqa: E402
from app.rag.factory import create_embedding_provider  # noqa: E402
from app.rag.retriever import cosine_similarity  # noqa: E402

QUESTION = LLMPlanRequest(
    technical_request_id="req-repeticao",
    trace_id="TRC-REPETICAO",
    title="Limite de crédito por segmento",
    problem="O sistema fictício usa um limite de crédito fixo para todos os clientes.",
    objective="Listar riscos de permitir limites diferentes por segmento.",
    context="Sistema legado fictício em Java. O limite é usado na aprovação de pedidos.",
    restrictions=["Não executar alterações"],
)
# Controle: outra pergunta técnica, de outro assunto, com a mesma forma de resposta.
CONTROL = LLMPlanRequest(
    technical_request_id="req-controle",
    trace_id="TRC-CONTROLE",
    title="Logs sem correlação entre serviços",
    problem="Os serviços fictícios gravam logs sem um identificador comum de requisição.",
    objective="Listar riscos de investigar incidentes sem rastreamento distribuído.",
    context="Três serviços fictícios em Node.js atrás de um gateway.",
    restrictions=["Não executar alterações"],
)


def _text(plan: LLMPlan) -> str:
    return plan.summary + "\n" + "\n".join(plan.risks)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--pause", type=float, default=4.0, help="segundos entre chamadas")
    args = parser.parse_args()

    config = Settings(
        llm_enabled=True,
        llm_provider="openrouter",
        llm_model=args.model,
        llm_allowed_models=args.model,
        openrouter_api_key=os.environ["OPENROUTER_API_KEY"],
        openrouter_base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        embedding_model=os.environ.get("EMBEDDING_MODEL", "openai/text-embedding-3-small"),
    )
    provider = OpenRouterLLMProvider(config)

    def ask(request: LLMPlanRequest, index: int) -> LLMPlan | None:
        try:
            return provider.generate_plan(request, llm_call_id=f"rep-{index}", model=args.model).plan
        except Exception as exc:  # noqa: BLE001 - uma falha conta como resposta perdida
            print(f"  falha: {type(exc).__name__}: {str(exc)[:100]}", flush=True)
            return None
        finally:
            time.sleep(args.pause)

    plans = [plan for index in range(args.repeats) if (plan := ask(QUESTION, index))]
    controls = [plan for index in range(2) if (plan := ask(CONTROL, 100 + index))]
    if len(plans) < 2 or not controls:
        raise SystemExit(f"Respostas insuficientes: {len(plans)} da pergunta, {len(controls)} do controle.")

    vectors = create_embedding_provider(config).embed([_text(p) for p in plans + controls])
    answers, control_vectors = vectors[: len(plans)], vectors[len(plans) :]
    within = [cosine_similarity(a, b) for a, b in itertools.combinations(answers, 2)]
    across = [cosine_similarity(a, c) for a in answers for c in control_vectors]
    distinct = len({hashlib.sha256(p.model_dump_json().encode()).hexdigest() for p in plans})

    print(f"modelo: {args.model}  embeddings: {config.embedding_model}")
    print(f"respostas: {len(plans)} de {args.repeats}, textos distintos: {distinct}")
    print(f"similaridade entre repetições: média {_mean(within):.3f}, mín {min(within):.3f}")
    print(f"similaridade com o controle:   média {_mean(across):.3f}, máx {max(across):.3f}")
    print(f"riscos por resposta: {[len(p.risks) for p in plans]}")


if __name__ == "__main__":
    main()
