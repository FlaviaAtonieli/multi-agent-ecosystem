"""A documentação da API precisa ser útil e continuar verdadeira.

Os exemplos passam pelos mesmos schemas Pydantic que a API usa: um exemplo que a
própria API recusaria faz o teste falhar.
"""

import importlib
import pkgutil
import re

import pytest
from pydantic import BaseModel, TypeAdapter

import app.schemas
from app.main import app as fastapi_app

PREFIX = "/api/v1"
METHODS = {"get", "post", "put", "patch", "delete"}

# O caminho principal de quem usa a API: cadastro, comitê, solicitação, execução e resultado.
MAIN_OPERATIONS = [
    ("post", "/auth/register"),
    ("post", "/auth/login"),
    ("post", "/clans"),
    ("post", "/clans/{clan_id}/skills"),
    ("post", "/agent-skills"),
    ("post", "/agent-skills/suggestions"),
    ("post", "/requests"),
    ("post", "/agent-skills/requests/{request_id}/start"),
    ("post", "/agent-skills/requests/{request_id}/ask/start"),
    ("post", "/requests/{request_id}/review"),
]
MAIN_RESPONSES = [
    ("post", "/agent-skills/suggestions", "200"),
    ("post", "/requests", "201"),
    ("get", "/orchestrations/{trace_id}/artifacts", "200"),
]


def _schema() -> dict:
    return fastapi_app.openapi()


def _models() -> dict[str, type[BaseModel]]:
    models: dict[str, type[BaseModel]] = {}
    for module in pkgutil.iter_modules(app.schemas.__path__):
        loaded = importlib.import_module(f"app.schemas.{module.name}")
        for name, value in vars(loaded).items():
            if isinstance(value, type) and issubclass(value, BaseModel):
                models[name] = value
    return models


def _ref_name(schema: dict) -> str:
    return schema["$ref"].rsplit("/", 1)[-1]


def _request_schemas() -> set[str]:
    names: set[str] = set()
    for operations in _schema()["paths"].values():
        for method, operation in operations.items():
            if method in METHODS:
                for content in operation.get("requestBody", {}).get("content", {}).values():
                    names.update(re.findall(r"schemas/(\w+)", str(content.get("schema", {}))))
    return names


def test_every_field_sent_to_the_api_is_described() -> None:
    components = _schema()["components"]["schemas"]
    missing = [
        f"{name}.{field}"
        for name in _request_schemas()
        for field, spec in components[name].get("properties", {}).items()
        if not spec.get("description")
    ]

    assert missing == []


@pytest.mark.parametrize(("method", "path"), MAIN_OPERATIONS)
def test_main_operation_has_a_valid_request_example(method: str, path: str) -> None:
    body = _schema()["paths"][PREFIX + path][method]["requestBody"]["content"]["application/json"]

    assert "example" in body, f"{method} {path} sem exemplo"
    schema = body["schema"]
    # Corpo opcional aparece como anyOf com null.
    reference = next(item for item in schema.get("anyOf", [schema]) if "$ref" in item)
    _models()[_ref_name(reference)].model_validate(body["example"])


@pytest.mark.parametrize(("method", "path", "code"), MAIN_RESPONSES)
def test_main_response_has_a_valid_example(method: str, path: str, code: str) -> None:
    body = _schema()["paths"][PREFIX + path][method]["responses"][code]["content"]["application/json"]

    assert "example" in body, f"{method} {path} sem exemplo de resposta"
    schema = body["schema"]
    if schema.get("type") == "array":
        TypeAdapter(list[_models()[_ref_name(schema["items"])]]).validate_python(body["example"])
    else:
        _models()[_ref_name(schema)].model_validate(body["example"])


@pytest.mark.parametrize(
    ("path", "media_type"),
    [
        ("/orchestrations/{trace_id}/artifacts.zip", "application/zip"),
        ("/orchestrations/{trace_id}/artifacts/{artifact_id}/download", "application/octet-stream"),
    ],
)
def test_downloads_are_documented_as_files(path: str, media_type: str) -> None:
    content = _schema()["paths"][PREFIX + path]["get"]["responses"]["200"]["content"]

    assert content[media_type]["schema"] == {"type": "string", "format": "binary"}


def test_servers_are_listed() -> None:
    urls = [server["url"] for server in _schema()["servers"]]

    assert "http://localhost:8000" in urls
    assert any(url.startswith("https://") for url in urls)
