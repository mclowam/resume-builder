from contextlib import AsyncExitStack

import pytest_asyncio


@pytest_asyncio.fixture
async def cleanup():
    async with AsyncExitStack() as stack:
        yield stack
