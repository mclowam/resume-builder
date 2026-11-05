import json

from app.interfaces.llm import ILLMClient
from app.prompts.critic import CRITIC_PROMPT
from app.schemas.critic import CriticResult
from app.schemas.tailor import TailorResult


class CriticAgent:
    def __init__(self, llm_client: ILLMClient):
        self._llm_client = llm_client

    async def run(self, resume_text: str, vacancy_text: str, tailor_result: TailorResult) -> CriticResult:
        if not resume_text.strip() or not vacancy_text.strip():
            raise ValueError("Resume and vacancy text must not be empty")
        response = await self._llm_client.generate(
            CRITIC_PROMPT,
            json.dumps({
                "resume": resume_text,
                "vacancy": vacancy_text,
                "tailor_result": tailor_result.model_dump(),
            }, ensure_ascii=False),
        )
        review = CriticResult.model_validate_json(response)
        original = " ".join(resume_text.split()).casefold()
        adapted = " ".join(tailor_result.resume_text.split()).casefold()
        if adapted == original:
            return CriticResult(passed=False, issues=[
                "Результат повторяет исходное резюме. Требуется адаптировать профиль и акценты под вакансию.",
            ])
        return review
