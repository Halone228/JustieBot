from aioredis import Redis
from os import getenv


class RedisDB:
    def __init__(self):
        self.client: Redis = Redis(
            host=getenv('REDIS_HOST'),
            port=int(getenv('REDIS_PORT')),
            username=getenv("REDIS_USERNAME"),
            password=getenv("REDIS_PASSWORD")
        )

redis_db = RedisDB()