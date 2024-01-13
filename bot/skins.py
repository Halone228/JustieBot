import asyncio
import random
from typing import Tuple, Any

from aiohttp import ClientSession
from async_lru import alru_cache
from bs4 import BeautifulSoup
from dataclasses import dataclass
from .redis import redis_db
from pickle import dumps, loads


@dataclass
class Skin:
    id: int
    url: str
    image_src: str
    item_name: str
    price: int

    def to_dict(self):
        return self.__dict__


class SkinsStorage:
    url_to_id = dict()
    id_to_url = dict()
    url_to_price = dict()

    @classmethod
    def fill_urls(cls, data: dict[str, float]) -> None:
        for key, value in data.items():
            cls.url_to_price[key] = value

    @classmethod
    def get_price_by_url(cls, url) -> int:
        return cls.url_to_price[url]

    @classmethod
    def get_id_by_url(cls, url: str):
        if url not in cls.url_to_id:
            if not redis_db.sync_client.get('skin_counter'):
                redis_db.sync_client.set('skin_counter', 1)
            redis_db.sync_client.incrby('skin_counter', 1)
            counter = int(redis_db.sync_client.get('skin_counter'))
            cls.url_to_id[url] = counter
            cls.id_to_url[counter] = url
        return cls.url_to_id[url]

    @classmethod
    def get_url_by_id(cls, id: int):
        return cls.id_to_url[id]

    @classmethod
    @alru_cache()
    async def get_skin(cls, url: str, try_=0) -> Skin:
        data: bytes | None = await redis_db.client.get(f'skin_data:{url}')
        if data is not None:
            data: Skin = loads(data)
            cls.url_to_price[url] = data.price
            cls.id_to_url[data.id] = data.price
            return data
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
                    new_skin = Skin(
                        item_id, url, image_src, item_name, cls.get_price_by_url(url)
                    )
                    await redis_db.client.set(f'skin_data:{url}', dumps(new_skin))
                    return new_skin
            except AttributeError as e:
                if try_ > 5:
                    return Skin(0,'','','')
                await asyncio.sleep(random.randint(0, 3)+random.random())
                return await cls.get_skin(url, try_+1)

    @classmethod
    async def get_bulk_skins(cls, urls_list: list) -> tuple[Any] | tuple[Skin]:
        return await asyncio.gather(
            *[cls.get_skin(i) for i in urls_list]
        )
