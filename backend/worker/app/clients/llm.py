import httpx

from app.core.core import settings


class LLMHttpClient:
    def __init__(self, base_url: str, api_key: str | None, model: str):
        if not api_key or not api_key.strip():
            raise ValueError("OPENAI_API_KEY must not be empty")
        self.model = model
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=settings.HTTP_TIME_OUT,
            headers={"Authorization": f"Bearer {api_key.strip()}"},
        )

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = await self._client.post(
            "chat/completions",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        choice = response.json()["choices"][0]
        message = choice["message"]
        if message.get("refusal") or choice["finish_reason"] != "stop" or not message.get("content"):
            raise ValueError("LLM did not return a complete result")
        return message["content"]

    async def close(self) -> None:
        await self._client.aclose()
