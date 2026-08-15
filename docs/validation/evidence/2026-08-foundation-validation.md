# Evidência de Validação - Fundação da Aplicação

**Consolidação documental:** 02/08/2026  
**Escopo:** autenticação, solicitações, rastreabilidade e integração simulada com modelos

## Origem dos registros

Este documento consolida os arquivos de validação produzidos durante a montagem da base. Os registros não estavam na mesma etapa do projeto, por isso os resultados são apresentados separadamente.

## Fundação de autenticação e orquestração

Os registros da versão com a migration `0002_orchestration` informam:

| Verificação | Resultado registrado |
|---|---|
| `python -m compileall -q app tests` | Concluído |
| `pytest -q` | 6 testes aprovados |
| `alembic upgrade head` em banco SQLite limpo | `0002_orchestration (head)` |
| Análise sintática de TypeScript/TSX | Concluída |
| Build completo do frontend | Pendente no ambiente local |

O uso de SQLite serviu como verificação estrutural da migration. A aplicação oficial utiliza PostgreSQL, portanto a validação final deve ser repetida nesse banco.

## Fundação de provedores de modelo

O pacote posterior acrescentou:

- migration `0003_llm_foundation`;
- dois testes para autorização, provedor simulado e rastreabilidade;
- validação de hashes e mascaramento de conteúdo;
- verificação de que o conteúdo integral não é persistido por padrão.

O código disponível contém oito testes no total: cinco de autenticação, um de orquestração e dois da integração simulada. Como os documentos anteriores registram apenas seis testes, o total de oito deve ser confirmado por uma nova execução no ambiente local antes de ser usado como evidência final.

## Revalidação recomendada

Na raiz do projeto:

```powershell
docker compose down
docker compose up --build -d
docker compose ps
```

Validar o backend:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
docker compose exec backend alembic current
```

Resultado esperado da migration atual:

```text
0003_llm_foundation (head)
```

Executar os testes:

```powershell
docker run --rm `
  --mount "type=bind,source=$((Get-Location).Path)\backend,target=/app" `
  -w /app `
  python:3.12-slim `
  sh -c "pip install --no-cache-dir -r requirements-dev.txt && pytest -v"
```

Validar o frontend:

```powershell
docker compose build frontend --no-cache
```

## Evidências que devem ser anexadas após a execução

- data e horário;
- branch e commit;
- saída resumida do `docker compose ps`;
- revisão atual do Alembic;
- quantidade de testes aprovados;
- resultado do build do frontend;
- print do health check;
- falhas encontradas e respectivas issues.

## Limitações deste registro

- Não há commit identificado nos arquivos originais de validação.
- O build completo do frontend não foi registrado como concluído.
- A migration `0003` precisa ser confirmada no PostgreSQL.
- Este documento não substitui o relatório de validação da PoC nem a medição dos KPIs do RFC.
