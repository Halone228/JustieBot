import asyncio

from bot.core import dp, main
import bot.core
import bot.routes
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
asyncio.run(main())
