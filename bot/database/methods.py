import asyncio
from aiogram import types
from .core import AsyncSession, asession_maker
from .models import User, UserInfo, Users
from sqlalchemy import select, update, bindparam
from datetime import datetime, timedelta
from bot.events import expire_event, notify_event
from bot.config import config
from functools import wraps


async def get_or_create(message: types.Message, session: AsyncSession) -> User:
    stmt = select(Users).where(Users.id == message.from_user.id)
    result = await session.execute(stmt)
    result = result.scalar()
    if not result:
        await add_user(
            session,
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        await session.commit()
    return result


def session_dec(func):
    # @wraps(func)
    async def wrapper(*args, **kwargs):
        async with asession_maker() as session:
            print(1)
            return await func(session=session, *args, **kwargs)
    return wrapper


def user_dec(func):
    @session_dec
    async def wrapper(message: types.Message, session: AsyncSession,  *args, **kwargs):
        return await func(
            message=message,
            session=session,
            user=await get_or_create(message.from_user.id, session),
            *args,
            **kwargs
        )
    return wrapper


async def check_expires(session: AsyncSession):
    stmt_notify = select(User).where(
        (User.expire_date > (datetime.now() - datetime.fromtimestamp(config['data']['notify_delay'])))
        and not User.notified and User.in_group
    )
    stmt_expire = select(User).where(
        (User.expire_date > datetime.now()) and User.in_group
    )
    result_expire = (await session.execute(stmt_expire)).scalars()
    result_notify = (await session.execute(stmt_notify)).scalars()
    expired_set = set()
    for i in result_expire:
        await asyncio.sleep(0)
        expired_set.add(i.user_id)
        await expire_event.send_async(i.user_id)

    for i in result_notify:
        await asyncio.sleep(0)
        if i.user_id in expired_set:
            continue
        await notify_event.send_async(i.user_id)


async def set_notified(session: AsyncSession, user_id: int):
    stmt = update(User).where(User.user_id == user_id).values(notified=True)
    await session.execute(stmt)
    await session.commit()


async def set_expired(session: AsyncSession, user_id: int):
    stmt = update(User).where(User.user_id == user_id).values(
        in_group=False,
        notified=True
    )
    await session.execute(stmt)
    await session.commit()


async def set_added(session: AsyncSession, user_id: int, delta_time: float):
    stmt = update(User).where(User.user_id == user_id).values(
        in_group=True,
        notified=False,
        expire_date=datetime.now() + timedelta(seconds=delta_time)
    )
    await session.execute(stmt)
    await session.commit()


async def increment_count(session: AsyncSession, cache_data: dict[int, float]):
    for k, v in cache_data.items():
        stmt = update(User).where(User.user_id == k).values(
            points=User.points + v
        )
        await session.execute(stmt)
    await session.commit()


async def get_points(session: AsyncSession, user_id: int):
    stmt = select(User).where(User.user_id == user_id)
    result = (await session.execute(stmt)).scalar()
    return result.points if result else 0.


async def add_user(
        session: AsyncSession,
        user_id: int,
        first_name: str,
        last_name: str,
        username: str
):
    session.add(Users(id=user_id))
    try:
        await session.commit()
    except:
        pass
    session.add(UserInfo(user_id=user_id, first_name=first_name, last_name=last_name, username=username))
    try:
        await session.commit()
    except:
        pass
