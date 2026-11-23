"""Cria os comitês de exemplo (jurídico, aptidão física e mental, financeiro) e as
Agent Skills de cada um, com um relator por comitê, pela API da plataforma.

Quem roda vira dono dos comitês e das skills. A senha e o código do e-mail são
digitados no terminal e não ficam gravados em lugar nenhum.

    python scripts/criar_comites_exemplo.py
    python scripts/criar_comites_exemplo.py --base-url http://localhost:8000

Pode rodar de novo: comitês e skills que já existem com o mesmo nome são mantidos.
"""

import argparse
import getpass
import json
import sys
from pathlib import Path

import httpx

DADOS = Path(__file__).with_name("comites_exemplo.json")
PRODUCAO = "https://jolly-grass-0a3af3f10.2.azurestaticapps.net"
API = "/api/v1"
PERSONA_MAX = 4000


def skill_payload(agente: dict, regras_comuns: str, clan_id: str | None) -> dict:
    persona = f"{agente['persona']} {regras_comuns}"
    if len(persona) > PERSONA_MAX:
        raise ValueError(f"A persona de {agente['name']} passou de {PERSONA_MAX} caracteres.")
    return {
        "visibility": "CLAN",
        "clan_id": clan_id,
        "name": agente["name"],
        "version": "1.0",
        "author_origin": "Flav.IA, comitê de exemplo",
        "domain": agente["domain"],
        "objective": agente["objective"],
        "capabilities": agente["capabilities"],
        "expected_inputs": agente["expected_inputs"],
        "produced_outputs": agente["produced_outputs"],
        "operating_limits": [
            "Só analisa a solicitação, os anexos e a base do comitê",
            "Não decide: recomenda, e uma pessoa decide",
        ],
        "input_contract_ref": "solicitacao_analise_schema.v1",
        "output_contract_ref": "resposta_especialista_schema.v1",
        "security_rules": [
            "Não inventa fontes, números nem documentos",
            "Dados pessoais só pelas iniciais",
        ],
        "usage_examples": [f"{agente['objective']}"],
        "validation_criteria": [
            "Cada ponto cita o documento ou o trecho de origem",
            "A confiança cai quando falta documento de apoio",
        ],
        "uses_external_services": False,
        "persona_instructions": persona,
    }


class Plataforma:
    def __init__(self, base_url: str) -> None:
        self.client = httpx.Client(base_url=base_url, timeout=60)

    def _csrf(self) -> dict[str, str]:
        token = next((v for k, v in self.client.cookies.items() if "csrf" in k.lower()), "")
        return {"X-CSRF-Token": token}

    def get(self, path: str) -> httpx.Response:
        return self.client.get(API + path)

    def post(self, path: str, body: dict | None = None) -> httpx.Response:
        return self.client.post(API + path, json=body or {}, headers=self._csrf())

    def entrar(self) -> dict:
        self.get("/auth/csrf").raise_for_status()
        email = input("E-mail da sua conta: ").strip()
        senha = getpass.getpass("Senha (não aparece enquanto digita): ")
        resposta = self.post("/auth/login", {"email": email, "password": senha})
        if resposta.status_code == 202:
            codigo = input("Código de 6 dígitos enviado ao seu e-mail: ").strip()
            resposta = self.post("/auth/login/verify", {"code": codigo})
        if resposta.status_code != 200:
            sys.exit(f"Não foi possível entrar ({resposta.status_code}): {resposta.text}")
        return resposta.json()["user"]


def achar_comite(plataforma: Plataforma, comite: dict, email: str) -> str | None:
    comites = plataforma.get("/clans").json()
    exato = [c for c in comites if c["name"].lower() == comite["nome"].lower()]
    parecidos = [
        c for c in comites if any(trecho in c["name"].lower() for trecho in comite["procura_existente"])
    ]
    for candidato in exato or parecidos:
        detalhe = plataforma.get(f"/clans/{candidato['id']}").json()
        membro = any(m["email"].lower() == email.lower() for m in detalhe["members"])
        if not membro and detalhe["is_open"]:
            membro = plataforma.post(f"/clans/{candidato['id']}/join").status_code == 200
        if membro:
            print(f"  usando o comitê existente \"{candidato['name']}\"")
            return str(candidato["id"])
    return None


def criar(plataforma: Plataforma, dados: dict, email: str) -> None:
    for comite in dados["comites"]:
        print(f"\n{comite['nome']}")
        clan_id = achar_comite(plataforma, comite, email)
        if clan_id is None:
            resposta = plataforma.post(
                "/clans",
                {
                    "name": comite["nome"],
                    "is_open": True,
                    "skills_policy": "OWNER_ONLY",
                    "members_policy": "ALL_MEMBERS",
                },
            )
            resposta.raise_for_status()
            clan_id = resposta.json()["id"]
            print("  comitê criado, aberto ao público")

        existentes = {s["name"].lower() for s in plataforma.get(f"/clans/{clan_id}/skills").json()}
        for agente in comite["agentes"]:
            if agente["name"].lower() in existentes:
                print(f"  = {agente['name']} (já existe)")
                continue
            payload = skill_payload(agente, comite["regras_comuns"], clan_id)
            resposta = plataforma.post("/agent-skills", payload)
            if resposta.status_code != 201:
                print(f"  ! {agente['name']}: {resposta.status_code} {resposta.text}")
                continue
            vinculo = plataforma.post(f"/clans/{clan_id}/skills", {"agent_skill_id": resposta.json()["id"]})
            if vinculo.status_code not in (201, 409):
                print(f"  ! {agente['name']} criada, mas não entrou no comitê: {vinculo.text}")
                continue
            print(f"  + {agente['name']} ({agente['domain']})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", default=PRODUCAO)
    args = parser.parse_args()
    dados = json.loads(DADOS.read_text(encoding="utf-8"))
    plataforma = Plataforma(args.base_url)
    print(f"Plataforma: {args.base_url}")
    usuario = plataforma.entrar()
    print(f"Entrou como {usuario['name']}")
    criar(plataforma, dados, usuario["email"])
    print("\nPronto. Os comitês aparecem em Comitês.")


if __name__ == "__main__":
    main()
