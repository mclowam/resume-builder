import asyncio
import logging
from app.use_cases.event_consumer import get_event_consumer
from app.use_cases.pipeline import get_pipeline_service


logger = logging.getLogger(__name__)


async def main() -> None:
    async with get_event_consumer() as consumer, get_pipeline_service() as pipeline:
        while True:
            event = await consumer.consume()
            if event is None:
                continue
            document = await pipeline.process(event)
            logger.info(
                "Saved embedding for %s %s: model=%s, dimensions=%s",
                document.document_type,
                document.document_id,
                document.embedding_model,
                len(document.embedding),
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
