# Evidência: repetição da resposta do modelo

**Data:** 05/11/2026
**Pergunta:** fixar `temperature` e `seed` faz o modelo devolver a mesma resposta para a mesma entrada?

A linha de IA do Portfólio reprova "modelo com resultados aleatórios ou não replicáveis". Esta medição verifica o quanto os parâmetros ajudam.

## Como foi medido

- **Entrada:** a mesma solicitação técnica fictícia, enviada pelo provedor real do projeto (`OpenRouterLLMProvider`), com o mesmo prompt e o mesmo schema estrito.
- **Repetições:** 4 por configuração, com e sem `temperature=0` e `seed=42`.
- **Comparação:** o JSON completo da resposta, por hash. Respostas que diferem em qualquer palavra contam como distintas.
- **Modelos:** somente gratuitos da OpenRouter. Um proxy local recusava qualquer modelo pago.
- **Script:** `C:\Users\Flavia\fv12\repeat.py`, fora do repositório, com o proxy `free_proxy.py`.

## Resultado

| Modelo | Parâmetros | Respostas obtidas | Respostas distintas | Tempo médio |
|---|---|---:|---:|---:|
| `nvidia/nemotron-3.5-super-vl:free` | `temperature=0`, `seed=42` | 4 de 4 | 4 | 10,3 s |
| `nvidia/nemotron-3.5-super-vl:free` | sem parâmetros | 4 de 4 | 4 | 10,2 s |
| `xingchen-agi/xing4.0-29b-a4b:free` | `temperature=0`, `seed=42` | 4 de 4 | 4 | 11,5 s |
| `xingchen-agi/xing4.0-29b-a4b:free` | sem parâmetros | 4 de 4 | 4 | 5,7 s |
| `dots-studio/dots-3-note-preview:free` | `temperature=0`, `seed=42` | 4 de 4 | 4 | 8,0 s |
| `dots-studio/dots-3-note-preview:free` | sem parâmetros | 4 de 4 | 4 | 9,8 s |
| `liquid/lfm-2.5-2.6b:free` | `temperature=0`, `seed=42` | 1 de 4 | 1 | 9,0 s |
| `liquid/lfm-2.5-2.6b:free` | sem parâmetros | 3 de 4 | 3 | 4,7 s |

O `liquid/lfm-2.5-2.6b:free` recusou a maior parte das chamadas por limite de uso (429), então não entra na conclusão.

## Conclusão

**Fixar os parâmetros não tornou a resposta repetível em nenhum dos três modelos que responderam todas as vezes.** As 4 respostas saíram diferentes com e sem `temperature=0` e `seed=42`. Isso é esperado em parte: o catálogo da OpenRouter indica que esses modelos aceitam os parâmetros, mas o provedor não garante determinismo, e o modelo pode ser servido por máquinas diferentes.

O que esta medição **não** mostra:

- se as respostas diferentes são equivalentes em conteúdo, porque a comparação é exata;
- o comportamento de `openai/gpt-5-mini`, o modelo padrão em produção, porque ele é pago e não foi usado.

## O que o projeto faz com isso

- **Guarda as condições de cada chamada:** modelo, `temperature`, `seed`, hash da entrada e hash da saída, em `llm_invocations`. Uma análise pode ser auditada mesmo que não possa ser refeita idêntica.
- **Partes determinísticas:** a busca do RAG, as métricas de recuperação, o Quality Gate e o motor de sugestão dão o mesmo resultado para a mesma entrada.
- **Próximo passo possível:** medir a equivalência de conteúdo entre as repetições, por exemplo pela similaridade dos resumos e pela coincidência dos riscos apontados. Isso também precisa de mais repetições.
