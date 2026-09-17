from pydantic import BaseModel

from app.llm.schemas import LLMPlan, strict_json_schema


def test_strict_json_schema_patches_the_top_level():
    schema = strict_json_schema(LLMPlan)
    assert set(schema["required"]) == set(schema["properties"].keys())
    assert schema["additionalProperties"] is False


class _NestedThing(BaseModel):
    label: str
    weight: int = 0


class _WithNestedModel(BaseModel):
    name: str
    thing: _NestedThing
    maybe_thing: _NestedThing | None = None


def test_strict_json_schema_also_patches_nested_defs():
    """Security review (PR #35): strict_json_schema only patched the schema's
    top level -- a nested BaseModel field lands in Pydantic's "$defs" (every
    nested model, however deep, flattened there with $ref pointing to it),
    left untouched, reproducing the exact 400 "invalid_json_schema" this
    function exists to prevent the moment a schema like this is used with a
    genuinely strict-mode model. LLMPlan itself has no nested field today,
    so this needed a schema built for the test, not LLMPlan."""
    schema = strict_json_schema(_WithNestedModel)

    assert set(schema["required"]) == {"name", "thing", "maybe_thing"}
    assert schema["additionalProperties"] is False

    nested = schema["$defs"]["_NestedThing"]
    assert set(nested["required"]) == {"label", "weight"}
    assert nested["additionalProperties"] is False
