import asyncio
import json
import os
import unittest
import uuid
from unittest.mock import AsyncMock

from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.messaging.outbox_dispatcher import OutboxDispatcher
from app.messaging.redis_publisher import RedisPublisher
from app.models.outbox import OutboxEvent
from app.models.resume import Resume
from app.models.vacancy import Vacancy
from app.repositories.resume import ResumeRepository
from app.repositories.vacancy import VacancyRepository
from app.schemas.resume import ResumeCreateSchema
from app.schemas.vacancy import VacancyCreateSchema


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "TEST_DATABASE_URL is required")
class OutboxTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = f"outbox_test_{uuid.uuid4().hex}"
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
        self.publisher = AsyncMock()
        self.dispatcher = OutboxDispatcher(self.sessions, self.publisher)

    async def drop_schema(self):
        async with self.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))

    async def create_entity(self, kind):
        async with self.sessions() as session:
            if kind == "resume":
                return await ResumeRepository(session).add(
                    ResumeCreateSchema(file_url="http://minio/resumes/resume.pdf"),
                    uuid.uuid4(),
                )
            return await VacancyRepository(session).add(
                VacancyCreateSchema(text="Python developer"), uuid.uuid4(),
            )

    async def pending(self):
        async with self.sessions() as session:
            return list((await session.scalars(select(OutboxEvent))).all())

    async def stop_task(self, task):
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_publish_failure_preserves_each_entity_and_retries_same_event(self):
        for kind, model in (("resume", Resume), ("vacancy", Vacancy)):
            with self.subTest(kind=kind):
                entity = await self.create_entity(kind)
                before = (await self.pending())[0]
                self.assertEqual(before.payload[f"{kind}_id"], str(entity.id))
                self.assertEqual(before.payload["user_id"], str(entity.user_id))
                self.publisher.publish.side_effect = RedisConnectionError("unavailable")
                with self.assertRaises(RedisConnectionError):
                    await self.dispatcher.dispatch_one()
                after = (await self.pending())[0]
                self.assertEqual((after.id, after.payload), (before.id, before.payload))
                async with self.sessions() as session:
                    self.assertIsNotNone(await session.get(model, entity.id))
                self.publisher.publish.side_effect = None
                self.assertTrue(await self.dispatcher.dispatch_one())
                event = self.publisher.publish.call_args.args[0]
                self.assertEqual(event.model_dump(mode="json"), before.payload)
                self.assertEqual(await self.pending(), [])
                self.assertFalse(await self.dispatcher.dispatch_one())

    async def test_existing_redis_wire_format_for_both_entity_types(self):
        redis = AsyncMock()
        dispatcher = OutboxDispatcher(
            self.sessions, RedisPublisher(redis, "embedding_tasks"),
        )
        for kind in ("resume", "vacancy"):
            with self.subTest(kind=kind):
                entity = await self.create_entity(kind)
                self.assertTrue(await dispatcher.dispatch_one())
                queue, payload = redis.rpush.call_args.args
                self.assertEqual(queue, "embedding_tasks")
                self.assertEqual(json.loads(payload), {
                    "event_type": f"{kind}.uploaded",
                    "data": {f"{kind}_id": str(entity.id), "user_id": str(entity.user_id)},
                })
                self.assertEqual(await self.pending(), [])

    async def test_outbox_insert_failure_rolls_back_entity(self):
        async with self.engine.begin() as connection:
            await connection.execute(text(
                "ALTER TABLE outbox_events ADD CONSTRAINT reject_events CHECK (false)"
            ))
        for kind in ("resume", "vacancy"):
            with self.subTest(kind=kind):
                with self.assertRaises(IntegrityError):
                    await self.create_entity(kind)
                async with self.sessions() as session:
                    for model in (Resume, Vacancy, OutboxEvent):
                        count = await session.scalar(select(func.count()).select_from(model))
                        self.assertEqual(count, 0)

    async def test_concurrent_dispatcher_skips_locked_event(self):
        resume = await self.create_entity("resume")
        vacancy = await self.create_entity("vacancy")
        started = asyncio.Event()
        release = asyncio.Event()

        async def publish(event):
            started.set()
            await release.wait()

        self.publisher.publish.side_effect = publish
        first = asyncio.create_task(self.dispatcher.dispatch_one())
        try:
            await asyncio.wait_for(started.wait(), timeout=2)
            other_publisher = AsyncMock()
            other = OutboxDispatcher(self.sessions, other_publisher)
            self.assertTrue(await asyncio.wait_for(other.dispatch_one(), timeout=2))
            event = other_publisher.publish.call_args.args[0]
            self.assertEqual(event.vacancy_id, vacancy.id)
            self.assertEqual((await self.pending())[0].payload["resume_id"], str(resume.id))
            self.assertFalse(await other.dispatch_one())
        finally:
            release.set()
            await asyncio.wait_for(first, timeout=2)
        self.assertEqual(await self.pending(), [])

    async def test_cancellation_retains_event_and_releases_lock(self):
        await self.create_entity("resume")
        started = asyncio.Event()

        async def publish(event):
            started.set()
            await asyncio.Event().wait()

        self.publisher.publish.side_effect = publish
        task = asyncio.create_task(self.dispatcher.dispatch_one())
        try:
            await asyncio.wait_for(started.wait(), timeout=2)
        finally:
            await self.stop_task(task)
        self.assertEqual(len(await self.pending()), 1)
        self.publisher.publish.side_effect = None
        self.assertTrue(await self.dispatcher.dispatch_one())
        self.assertEqual(await self.pending(), [])

    async def test_publish_timeout_retains_event(self):
        await self.create_entity("vacancy")

        async def publish(event):
            await asyncio.Event().wait()

        self.publisher.publish.side_effect = publish
        dispatcher = OutboxDispatcher(self.sessions, self.publisher, publish_timeout=0.02)
        with self.assertRaises(TimeoutError):
            await dispatcher.dispatch_one()
        self.assertEqual(len(await self.pending()), 1)
        self.publisher.publish.side_effect = None
        self.assertTrue(await dispatcher.dispatch_one())

    async def test_run_recovers_after_publish_failure(self):
        await self.create_entity("resume")
        self.publisher.publish.side_effect = [RedisConnectionError("unavailable"), None]
        dispatcher = OutboxDispatcher(
            self.sessions, self.publisher, poll_interval=0.01, retry_interval=0.01,
        )

        async def wait_until_delivered():
            while await self.pending():
                await asyncio.sleep(0.01)

        with self.assertLogs("app.messaging.outbox_dispatcher", level="ERROR"):
            task = asyncio.create_task(dispatcher.run())
            try:
                await asyncio.wait_for(wait_until_delivered(), timeout=2)
            finally:
                await self.stop_task(task)
        self.assertEqual(self.publisher.publish.await_count, 2)
        self.assertEqual(await self.pending(), [])


if __name__ == "__main__":
    unittest.main()
