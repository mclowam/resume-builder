import asyncio
import json
import os
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.adaptation import Adaptation
from app.models.resume import Resume
from app.models.vacancy import Vacancy
from app.models.outbox import OutboxEvent
from app.messaging.outbox_dispatcher import OutboxDispatcher
from app.messaging.redis_publisher import RedisPublisher
from app.repositories.adaptation import AdaptationRepository
from app.schemas.adaptation import AdaptationCreateSchema, AdaptationFinishSchema


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "TEST_DATABASE_URL is required")
class AdaptationRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = f"adaptation_test_{uuid.uuid4().hex}"
        self.engine = create_async_engine(
            os.environ["TEST_DATABASE_URL"],
            connect_args={"server_settings": {"search_path": self.schema}},
        )
        self.addAsyncCleanup(self.engine.dispose)
        async with self.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.addAsyncCleanup(self.drop_schema)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.user_id = uuid.uuid4()
        self.resume_id = uuid.uuid4()
        self.vacancy_ids = [uuid.uuid4(), uuid.uuid4()]
        async with self.sessions() as session:
            session.add(Resume(
                id=self.resume_id, user_id=self.user_id,
                file_url="http://minio/resumes/original.pdf", embedding=[0.1, 0.2],
            ))
            for vacancy_id, vacancy_text in zip(self.vacancy_ids, ("Python", "PostgreSQL")):
                session.add(Vacancy(id=vacancy_id, user_id=self.user_id, text=vacancy_text))
            await session.commit()

    async def drop_schema(self):
        async with self.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))

    async def test_separate_results_for_two_vacancies_preserve_original(self):
        adaptations = []
        async with self.sessions() as session:
            repository = AdaptationRepository(session)
            for vacancy_id in self.vacancy_ids:
                result = await repository.add(
                    AdaptationCreateSchema(resume_id=self.resume_id, vacancy_id=vacancy_id), self.user_id,
                )
                self.assertEqual(result.status, "pending")
                self.assertIsNone(result.result)
                self.assertIsNone(result.error)
                adaptations.append(result)
        self.assertNotEqual(adaptations[0].id, adaptations[1].id)

        async with self.sessions() as session:
            for adaptation, result_text, review in zip(adaptations, ("Python resume", "SQL resume"), (
                {"passed": True, "issues": []}, {"passed": False, "issues": ["Unsupported fact"]},
            )):
                stored = await session.get(Adaptation, adaptation.id)
                stored.status = "done"
                stored.result = {"resume_text": result_text, "review": review}
            await session.commit()

        async with self.sessions() as session:
            repository = AdaptationRepository(session)
            first = await repository.get_by_id(adaptations[0].id, self.user_id)
            second = await repository.get_by_id(adaptations[1].id, self.user_id)
            self.assertEqual(first.result.resume_text, "Python resume")
            self.assertTrue(first.result.review.passed)
            self.assertEqual(second.result.resume_text, "SQL resume")
            self.assertFalse(second.result.review.passed)
            self.assertEqual(second.result.review.issues, ["Unsupported fact"])
            original = await session.get(Resume, self.resume_id)
            self.assertEqual(original.file_url, "http://minio/resumes/original.pdf")
            self.assertEqual(original.embedding, [0.1, 0.2])
            for vacancy_id, expected in zip(self.vacancy_ids, ("Python", "PostgreSQL")):
                self.assertEqual((await session.get(Vacancy, vacancy_id)).text, expected)

    async def test_owner_scope_hides_foreign_and_missing_records(self):
        async with self.sessions() as session:
            repository = AdaptationRepository(session)
            adaptation = await repository.add(
                AdaptationCreateSchema(resume_id=self.resume_id, vacancy_id=self.vacancy_ids[0]), self.user_id,
            )
        async with self.sessions() as session:
            repository = AdaptationRepository(session)
            self.assertIsNone(await repository.get_by_id(adaptation.id, uuid.uuid4()))
            self.assertIsNone(await repository.get_by_id(uuid.uuid4(), self.user_id))

    async def test_repeated_pair_creates_independent_records_and_preserves_error(self):
        data = AdaptationCreateSchema(resume_id=self.resume_id, vacancy_id=self.vacancy_ids[0])
        async with self.sessions() as session:
            repository = AdaptationRepository(session)
            first = await repository.add(data, self.user_id)
            second = await repository.add(data, self.user_id)
            self.assertNotEqual(first.id, second.id)
            stored = await session.get(Adaptation, first.id)
            stored.status = "failed"
            stored.error = "LLM unavailable"
            await session.commit()
        async with self.sessions() as session:
            repository = AdaptationRepository(session)
            failed = await repository.get_by_id(first.id, self.user_id)
            self.assertEqual(failed.status, "failed")
            self.assertEqual(failed.error, "LLM unavailable")
            self.assertIsNone(failed.result)
            self.assertEqual((await repository.get_by_id(second.id, self.user_id)).status, "pending")

    async def test_adaptation_outbox_retries_and_publishes_worker_wire_format(self):
        async with self.sessions() as session:
            adaptation = await AdaptationRepository(session).add(
                AdaptationCreateSchema(resume_id=self.resume_id, vacancy_id=self.vacancy_ids[0]), self.user_id,
            )
        redis = AsyncMock()
        redis.rpush.side_effect = ConnectionError("Redis unavailable")
        dispatcher = OutboxDispatcher(self.sessions, RedisPublisher(redis, "embedding_tasks"))
        with self.assertRaises(ConnectionError):
            await dispatcher.dispatch_one()
        async with self.sessions() as session:
            events = (await session.scalars(select(OutboxEvent))).all()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].payload, {
                "event_type": "adaptation.requested", "adaptation_id": str(adaptation.id), "user_id": str(self.user_id),
            })
            self.assertIsNotNone(await session.get(Adaptation, adaptation.id))
        redis.rpush.side_effect = None
        self.assertTrue(await dispatcher.dispatch_one())
        queue, payload = redis.rpush.call_args.args
        self.assertEqual(queue, "embedding_tasks")
        self.assertEqual(json.loads(payload), {
            "event_type": "adaptation.requested",
            "data": {"adaptation_id": str(adaptation.id), "user_id": str(self.user_id)},
        })
        self.assertFalse(await dispatcher.dispatch_one())

    async def test_failed_transaction_rolls_back_adaptation_and_outbox(self):
        async with self.sessions() as session:
            with patch.object(session, "commit", side_effect=RuntimeError("Commit failed")):
                with self.assertRaises(RuntimeError):
                    await AdaptationRepository(session).add(
                        AdaptationCreateSchema(resume_id=self.resume_id, vacancy_id=self.vacancy_ids[0]), self.user_id,
                    )
            await session.rollback()
        async with self.sessions() as session:
            self.assertEqual((await session.scalars(select(Adaptation))).all(), [])
            self.assertEqual((await session.scalars(select(OutboxEvent))).all(), [])

    async def test_concurrent_claim_has_one_winner_and_terminal_result_is_immutable(self):
        async with self.sessions() as session:
            adaptation = await AdaptationRepository(session).add(
                AdaptationCreateSchema(resume_id=self.resume_id, vacancy_id=self.vacancy_ids[0]), self.user_id,
            )

        async def claim():
            async with self.sessions() as session:
                return await AdaptationRepository(session).claim(adaptation.id, self.user_id)

        results = await asyncio.gather(claim(), claim())
        self.assertEqual(sum(result is not None for result in results), 1)
        done = AdaptationFinishSchema(status="done", result={
            "resume_text": "Python", "review": {"passed": False, "issues": ["Unconfirmed fact"]},
        })
        async with self.sessions() as session:
            repository = AdaptationRepository(session)
            self.assertIsNone(await repository.finish(adaptation.id, uuid.uuid4(), done))
            result = await repository.finish(adaptation.id, self.user_id, done)
            self.assertEqual(result.status, "done")
            self.assertFalse(result.result.review.passed)
            self.assertIsNone(await repository.claim(adaptation.id, self.user_id))
            self.assertIsNone(await repository.finish(
                adaptation.id, self.user_id, AdaptationFinishSchema(status="failed", error="late error"),
            ))
            self.assertEqual((await repository.get_by_id(adaptation.id, self.user_id)).result.resume_text, "Python")

    async def test_failed_status_is_saved_only_after_claim_by_owner(self):
        async with self.sessions() as session:
            repository = AdaptationRepository(session)
            adaptation = await repository.add(
                AdaptationCreateSchema(resume_id=self.resume_id, vacancy_id=self.vacancy_ids[0]), self.user_id,
            )
            failed = AdaptationFinishSchema(status="failed", error="LLM unavailable")
            self.assertIsNone(await repository.claim(adaptation.id, uuid.uuid4()))
            self.assertIsNone(await repository.finish(adaptation.id, self.user_id, failed))
            await repository.claim(adaptation.id, self.user_id)
            result = await repository.finish(adaptation.id, self.user_id, failed)
            self.assertEqual(result.error, "LLM unavailable")
            self.assertEqual(result.status, "failed")
            self.assertIsNone(result.result)
