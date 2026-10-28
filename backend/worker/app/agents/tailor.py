import json

from app.interfaces.llm import ILLMClient
from app.prompts.tailor import TAILOR_PROMPT
from app.schemas.matcher import MatchResult
from app.schemas.tailor import TailorResult


class TailorAgent:
    def __init__(self, llm_client: ILLMClient):
        self._llm_client = llm_client

    async def run(self, resume_text: str, vacancy_text: str, match_result: MatchResult) -> TailorResult:
        if not resume_text.strip() or not vacancy_text.strip():
            raise ValueError("Resume and vacancy text must not be empty")
        response = await self._llm_client.generate(
            TAILOR_PROMPT,
            json.dumps({
                "resume": resume_text,
                "vacancy": vacancy_text,
                "match_result": match_result.model_dump(),
            }, ensure_ascii=False),
        )
        return TailorResult.model_validate_json(response)
