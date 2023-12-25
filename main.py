import asyncio

from bot.core import dp, main as core_main
import bot.core
import bot.routes
import logging
import sys


async def main():
    await asyncio.gather(bot.routes.update_cache_points(), core_main())

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
asyncio.run(main())
