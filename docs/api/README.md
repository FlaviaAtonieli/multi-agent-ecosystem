# Documentação da API (OpenAPI / Swagger)

O arquivo [`openapi.json`](openapi.json) é o contrato da API: 68 rotas, com descrição, exemplos no caminho principal e formato de erros.

## Onde ver

| Onde | Como |
|---|---|
| **Navegador, sem instalar nada** | [Abrir no Swagger UI](https://petstore.swagger.io/?url=https://raw.githubusercontent.com/FlaviaAtonieli/multi-agent-ecosystem/main/docs/api/openapi.json). Só leitura: as chamadas de teste não funcionam daqui, porque a API não aceita outra origem |
| **Desenvolvimento local** | Swagger interativo em http://localhost:8000/docs e ReDoc em http://localhost:8000/redoc |
| **Postman ou Insomnia** | Importe o `openapi.json` |

Em produção, `/docs`, `/redoc` e `/openapi.json` não são servidos, para não expor o mapa da API. O arquivo versionado é a referência.

## Testar pelo Swagger

1. Com o backend rodando, abra http://localhost:8000/docs.
2. `GET /api/v1/auth/csrf`.
3. `POST /api/v1/auth/login` ou `/register`. Se responder `202`, pegue o código no e-mail, ou no log do backend com `EMAIL_BACKEND=console`, e confirme em `POST /api/v1/auth/login/verify`.
4. O navegador guarda o cookie de sessão, e a página preenche o cabeçalho `X-CSRF-Token` sozinha.

## Como a documentação é mantida

- `backend/app/api/openapi_docs.py`: descrição geral, tags, resumo e descrição de cada rota.
- `backend/app/api/openapi_examples.py`: descrição dos campos e exemplos.
- Os requisitos de segurança de cada rota são detectados pelas dependências reais dela, então não divergem do código.

Os testes falham se uma rota ou um campo de entrada ficar sem descrição, se um exemplo for recusado pelos schemas da API ou se o `openapi.json` estiver desatualizado.

Depois de mudar rotas ou schemas, gere o arquivo de novo:

```bash
cd backend
python scripts/export_openapi.py
```
