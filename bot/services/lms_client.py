import httpx


class LMSClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._base_url}/health", headers=self._headers)
                return resp.status_code == 200
        except Exception:
            return False

    async def get_items(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self._base_url}/items/", headers=self._headers)
            resp.raise_for_status()
            return resp.json()

    async def get_task_pass_rate(self, lab: str | None = None) -> list[dict]:
        params = {}
        if lab:
            params["lab"] = lab
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self._base_url}/analytics/task-pass-rate",
                headers=self._headers,
                params=params,
            )
            resp.raise_for_status()
            return resp.json()
