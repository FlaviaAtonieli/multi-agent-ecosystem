"""Cria o clã "Desenvolvimento de Jogos" com 5 Agent Skills, pela API.

Cenário de teste: uma orquestração que pede o código-fonte de um jogo simples.
As skills não conversam entre si (cada uma recebe a mesma solicitação), então
as personas dividem o trabalho: só a de Programação escreve o código do jogo;
as outras entregam o próprio documento. Assim sai um pacote coerente, em vez de
cinco versões concorrentes do mesmo jogo.

Uso (a senha vem de variável de ambiente, nunca da linha de comando):

    FLAVIA_API=https://<site>/api/v1 FLAVIA_EMAIL=voce@exemplo.com FLAVIA_PASSWORD=... \\
        python scripts/create_game_dev_clan.py

Se a conta pedir código de login (navegador novo), entre uma vez pelo site antes.
"""

import os
import sys

import httpx

CLAN_NAME = "Desenvolvimento de Jogos"

_COMMON = {
    "version": "1.0.0",
    "author_origin": "Cenário de teste do Flav.IA",
    "input_contract_ref": "solicitacao_analise_schema.v1",
    "output_contract_ref": "resposta_especialista_schema.v1",
    "security_rules": [
        "Não executar código nem alterar sistemas: os arquivos são propostas.",
        "Não incluir dependências externas, chaves ou dados pessoais.",
    ],
}

SKILLS = [
    {
        "name": "Programação de Jogos Web",
        "domain": "programacao_jogos",
        "objective": "Escrever o código-fonte jogável de jogos simples para navegador.",
        "capabilities": [
            "HTML5, CSS e JavaScript sem bibliotecas",
            "Loop de jogo e estado",
            "Entrada por mouse e teclado",
        ],
        "expected_inputs": ["Regras do jogo", "Plataforma alvo"],
        "produced_outputs": ["index.html", "style.css", "game.js"],
        "operating_limits": ["Só jogos 2D simples, que rodam abrindo o index.html"],
        "validation_criteria": [
            "O jogo abre no navegador sem erros no console",
            "Uma partida completa termina com vitória ou derrota",
        ],
        "persona_instructions": (
            "Você é a única skill do clã que escreve o código-fonte do jogo. Entregue em generated_files "
            "exatamente três arquivos completos e funcionais: index.html, style.css e game.js. "
            "O jogo precisa rodar abrindo o index.html direto no navegador, sem servidor, build "
            "ou biblioteca externa. Use "
            "JavaScript puro em game.js, carregado com <script src=\"game.js\"> no fim do body. Não deixe "
            "trechos para completar, TODO ou pseudocódigo. Dê ids estáveis aos elementos principais "
            "(tabuleiros, mensagem de status, botão de reiniciar) e mostre o fim de jogo em texto na página."
        ),
    },
    {
        "name": "Game Design",
        "domain": "game_design",
        "objective": "Definir regras, fluxo de turnos, feedback e condições de vitória.",
        "capabilities": ["Regras e balanceamento", "Fluxo de partida", "Feedback ao jogador"],
        "expected_inputs": ["Ideia do jogo", "Público"],
        "produced_outputs": ["GDD.md"],
        "operating_limits": ["Não escreve código"],
        "validation_criteria": ["Toda regra tem condição verificável", "Vitória e derrota estão definidas"],
        "persona_instructions": (
            "Você define o design do jogo. Não escreva código-fonte. Entregue em generated_files um único "
            "arquivo GDD.md, curto, com regras, preparação, turnos, feedback de acerto, erro e afundamento, "
            "condição de vitória e derrota, e o que fica fora desta primeira versão."
        ),
    },
    {
        "name": "Metodologia de Desenvolvimento de Jogos",
        "domain": "metodologia_desenvolvimento",
        "objective": "Organizar o desenvolvimento em incrementos pequenos e verificáveis.",
        "capabilities": ["Backlog e MVP", "Critérios de aceite", "Iterações curtas"],
        "expected_inputs": ["Escopo do jogo"],
        "produced_outputs": ["BACKLOG.md"],
        "operating_limits": ["Não escreve código"],
        "validation_criteria": ["Cada história tem critério de aceite", "O MVP cabe em uma iteração"],
        "persona_instructions": (
            "Você organiza o trabalho. Não escreva código-fonte. Entregue em generated_files um único "
            "BACKLOG.md com histórias de usuário do MVP em ordem de prioridade, cada uma com critério "
            "de aceite verificável, e o que fica para depois."
        ),
    },
    {
        "name": "Qualidade e Testes de Jogos",
        "domain": "qualidade_jogos",
        "objective": "Planejar como verificar que o jogo funciona e encontrar casos de borda.",
        "capabilities": ["Casos de teste manuais", "Casos de borda de regras", "Critérios de pronto"],
        "expected_inputs": ["Regras do jogo"],
        "produced_outputs": ["PLANO_DE_TESTES.md"],
        "operating_limits": ["Não escreve o código do jogo"],
        "validation_criteria": [
            "Cada caso tem passos e resultado esperado",
            "Casos de borda das regras cobertos",
        ],
        "persona_instructions": (
            "Você cuida da qualidade. Não escreva o código do jogo. Entregue em generated_files um único "
            "PLANO_DE_TESTES.md com casos numerados (passos e resultado esperado), incluindo casos de borda: "
            "tiro repetido na mesma casa, navios que não se sobrepõem nem saem do tabuleiro, fim de jogo e "
            "reinício."
        ),
    },
    {
        "name": "UX e Acessibilidade de Jogos",
        "domain": "ux_acessibilidade_jogos",
        "objective": "Garantir que o jogo seja claro e jogável por mais pessoas.",
        "capabilities": ["Feedback visual", "Teclado e leitor de tela", "Contraste e daltonismo"],
        "expected_inputs": ["Interface do jogo"],
        "produced_outputs": ["ACESSIBILIDADE.md"],
        "operating_limits": ["Não escreve o código do jogo"],
        "validation_criteria": ["Recomendações verificáveis", "Jogável só com teclado"],
        "persona_instructions": (
            "Você cuida de UX e acessibilidade. Não escreva o código do jogo. Entregue em generated_files um "
            "único ACESSIBILIDADE.md com recomendações verificáveis: jogar só com teclado, estados que não "
            "dependem só de cor (acerto, erro, afundado), contraste, textos para leitor de tela e mensagens "
            "de status."
        ),
    },
]


