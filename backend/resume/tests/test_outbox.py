import asyncio
import json
import os
import uuid
from unittest.mock import AsyncMock

import pytest
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


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is required")
class TestOutbox:
    @pytest.fixture(autouse=True)
    async def setup(self, cleanup):
        self.cleanup = cleanup
        self.schema = f"outbox_test_{uuid.uuid4().hex}"
        self.engine = create_async_engine(
            os.environ["TEST_DATABASE_URL"],
            connect_args={"server_settings": {"search_path": self.schema}},
        )
        self.cleanup.push_async_callback(self.engine.dispose)
        async with self.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.cleanup.push_async_callback(self.drop_schema)
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
        with pytest.raises(asyncio.CancelledError):
            await task

    async def test_publish_failure_preserves_each_entity_and_retries_same_event(self, subtests):
        for kind, model in (("resume", Resume), ("vacancy", Vacancy)):
            with subtests.test(kind=kind):
                entity = await self.create_entity(kind)
                before = (await self.pending())[0]
                assert before.payload[f"{kind}_id"] == str(entity.id)
                assert before.payload["user_id"] == str(entity.user_id)
                self.publisher.publish.side_effect = RedisConnectionError("unavailable")
                with pytest.raises(RedisConnectionError):
                    await self.dispatcher.dispatch_one()
                after = (await self.pending())[0]
                assert (after.id, after.payload) == (before.id, before.payload)
                async with self.sessions() as session:
                    assert await session.get(model, entity.id) is not None
                self.publisher.publish.side_effect = None
                assert await self.dispatcher.dispatch_one()
                event = self.publisher.publish.call_args.args[0]
                assert event.model_dump(mode="json") == before.payload
                assert await self.pending() == []
                assert not await self.dispatcher.dispatch_one()

    async def test_existing_redis_wire_format_for_both_entity_types(self, subtests):
        redis = AsyncMock()
        dispatcher = OutboxDispatcher(
            self.sessions, RedisPublisher(redis, "embedding_tasks"),
        )
        for kind in ("resume", "vacancy"):
            with subtests.test(kind=kind):
                entity = await self.create_entity(kind)
                assert await dispatcher.dispatch_one()
                queue, payload = redis.rpush.call_args.args
                assert queue == "embedding_tasks"
                assert json.loads(payload) == {
                    "event_type": f"{kind}.uploaded",
                    "data": {f"{kind}_id": str(entity.id), "user_id": str(entity.user_id)},
                }
                assert await self.pending() == []

    async def test_outbox_insert_failure_rolls_back_entity(self, subtests):
        async with self.engine.begin() as connection:
            await connection.execute(text(
                "ALTER TABLE outbox_events ADD CONSTRAINT reject_events CHECK (false)"
            ))
        for kind in ("resume", "vacancy"):
            with subtests.test(kind=kind):
                with pytest.raises(IntegrityError):
                    await self.create_entity(kind)
                async with self.sessions() as session:
                    for model in (Resume, Vacancy, OutboxEvent):
                        count = await session.scalar(select(func.count()).select_from(model))
                        assert count == 0

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
            assert await asyncio.wait_for(other.dispatch_one(), timeout=2)
            event = other_publisher.publish.call_args.args[0]
            assert event.vacancy_id == vacancy.id
            assert (await self.pending())[0].payload["resume_id"] == str(resume.id)
            assert not await other.dispatch_one()
        finally:
            release.set()
            await asyncio.wait_for(first, timeout=2)
        assert await self.pending() == []

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
        assert len(await self.pending()) == 1
        self.publisher.publish.side_effect = None
        assert await self.dispatcher.dispatch_one()
        assert await self.pending() == []

    async def test_publish_timeout_retains_event(self):
        await self.create_entity("vacancy")

        async def publish(event):
            await asyncio.Event().wait()

        self.publisher.publish.side_effect = publish
        dispatcher = OutboxDispatcher(self.sessions, self.publisher, publish_timeout=0.02)
        with pytest.raises(TimeoutError):
            await dispatcher.dispatch_one()
        assert len(await self.pending()) == 1
        self.publisher.publish.side_effect = None
        assert await dispatcher.dispatch_one()

    async def test_run_recovers_after_publish_failure(self, caplog):
        await self.create_entity("resume")
        self.publisher.publish.side_effect = [RedisConnectionError("unavailable"), None]
        dispatcher = OutboxDispatcher(
            self.sessions, self.publisher, poll_interval=0.01, retry_interval=0.01,
        )

        async def wait_until_delivered():
            while await self.pending():
                await asyncio.sleep(0.01)

        with caplog.at_level("ERROR", logger="app.messaging.outbox_dispatcher"):
            task = asyncio.create_task(dispatcher.run())
            try:
                await asyncio.wait_for(wait_until_delivered(), timeout=2)
            finally:
                await self.stop_task(task)
        assert self.publisher.publish.await_count == 2
        assert await self.pending() == []
        assert any(record.name == "app.messaging.outbox_dispatcher" and record.levelname == "ERROR" for record in caplog.records)
