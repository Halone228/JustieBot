import asyncio
from aiogram import types
from .core import AsyncSession, asession_maker
from .models import User, UserInfo, Users, Referrers
from sqlalchemy import select, update, bindparam
from datetime import datetime, timedelta
from bot.events import expire_event, notify_event
from bot.config import config
from functools import wraps
from sqlalchemy.dialects.postgresql import insert
from bot.redis import redis_db


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


async def add_referrer(session: AsyncSession, user_id: int, referrer_id: int) -> 0 | -1 | 1:
    """
    -1 - not found referrer
    0 - has referrer
    1 - success
    :param session:
    :param user_id:
    :param referrer_id:
    :return:
    """
    stmt = select(UserInfo).where(
        UserInfo.user_id == user_id
    )
    stmt_referrer = select(Users).where(
        Users.id == referrer_id
    )
    _res = await session.execute(stmt)
    _res_ref = await session.execute(stmt_referrer)
    result = _res.scalar()
    res_ref = _res_ref.scalar()
    if res_ref is None:
        return -1
    if result.referrer is None:
        stmt1 = update(UserInfo).where(UserInfo.user_id == user_id).values(
            referrer=referrer_id
        )
        stmt2 = insert(Referrers).values(
            referrer_id=referrer_id,
            referral_id=user_id
        )
        await session.execute(stmt1)
        await session.execute(stmt2)
        await session.commit()
        return 1
    else:
        return 0


async def set_added(session: AsyncSession, user_id: int, delta_time: float):
    stmt = update(User).where(User.user_id == user_id).values(
        in_group=True,
        notified=False,
        expire_date=datetime.now() + timedelta(seconds=delta_time)
    )
    await session.execute(stmt)
    await session.commit()


async def increment_count(session: AsyncSession, cache_data: dict[int, float]):
    percent = float(await redis_db.client.get('referer_percent'))
    for k, v in cache_data.items():
        stmt = update(User).where(User.user_id == k).values(
            points=User.points + v
        )
        sstmt = select(UserInfo).where(UserInfo.user_id == k)
        res = (await session.execute(sstmt)).scalar()
        if res.referrer:
            stmt2 = update(User).where(
                User.user_id == res.referrer
            ).values(
                points=User.points + percent*v
            )
            await session.execute(stmt2)
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
    stmt1 = insert(Users).values(
        user_id=user_id
    ).on_conflict_do_nothing()
    stmt2 = insert(UserInfo).values(
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        username=username
    ).on_conflict_do_nothing()
    stmt3 = insert(User).values(
        user_id=user_id
    ).on_conflict_do_nothing()
    await session.execute(stmt1)
    await session.execute(stmt2)
    await session.execute(stmt3)
    await session.commit()
