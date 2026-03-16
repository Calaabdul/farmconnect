# import sys
# sys.path.append("../")
from app.models.schemas import ExtractionResult
from app.prompts.prompt import render_prompt
from app.services.llm_service import LLMService
from app.services.base_agent import BaseAgent #, TaskContext
from app.models.schemas import TaskContext


class ExtractionAgent(BaseAgent):
    """Agent that extracts structured information from a message."""

    def __init__(self, context: TaskContext):
        super().__init__(context)
        self.llm = LLMService()

    async def _extract_entities_llm(self, text: str) -> ExtractionResult:
        """Internal call to the LLM returning a typed ExtractionResult."""
        prompt = render_prompt("extraction.jinja2", text=text)
        return await self.llm.call_structured(prompt, ExtractionResult)

    async def process(self) -> TaskContext:
        """Extract structured information and update context."""
        result = await self._extract_entities_llm(self.context.raw_message or "")
        self.context.extracted = result.model_dump(exclude_unset=True)
        return self.context

    async def extract_listing(self, text: str) -> dict:
        """Public helper that returns a plain dict of extracted values."""
        result = await self._extract_entities_llm(text)
        return result.model_dump(exclude_unset=True)
