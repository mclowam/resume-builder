from typing import Protocol


class IEmbeddingClient(Protocol):
    @property
    def model(self) -> str:
        pass

    async def embed(self, text: str) -> list[float]:
        pass
