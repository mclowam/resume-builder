import json

from app.interfaces.llm import ILLMClient
from app.prompts.matcher import MATCHER_PROMPT
from app.schemas.matcher import MatchResult


class MatcherAgent:
    def __init__(self, llm_client: ILLMClient):
        self._llm_client = llm_client

    async def run(self, resume_text: str, vacancy_text: str) -> MatchResult:
        if not resume_text.strip() or not vacancy_text.strip():
            raise ValueError("Resume and vacancy text must not be empty")
        response = await self._llm_client.generate(
            MATCHER_PROMPT,
            json.dumps({"resume": resume_text, "vacancy": vacancy_text}, ensure_ascii=False),
        )
        return MatchResult.model_validate_json(response)
