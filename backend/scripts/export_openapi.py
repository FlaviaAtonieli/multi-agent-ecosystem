"""Exporta o schema OpenAPI para docs/api/openapi.json.

Em produção /docs e /openapi.json não são servidos (auditoria de segurança P1);
o arquivo exportado é a documentação versionada da API. Rode depois de mudar
rotas ou schemas:

    cd backend && python scripts/export_openapi.py
"""

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

OUTPUT = BACKEND_DIR.parent / "docs" / "api" / "openapi.json"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OpenAPI exportado para {OUTPUT}")


if __name__ == "__main__":
    main()
