import json
import unittest
import uuid
from unittest.mock import AsyncMock

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import ConnectionError

from app.messaging.redis_consumer import RedisConsumer
from app.schemas.event import ResumeUploadedEvent, VacancyUploadedEvent


class RedisConsumerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.redis = AsyncMock(spec=Redis)
        self.redis.blmove = AsyncMock()
        self.redis.lrem = AsyncMock()
        self.consumer = RedisConsumer(self.redis, "embedding_tasks")
        self.resource_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

    async def test_accepts_publisher_payloads(self):
        for event_type, field, model in (
            ("resume.uploaded", "resume_id", ResumeUploadedEvent),
            ("vacancy.uploaded", "vacancy_id", VacancyUploadedEvent),
        ):
            payload = json.dumps({
                "event_type": event_type,
                "data": {field: str(self.resource_id), "user_id": str(self.user_id)},
            })
            for wire_payload in (payload, payload.encode()):
                with self.subTest(event_type=event_type, wire_type=type(wire_payload)):
                    self.redis.blmove.return_value = wire_payload

                    event, received_payload = await self.consumer.consume()

                    self.assertIsInstance(event, model)
                    self.assertEqual(received_payload, wire_payload)
                    self.assertEqual(getattr(event.data, field), self.resource_id)
                    self.assertEqual(event.data.user_id, self.user_id)
                    self.redis.blmove.assert_awaited_with(
                        "embedding_tasks", "embedding_tasks:processing", timeout=5,
                        src="LEFT", dest="RIGHT",
                    )
                    self.redis.lrem.assert_not_awaited()
                    await self.consumer.ack(received_payload)
                    self.redis.lrem.assert_awaited_once_with("embedding_tasks:processing", 1, wire_payload)
                    self.redis.lrem.reset_mock()

    async def test_returns_none_on_timeout(self):
        self.redis.blmove.return_value = None

        self.assertIsNone(await self.consumer.consume(timeout=1))
        self.redis.blmove.assert_awaited_once_with(
            "embedding_tasks", "embedding_tasks:processing", timeout=1,
            src="LEFT", dest="RIGHT",
        )

    async def test_reserves_message_without_removing_it(self):
        payload = json.dumps({
            "event_type": "resume.uploaded",
            "data": {"resume_id": str(self.resource_id), "user_id": str(self.user_id)},
        })
        self.redis.blpop = AsyncMock(return_value=("embedding_tasks", payload))
        self.redis.blmove.return_value = payload

        await self.consumer.consume()

        self.redis.blpop.assert_not_awaited()
        self.redis.blmove.assert_awaited_once_with(
            "embedding_tasks", "embedding_tasks:processing", timeout=5,
            src="LEFT", dest="RIGHT",
        )
        self.redis.lrem.assert_not_awaited()

    async def test_rejects_invalid_payloads(self):
        valid_data = {"resume_id": str(self.resource_id), "user_id": str(self.user_id)}
        payloads = (
            "not json",
            json.dumps({"event_type": "unknown", "data": valid_data}),
            json.dumps({"event_type": "resume.uploaded", "data": {**valid_data, "resume_id": "invalid"}}),
            json.dumps({"event_type": "resume.uploaded", "data": {**valid_data, "user_id": "invalid"}}),
            json.dumps({"event_type": "vacancy.uploaded", "data": valid_data}),
            json.dumps({"event_type": "resume.uploaded", "data": {"vacancy_id": str(self.resource_id), "user_id": str(self.user_id)}}),
            json.dumps({"event_type": "resume.uploaded", "data": {"resume_id": str(self.resource_id)}}),
            json.dumps({"event_type": "resume.uploaded"}),
            json.dumps({"data": valid_data}),
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                self.redis.blmove.return_value = payload

                with self.assertRaises(ValidationError):
                    await self.consumer.consume()

                self.redis.lrem.assert_not_awaited()

    async def test_acknowledges_each_received_payload(self):
        payloads = [json.dumps({
            "event_type": "resume.uploaded",
            "data": {"resume_id": str(resource_id), "user_id": str(self.user_id)},
        }).encode() for resource_id in (self.resource_id, uuid.uuid4())]
        self.redis.blmove.side_effect = payloads

        first_event, first_payload = await self.consumer.consume()
        second_event, second_payload = await self.consumer.consume()
        await self.consumer.ack(second_payload)
        self.redis.lrem.assert_awaited_with("embedding_tasks:processing", 1, payloads[1])
        await self.consumer.ack(first_payload)
        self.redis.lrem.assert_awaited_with("embedding_tasks:processing", 1, payloads[0])

        self.assertNotEqual(first_event.data.resume_id, second_event.data.resume_id)
        self.assertEqual(self.redis.lrem.await_count, 2)

    async def test_ack_failure_keeps_original_payload(self):
        payload = json.dumps({
            "event_type": "resume.uploaded",
            "data": {"resume_id": str(self.resource_id), "user_id": str(self.user_id)},
        }, indent=2).encode()
        self.redis.blmove.return_value = payload
        self.redis.lrem.side_effect = [ConnectionError("Redis unavailable"), 1]
        _, received_payload = await self.consumer.consume()

        with self.assertRaises(ConnectionError):
            await self.consumer.ack(received_payload)
        await self.consumer.ack(received_payload)

        self.assertEqual(self.redis.lrem.await_count, 2)
        self.redis.lrem.assert_awaited_with("embedding_tasks:processing", 1, payload)

    async def test_propagates_redis_error(self):
        error = ConnectionError("Redis unavailable")
        self.redis.blmove.side_effect = error

        with self.assertRaises(ConnectionError) as raised:
            await self.consumer.consume()

        self.assertIs(raised.exception, error)


if __name__ == "__main__":
    unittest.main()
