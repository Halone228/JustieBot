import asyncio
import datetime
from sqlalchemy import update
import loguru
from dotenv import load_dotenv
load_dotenv('.env')
from pyrogram import Client, types
from jastie_database.sql import UserPoints, asession_maker
from tqdm import tqdm

api_id = 7816785
api_hash = "a31486c26edf6c02ed37333696a2a49e"


async def main():
    client = Client(
        'recover_bot',
        api_id=api_id,
        api_hash=api_hash,
        phone_number='+375298936228'
    )
    data = {}
    users = {932205679}
    async with client as app:
        app: Client
        progress = tqdm()
        async for message in app.get_chat_history(-1001743519955):
            progress.update(1)
            if message.date > (datetime.datetime.now() - datetime.timedelta(days=2)):
                try:
                    if users and message.from_user and int(message.from_user.id) in users:
                        data[message.from_user.id] = data.get(message.from_user.id, 0) + len(message.text or message.caption or '0')/100
                except Exception as e:
                    loguru.logger.exception(e)
            else:
                break
    async with asession_maker() as session:
        for k, v in data.items():
            stmt = update(UserPoints).where(UserPoints.user_id == k).values(
                points=v
            )
            await session.execute(stmt)
        await session.commit()

asyncio.run(main())