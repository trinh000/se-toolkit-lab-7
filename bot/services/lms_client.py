import httpx


class LMSClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def _get(self, path: str, params: dict | None = None) -> list | dict:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self._base_url}{path}", headers=self._headers, params=params or {}
            )
            resp.raise_for_status()
            return resp.json()

    async def get_items(self) -> list[dict]:
        return await self._get("/items/")  # type: ignore[return-value]

    async def get_learners(self) -> list[dict]:
        return await self._get("/learners/")  # type: ignore[return-value]

    async def get_scores(self, lab: str) -> list[dict]:
        return await self._get("/analytics/scores", {"lab": lab})  # type: ignore[return-value]

    async def get_pass_rates(self, lab: str) -> list[dict]:
        return await self._get("/analytics/pass-rates", {"lab": lab})  # type: ignore[return-value]

    async def get_timeline(self, lab: str) -> list[dict]:
        return await self._get("/analytics/timeline", {"lab": lab})  # type: ignore[return-value]

    async def get_groups(self, lab: str) -> list[dict]:
        return await self._get("/analytics/groups", {"lab": lab})  # type: ignore[return-value]

    async def get_top_learners(self, lab: str, limit: int = 5) -> list[dict]:
        return await self._get("/analytics/top-learners", {"lab": lab, "limit": limit})  # type: ignore[return-value]

    async def get_completion_rate(self, lab: str) -> dict:
        return await self._get("/analytics/completion-rate", {"lab": lab})  # type: ignore[return-value]

    async def trigger_sync(self) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self._base_url}/pipeline/sync",
                headers=self._headers,
                json={},
            )
            resp.raise_for_status()
            return resp.json()
