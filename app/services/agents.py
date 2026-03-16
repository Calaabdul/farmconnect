from __future__ import annotations
from typing import List

from app.models.schemas import TaskContext
from app.services.base_agent import BaseAgent  # , TaskContext
from app.services.guardrail_service import GuardrailService
from app.services.extraction_service import ExtractionAgent


class IntentAgent(BaseAgent):
    """Agent responsible for classifying intent in the context."""

    def __init__(self, context: TaskContext):
        super().__init__(context)
        self.guard = GuardrailService()

    async def check_farming_intent_llm(self, text: str):
        """Internal method to check farming intent."""
        return await self.guard._check_farming_intent_llm(text)

    async def process(self) -> TaskContext:
        """Classify intent and update context."""
        result = await self.check_farming_intent_llm(self.context.raw_message or "")
        self.context.intent = result.intent
        self.context.confidence = result.confidence
        return self.context


class GuardrailAgent(BaseAgent):
    """Agent enforcing guardrails before other processing steps."""

    def __init__(self, context: TaskContext):
        super().__init__(context)
        self.guard = GuardrailService()

    async def check_prompt_injection_llm(self, text: str):
        """Internal method to check prompt injection."""
        return await self.guard._check_prompt_injection_llm(text)

    async def process(self) -> TaskContext:
        """Perform guardrail checks and update context."""
        # Check prompt injection
        injection_result = await self.check_prompt_injection_llm(
            self.context.raw_message or ""
        )
        if not injection_result.is_safe:
            raise ValueError("Prompt injection detected")

        # Check farming intent
        if not await self.guard.check_farming_intent(self.context.raw_message or ""):
            raise ValueError("Non farming intent")

        return self.context


class AgentPipeline:
    """Pipeline class that manages and runs agent steps in sequence."""

    def __init__(self):
        self.steps: List[BaseAgent] = []

    def add_step(self, agent: BaseAgent):
        """Add an agent step to the pipeline."""
        self.steps.append(agent)
        return self

    async def run(self, context: TaskContext) -> TaskContext:
        """Run all agent steps in sequence."""
        current_context = context
        for step in self.steps:
            step.context = current_context
            current_context = await step.process()
        return current_context


# Convenience function to create a standard pipeline
def create_standard_pipeline(context: TaskContext) -> AgentPipeline:
    """Create a standard agent pipeline with guardrail, intent, and extraction."""
    pipeline = AgentPipeline()
    pipeline.add_step(GuardrailAgent(context))
    pipeline.add_step(IntentAgent(context))
    pipeline.add_step(ExtractionAgent(context))
    return pipeline


# if __name__ == "__main__":
#     # Example of running the agents in sequence
#     context = TaskContext(
#         # user_id="123",
#         phone="+2348140516438",
#         raw_message="Looking to buy 100kg of maize for under 500 naira.",
#     )

#     import asyncio

#     async def main():
#         pipeline = create_standard_pipeline(context)
#         result = await pipeline.run(context)
#         print("Final context:", result)

#     asyncio.run(main())