def main() -> int:
    api = os.environ["FLAVIA_API"].rstrip("/")
    client = httpx.Client(timeout=60)
    client.get(f"{api}/auth/csrf")
    headers = {"X-CSRF-Token": client.cookies["agenthub_csrf"]}
    login = client.post(
        f"{api}/auth/login",
        json={"email": os.environ["FLAVIA_EMAIL"], "password": os.environ["FLAVIA_PASSWORD"]},
        headers=headers,
    )
    if login.status_code != 200 or "user" not in login.json():
        print("Login não concluído (código por e-mail?). Entre pelo site uma vez e tente de novo.")
        return 1
    headers = {"X-CSRF-Token": client.cookies["agenthub_csrf"]}

    mine = client.get(f"{api}/clans", params={"mine": "true"}).json()
    existing = next((clan for clan in mine if clan["name"] == CLAN_NAME), None)
    if existing:
        clan_id = existing["id"]
        print(f"Clã já existia: {CLAN_NAME} ({clan_id})")
    else:
        clan = client.post(f"{api}/clans", json={"name": CLAN_NAME}, headers=headers)
        clan.raise_for_status()
        clan_id = clan.json()["id"]
        print(f"Clã criado: {CLAN_NAME} ({clan_id})")

    for skill in SKILLS:
        payload = {**_COMMON, **skill, "visibility": "CLAN", "clan_id": clan_id}
        created = client.post(f"{api}/agent-skills", json=payload, headers=headers)
        if created.status_code != 201:
            print(f"  falhou: {skill['name']} -> {created.status_code} {created.text[:500]}")
            return 1
        print(f"  skill criada: {skill['name']}")

    in_clan = client.get(f"{api}/clans/{clan_id}/skills").json()
    print(f"Skills no clã: {len(in_clan)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
