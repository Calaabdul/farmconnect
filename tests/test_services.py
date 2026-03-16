import asyncio
from app.services.agents import create_standard_pipeline
from app.services.base_agent import TaskContext
from app.models.schemas import IntentResult, ExtractionResult, GuardrailResult


async def test_agents_flow(monkeypatch):
    ctx = TaskContext(raw_message="I want to buy corn")

    # stub service methods
    async def dummy_check_farming(text):
        return True

    async def dummy_check_injection(text):
        return True

    async def dummy_intent_llm(text):
        return IntentResult(intent="farming", confidence=0.9)

    async def dummy_injection_llm(text):
        return GuardrailResult(is_safe=True)

    async def dummy_extract_llm(text):
        return ExtractionResult(role="buyer", product_name="corn")

    monkeypatch.setattr(
        "app.services.guardrail_service.GuardrailService.check_farming_intent",
        dummy_check_farming,
    )
    monkeypatch.setattr(
        "app.services.guardrail_service.GuardrailService.check_prompt_injection",
        dummy_check_injection,
    )
    monkeypatch.setattr(
        "app.services.guardrail_service.GuardrailService._check_farming_intent_llm",
        dummy_intent_llm,
    )
    monkeypatch.setattr(
        "app.services.guardrail_service.GuardrailService._check_prompt_injection_llm",
        dummy_injection_llm,
    )
    monkeypatch.setattr(
        "app.services.extraction_service.ExtractionAgent._extract_entities_llm",
        dummy_extract_llm,
    )

    pipeline = create_standard_pipeline(ctx)
    result = await pipeline.run(ctx)

    assert result.intent == "farming"
    assert result.confidence == 0.9
    assert result.extracted["product_name"] == "corn"


def test_agents_flow_sync():
    """Sync wrapper for the async test."""
    asyncio.run(test_agents_flow())
