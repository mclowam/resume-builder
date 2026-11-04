from app.clients.adaptation import AdaptationHttpClient
from app.schemas.event import AdaptationRequestedEvent, ResumeUploadedEvent, VacancyUploadedEvent
from app.services.document import DocumentService
from app.services.resume_adaptation import ResumeAdaptationService


class AdaptationTaskService:
    def __init__(
            self,
            adaptation_client: AdaptationHttpClient,
            document_service: DocumentService,
            adaptation_service: ResumeAdaptationService,
    ):
        self._adaptation_client = adaptation_client
        self._document_service = document_service
        self._adaptation_service = adaptation_service

    async def process(self, event: AdaptationRequestedEvent) -> None:
        adaptation_id = event.data.adaptation_id
        user_id = event.data.user_id
        adaptation = await self._adaptation_client.claim(adaptation_id, user_id)
        if adaptation is None:
            return

        try:
            resume = await self._document_service.get_document(ResumeUploadedEvent(
                event_type="resume.uploaded", data={"resume_id": adaptation["resume_id"], "user_id": user_id},
            ))
            vacancy = await self._document_service.get_document(VacancyUploadedEvent(
                event_type="vacancy.uploaded", data={"vacancy_id": adaptation["vacancy_id"], "user_id": user_id},
            ))
            result = await self._adaptation_service.run(resume.text, vacancy.text)
        except Exception as error:
            await self._adaptation_client.save(adaptation_id, user_id, {
                "status": "failed", "result": None, "error": type(error).__name__,
            })
            return

        await self._adaptation_client.save(adaptation_id, user_id, {
            "status": "done", "result": result.model_dump(mode="json"), "error": None,
        })
