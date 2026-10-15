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
        self.redis.blpop = AsyncMock()
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
                    self.redis.blpop.return_value = ("embedding_tasks", wire_payload)

                    event = await self.consumer.consume()

                    self.assertIsInstance(event, model)
                    self.assertEqual(getattr(event.data, field), self.resource_id)
                    self.assertEqual(event.data.user_id, self.user_id)
                    self.redis.blpop.assert_awaited_with("embedding_tasks", timeout=5)

    async def test_returns_none_on_timeout(self):
        self.redis.blpop.return_value = None

        self.assertIsNone(await self.consumer.consume(timeout=1))
        self.redis.blpop.assert_awaited_once_with("embedding_tasks", timeout=1)

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
                self.redis.blpop.return_value = ("embedding_tasks", payload)

                with self.assertRaises(ValidationError):
                    await self.consumer.consume()

    async def test_propagates_redis_error(self):
        error = ConnectionError("Redis unavailable")
        self.redis.blpop.side_effect = error

        with self.assertRaises(ConnectionError) as raised:
            await self.consumer.consume()

        self.assertIs(raised.exception, error)


if __name__ == "__main__":
    unittest.main()
