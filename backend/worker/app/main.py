import asyncio
import logging
from app.schemas.event import AdaptationRequestedEvent
from app.use_cases.adaptation_task import get_adaptation_task_service
from app.use_cases.event_consumer import get_event_consumer
from app.use_cases.pipeline import get_pipeline_service


logger = logging.getLogger(__name__)


async def main() -> None:
    async with get_event_consumer() as consumer, get_pipeline_service() as pipeline:
        while True:
            try:
                message = await consumer.consume()
                if message is None:
                    continue
                event, payload = message
                if isinstance(event, AdaptationRequestedEvent):
                    async with get_adaptation_task_service() as adaptation:
                        await adaptation.process(event)
                    await consumer.ack(payload)
                    continue
                document = await pipeline.process(event)
                await consumer.ack(payload)
                if document is None:
                    continue
                logger.info(
                    "Saved embedding for %s %s: model=%s, dimensions=%s",
                    document.document_type,
                    document.document_id,
                    document.embedding_model,
                    len(document.embedding),
                )
            except Exception:
                logger.exception("Failed to process task")
                await asyncio.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
