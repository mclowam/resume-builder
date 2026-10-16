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
            text = await pipeline.process(event)
            logger.info("Prepared text for %s: %s characters", event.event_type, len(text))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
