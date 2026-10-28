import asyncio
import logging
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
                document = await pipeline.process(event)
                await consumer.ack(payload)
                logger.info(
                    "Saved embedding for %s %s: model=%s, dimensions=%s",
                    document.document_type,
                    document.document_id,
                    document.embedding_model,
                    len(document.embedding),
                )
            except Exception:
                logger.exception("Failed to process embedding task")
                await asyncio.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
