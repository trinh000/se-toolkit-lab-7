import httpx


class LMSClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def get_items(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self._base_url}/items/", headers=self._headers)
            resp.raise_for_status()
            return resp.json()

    async def get_pass_rates(self, lab: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self._base_url}/analytics/pass-rates",
                headers=self._headers,
                params={"lab": lab},
            )
            resp.raise_for_status()
            return resp.json()
