import asyncio
from bot.database.core import asession_maker
from bot.database.models import UserInfo, Users
from sqlalchemy import select, insert
from pyrogram import Client
from sqlalchemy.dialects.postgresql import insert


async def main():
    client = Client(
        name='get_name',
        api_id=7816785,
        api_hash='a31486c26edf6c02ed37333696a2a49e',
        phone_number='+375298936228'
    )
    async with client as app:
        app: Client
        info_list = []
        async for user in app.get_chat_members(-1001743519955):
            info_list.append(
                UserInfo(
                    user_id=user.user.id,
                    first_name=user.user.first_name,
                    last_name=user.user.last_name,
                    username=user.user.username
                )
            )

        async with asession_maker() as session:
            stmt = insert(Users).values(
                [(i.user_id, ) for i in info_list]
            ).on_conflict_do_nothing()
            await session.execute(stmt)
            await session.commit()
            session.add_all(info_list)
            await session.commit()


if __name__=='__main__':
    asyncio.run(main())