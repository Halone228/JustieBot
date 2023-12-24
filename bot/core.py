import asyncio
from typing import TypedDict
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession
from .database.methods import check_expires, set_expired, set_notified, session_dec, set_added
from .config import config
from .database.core import asession_maker, init
from .events import expire_event, notify_event, add_event
from os import getenv


class AddEventData(TypedDict):
    user_id: int
    sec_add: float


bot: Bot = None


async def main():
    global bot
    bot = Bot(getenv('TOKEN'), parse_mode=ParseMode.HTML)
    await init()
    # asyncio.create_task(polling_events())
    print('start_bot')
    await dp.start_polling(bot)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
main_router = Router(name="main_router")
admin_router = Router(name="admin_router")
dp.include_routers(main_router, admin_router)


async def polling_events():
    async with asession_maker() as session:
        while True:
            await check_expires(session)
            await asyncio.sleep(30)


@expire_event.connect
@session_dec
async def expire(user_id: int, session: AsyncSession):
    await set_expired(session, user_id)
    await bot.ban_chat_member(
        config['bot']['chat_id'],
        user_id
    )
    await bot.send_message(
        chat_id=user_id,
        text=config['texts']['kick_now']
    )


@notify_event.connect
@session_dec
async def notify(user_id: int, session: AsyncSession):
    await set_notified(session, user_id)
    await bot.send_message(
        chat_id=user_id,
        text=config['texts']['notify_now']
    )


@add_event.connect
@session_dec
async def add(data: AddEventData, session: AsyncSession):
    user_id = data['user_id']
    sec_add = data['sec_add']
    await set_added(session, user_id, sec_add)
    try:
        await bot.unban_chat_member(
            config['bot']['chat_id'],
            user_id
        )
    except:
        pass
    link = await bot.create_chat_invite_link(chat_id=config['bot']['chat_id'], member_limit=1)
    data = {'link': link.invite_link}
    message: str = config['texts']['invite_link']
    message = message.format_map(data)
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text="Перейти", url=link.invite_link)
        ]]
    )
    await bot.send_message(user_id, text=message, reply_markup=keyboard)