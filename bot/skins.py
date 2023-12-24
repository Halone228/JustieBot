import asyncio
import random
from typing import Tuple, Any

from aiohttp import ClientSession
from async_lru import alru_cache
from bs4 import BeautifulSoup
from dataclasses import dataclass


@dataclass
class Skin:
    id: int
    url: str
    image_src: str
    item_name: str
    price: int


class SkinsStorage:
    counter = 0
    url_to_id = dict()
    id_to_url = dict()
    url_to_price = dict()

    @classmethod
    def fill_urls(cls, data: list[dict[str, int]]) -> None:
        for i in data:
            key, value = list(i.keys())[0], list(i.values())[0]
            cls.url_to_price[key] = value

    @classmethod
    def get_price_by_url(cls, url) -> int:
        return cls.id_to_url[url]

    @classmethod
    def get_id_by_url(cls, url: str):
        if url not in cls.url_to_id:
            cls.counter += 1
            cls.url_to_id[url] = cls.counter
            cls.id_to_url[cls.counter] = url
        return cls.url_to_id[url]

    @classmethod
    def get_url_by_id(cls, id: int):
        return cls.id_to_url[id]

    @classmethod
    @alru_cache()
    async def get_skin(cls, url: str, try_=0) -> Skin:
        async with ClientSession() as session:
            try:
                async with session.get(url, params={
                    'l': 'russian'
                }) as response:
                    soup = BeautifulSoup(await response.text())
                    await asyncio.sleep(0)
                    image_src = soup.select_one('.market_listing_largeimage>img').get('src')
                    await asyncio.sleep(0)
                    item_name = soup.select('.market_listing_item_name')[-1].text.strip()
                    item_id = cls.get_id_by_url(url)
                    return Skin(
                        item_id, url, image_src, item_name, cls.get_price_by_url(url)
                    )
            except AttributeError as e:
                if try_>5:
                    return Skin(0,'','','')
                await asyncio.sleep(random.randint(0, 3)+random.random())
                return await cls.get_skin(url, try_+1)

    @classmethod
    async def get_bulk_skins(cls, urls_list: list) -> tuple[Any] | tuple[Skin]:
        return await asyncio.gather(
            *[cls.get_skin(i) for i in urls_list]
        )
