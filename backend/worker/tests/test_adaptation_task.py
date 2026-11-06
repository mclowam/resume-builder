import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.schemas.event import AdaptationRequestedData, AdaptationRequestedEvent
from app.schemas.resume_adaptation import ResumeAdaptationResult
from app.services.adaptation_task import AdaptationTaskService


class TestAdaptationTask:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.event = AdaptationRequestedEvent(
            event_type="adaptation.requested",
            data=AdaptationRequestedData(adaptation_id=uuid.uuid4(), user_id=uuid.uuid4()),
        )
        self.claim = {"resume_id": str(uuid.uuid4()), "vacancy_id": str(uuid.uuid4())}
        self.client = SimpleNamespace(claim=AsyncMock(return_value=self.claim), save=AsyncMock())
        self.documents = SimpleNamespace(get_document=AsyncMock(side_effect=[
            SimpleNamespace(text="Original Python resume"), SimpleNamespace(text="Python vacancy"),
        ]))
        self.result = ResumeAdaptationResult(
            resume_text="Adapted Python resume", review={"passed": False, "issues": ["Unsupported fact"]},
        )
        self.adaptation = SimpleNamespace(run=AsyncMock(return_value=self.result))
        self.service = AdaptationTaskService(self.client, self.documents, self.adaptation)

    async def test_saves_rejected_review_as_completed_using_original_documents(self):
        await self.service.process(self.event)

        self.adaptation.run.assert_awaited_once_with("Original Python resume", "Python vacancy")
        events = [call.args[0] for call in self.documents.get_document.await_args_list]
        assert str(events[0].data.resume_id) == self.claim["resume_id"]
        assert str(events[1].data.vacancy_id) == self.claim["vacancy_id"]
        assert all(event.data.user_id == self.event.data.user_id for event in events)
        self.client.save.assert_awaited_once_with(
            self.event.data.adaptation_id, self.event.data.user_id,
            {"status": "done", "result": self.result.model_dump(mode="json"), "error": None},
        )

    async def test_duplicate_does_not_load_documents_or_call_llm(self):
        self.client.claim.return_value = None
        await self.service.process(self.event)
        self.documents.get_document.assert_not_awaited()
        self.adaptation.run.assert_not_awaited()
        self.client.save.assert_not_awaited()

    @pytest.mark.parametrize("name", ["document", "llm"])
    async def test_document_and_llm_errors_are_saved_without_private_error_text(self, name):
        stage = self.documents.get_document if name == "document" else self.adaptation.run
        stage.side_effect = ValueError("private original text and key")
        await self.service.process(self.event)
        self.client.save.assert_awaited_once_with(
            self.event.data.adaptation_id, self.event.data.user_id,
            {"status": "failed", "result": None, "error": "ValueError"},
        )

    async def test_claim_and_save_failures_propagate(self):
        self.client.claim.side_effect = ConnectionError()
        with pytest.raises(ConnectionError):
            await self.service.process(self.event)
        self.client.save.assert_not_awaited()
        self.client.claim.side_effect = None
        self.client.save.side_effect = ConnectionError()
        with pytest.raises(ConnectionError):
            await self.service.process(self.event)
        assert self.client.save.await_count == 1
        assert self.client.save.call_args.args[2]["status"] == "done"

    async def test_cancellation_does_not_save_failure(self):
        self.adaptation.run.side_effect = asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):
            await self.service.process(self.event)
        self.client.save.assert_not_awaited()
