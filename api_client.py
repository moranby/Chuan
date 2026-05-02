import aiohttp
from typing import Dict, Any, List
from astrbot.api import logger

class MiniWorldApiClient:
    BASE_URL = "https://moran.sylu.net/api"

    def __init__(self):
        self.session = None

    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def get_user_profile(self, uin: str) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/mini_cha.php?uin={uin}"
        return await self._get(url)

    async def get_user_maps(self, user_id: str) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/map_api.php"
        return await self._post(url, {"user_id": user_id})

    async def _get(self, url: str) -> Dict:
        session = await self._get_session()
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as e:
            logger.error(f"[MiniWorld] GET 请求失败: {url} - {e}")
            raise

    async def _post(self, url: str, data: Dict) -> Dict:
        session = await self._get_session()
        try:
            async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as e:
            logger.error(f"[MiniWorld] POST 请求失败: {url} - {e}")
            raise

    async def close(self):
        if self.session:
            await self.session.close()