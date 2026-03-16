# import sys
# sys.path.append("../")
from app.models.schemas import IntentResult, GuardrailResult
from app.prompts.prompt import render_prompt
from app.services.llm_service import LLMService


class GuardrailService:
    """Service providing simple guardrail checks via the LLM.

    The service wraps low-level LLM calls that return Pydantic models and
    exposes boolean helpers used elsewhere in the codebase.  All prompts are
    rendered through `app.prompts.prompt.render_prompt`.
    """

    def __init__(self):
        # Initialize the LLM client (OpenAI or Ollama).
        self.llm = LLMService()

    async def check_farming_intent_llm(self, text: str) -> IntentResult:
        """Run the farming-intent classifier prompt and return a typed result."""
        prompt = render_prompt("intent_classifier.jinja2", text=text)
        return await self.llm.call_structured(prompt, IntentResult)

    async def check_prompt_injection_llm(self, text: str) -> GuardrailResult:
        """Run the prompt-injection guardrail prompt and return a typed result."""
        prompt = render_prompt("guardrail_check.jinja2", text=text)
        return await self.llm.call_structured(prompt, GuardrailResult)

    async def check_farming_intent(self, text: str) -> bool:
        """Return True when the text appears to be farming-related."""
        result = await self._check_farming_intent_llm(text)
        return result.intent == "farming" and result.confidence > 0.6

    async def check_prompt_injection(self, text: str) -> bool:
        """Return True when the text passes the guardrail (is safe)."""
        result = await self._check_prompt_injection_llm(text)
        return result.is_safe
