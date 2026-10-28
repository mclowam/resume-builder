from app.agents.critic import CriticAgent
from app.agents.matcher import MatcherAgent
from app.agents.tailor import TailorAgent
from app.schemas.resume_adaptation import ResumeAdaptationResult


class ResumeAdaptationService:
    def __init__(
            self,
            matcher_agent: MatcherAgent,
            tailor_agent: TailorAgent,
            critic_agent: CriticAgent,
    ):
        self._matcher_agent = matcher_agent
        self._tailor_agent = tailor_agent
        self._critic_agent = critic_agent

    async def run(self, resume_text: str, vacancy_text: str) -> ResumeAdaptationResult:
        match_result = await self._matcher_agent.run(resume_text, vacancy_text)
        tailor_result = await self._tailor_agent.run(resume_text, vacancy_text, match_result)
        review = await self._critic_agent.run(resume_text, vacancy_text, tailor_result)

        return ResumeAdaptationResult(resume_text=tailor_result.resume_text, review=review)
