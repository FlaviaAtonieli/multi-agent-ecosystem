# Relatório de Validação

## Verificações desta versão

- compilação sintática dos módulos Python;
- autenticação, CSRF e sessões opacas;
- migrations Alembic até `0003_llm_foundation`;
- perfil `TECHNICIAN` e restrição RBAC;
- provedor mock sem chamada externa;
- endpoint seguro de status sem exposição de chave;
- plano estruturado com aprovação humana obrigatória;
- geração de `LLM Call ID`;
- hashes SHA-256 da entrada e saída;
- redaction de e-mail, senha, token e padrões de chave;
- rastreabilidade por `Trace ID`;
- ausência de conteúdo integral em `llm_invocations` por padrão;
- testes automatizados do backend.

## Comandos locais

```powershell
docker compose up --build -d
docker compose exec backend alembic current
docker compose ps
```

Para testar sem chave:

```env
LLM_ENABLED=true
LLM_PROVIDER=mock
```

Para retornar ao modo totalmente desabilitado:

```env
LLM_ENABLED=false
LLM_PROVIDER=mock
```

O adaptador OpenAI não realiza chamadas enquanto `LLM_ENABLED=false`.
