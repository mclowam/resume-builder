import argparse
import asyncio
from pathlib import Path

from app.agents.critic import CriticAgent
from app.agents.matcher import MatcherAgent
from app.agents.tailor import TailorAgent
from app.clients.llm import LLMHttpClient
from app.core.core import settings
from app.schemas.tailor import TailorResult
from app.services.resume_adaptation import ResumeAdaptationService


async def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Adapt a resume or review an existing adaptation with a real LLM.")
    parser.add_argument("resume", type=Path, help="Original resume text file (UTF-8)")
    parser.add_argument("vacancy", type=Path, help="Vacancy text file (UTF-8)")
    parser.add_argument("output", type=Path, help="Output JSON file")
    parser.add_argument("--model", required=True, help="Chat completion model")
    parser.add_argument("--tailored-resume", type=Path, help="Review this text file with Critic only")
    args = parser.parse_args(argv)

    inputs = [args.resume, args.vacancy]
    if args.tailored_resume is not None:
        inputs.append(args.tailored_resume)
    if args.output.resolve() in [path.resolve() for path in inputs]:
        parser.error("Output must not overwrite an input file")

    resume_text = args.resume.read_text(encoding="utf-8-sig")
    vacancy_text = args.vacancy.read_text(encoding="utf-8-sig")
    tailor_result = None
    if args.tailored_resume is not None:
        tailor_result = TailorResult(resume_text=args.tailored_resume.read_text(encoding="utf-8-sig"))

    client = LLMHttpClient(settings.OPENAI_BASE_URL, settings.OPENAI_API_KEY, args.model)
    try:
        critic = CriticAgent(client)
        if tailor_result is not None:
            result = await critic.run(resume_text, vacancy_text, tailor_result)
        else:
            service = ResumeAdaptationService(MatcherAgent(client), TailorAgent(client), critic)
            result = await service.run(resume_text, vacancy_text)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
