import httpx
from typing import Optional

class QbClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.cookies = None

    async def login(self):
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as c:
            r = await c.post(f"{self.base_url}/api/v2/auth/login", data={
                "username": self.username,
                "password": self.password,
            })
            r.raise_for_status()
            self.cookies = r.cookies
            return True

    async def _client(self) -> httpx.AsyncClient:
        if self.cookies is None:
            await self.login()
        return httpx.AsyncClient(cookies=self.cookies, timeout=20)

    async def add_magnet(self, magnet: str, save_path: Optional[str] = None) -> str:
        async with await self._client() as c:
            data = {"urls": magnet}
            if save_path:
                data["savepath"] = save_path
            r = await c.post(f"{self.base_url}/api/v2/torrents/add", data=data)
            r.raise_for_status()
            return ""

    async def list_torrents(self):
        async with await self._client() as c:
            r = await c.get(f"{self.base_url}/api/v2/torrents/info")
            r.raise_for_status()
            return r.json()

    async def info_by_hash(self, torrent_hash: str):
        async with await self._client() as c:
            r = await c.get(f"{self.base_url}/api/v2/torrents/info", params={"hashes": torrent_hash})
            r.raise_for_status()
            data = r.json()
            return data[0] if data else None

    async def pause(self, torrent_hash: str):
        async with await self._client() as c:
            r = await c.post(f"{self.base_url}/api/v2/torrents/pause", data={"hashes": torrent_hash})
            r.raise_for_status()

    async def resume(self, torrent_hash: str):
        async with await self._client() as c:
            r = await c.post(f"{self.base_url}/api/v2/torrents/resume", data={"hashes": torrent_hash})
            r.raise_for_status()

    async def delete(self, torrent_hash: str, delete_files: bool = False):
        async with await self._client() as c:
            r = await c.post(f"{self.base_url}/api/v2/torrents/delete", data={
                "hashes": torrent_hash,
                "deleteFiles": "true" if delete_files else "false",
            })
            r.raise_for_status()
