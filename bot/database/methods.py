import asyncio
from aiogram import types
from .core import AsyncSession, asession_maker
from .models import User
from sqlalchemy import select, update, bindparam
from datetime import datetime, timedelta
from bot.events import expire_event, notify_event
from bot.config import config
from functools import wraps


async def get_or_create(user_id: int, session: AsyncSession) -> User:
    stmt = select(User).where(User.user_id == user_id)
    result = await session.execute(stmt)
    result = result.scalar()
    if not result:
        result = User(user_id=user_id)
        session.add(result)
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
    stmt = update(User).values(
        points=User.points + bindparam("points")
    )
    await session.execute(stmt, [{'user_id': k, "points": v} for k,v in cache_data.items()])
    await session.commit()


async def get_points(session: AsyncSession, user_id: int):
    stmt = select(User).where(User.user_id == user_id)
    result = (await session.execute(stmt)).scalar()
    return result.points if result else 0.
