# Documentação da API (OpenAPI / Swagger)

## Onde ver

| Ambiente | Como |
|---|---|
| Desenvolvimento | Swagger interativo em http://localhost:8000/docs e ReDoc em http://localhost:8000/redoc |
| Qualquer lugar | [`openapi.json`](openapi.json), versionado neste diretório: abra em https://editor.swagger.io (*File → Import file*) ou em qualquer visualizador OpenAPI |

Em produção, `/docs`, `/redoc` e `/openapi.json` não são servidos (auditoria de segurança P1). O arquivo versionado é a referência.

## Testar pelo Swagger

1. `GET /api/v1/auth/csrf`
2. `POST /api/v1/auth/login` (ou `/register`). Se responder `202`, pegue o código no e-mail (ou no log do backend, com `EMAIL_BACKEND=console`) e confirme em `POST /api/v1/auth/login/verify`.
3. Pronto: o navegador guarda o cookie de sessão, e a página `/docs` preenche sozinha o cabeçalho `X-CSRF-Token` a partir do cookie `agenthub_csrf`.

## Como a documentação é mantida

- Os textos (descrição geral, tags, resumo e descrição de cada rota) ficam em `backend/app/api/openapi_docs.py`.
- Os requisitos de segurança de cada rota (cookie de sessão e/ou CSRF) são detectados a partir das dependências reais da rota, então não divergem do código.
- Todo erro é documentado com o formato padrão `ErrorResponse`.
- `backend/tests/test_openapi_docs.py` falha se uma rota nova não tiver documentação ou se o `openapi.json` estiver desatualizado.

Depois de mudar rotas ou schemas, regenere o arquivo:

```bash
cd backend
python scripts/export_openapi.py
```
