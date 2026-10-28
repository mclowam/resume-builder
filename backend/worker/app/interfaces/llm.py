from typing import Protocol


class ILLMClient(Protocol):
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        pass
