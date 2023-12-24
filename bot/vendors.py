import asyncio
import datetime
from typing import Any, Callable, Type, Callable
from aiofiles import open
from abc import ABC, abstractmethod
from aiogram import types
from uuid import uuid4
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from os import getenv
from .database.methods import session_dec, User
from .events import add_event
from .config import config
from .skins import SkinsStorage, Skin

ADMIN_CHAT = int()


class BaseVendor(ABC):

    def __init__(self, user: types.User, action: str, data: Any):
        self.user = user
        self.action = action
        self.data = data

    @abstractmethod
    async def check_action(self, session: AsyncSession) -> bool:
        ...

    @abstractmethod
    async def create_transaction(self, session: AsyncSession = None, callback_success: Callable = None):
        ...

    @abstractmethod
    async def get_message(self, session: AsyncSession = None) -> str | tuple[str, bool]:
        ...


class TextVendor(BaseVendor):
    def __init__(self, user: types.User, action: str, data: Any):
        super().__init__(
            user=user,
            action=action,
            data=data
        )
        self.expires = datetime.datetime.now() + datetime.timedelta(days=1)

    async def check_action(self, session: AsyncSession) -> bool:
        if self.action == "date":
            return True
        return False

    async def create_transaction(self, session: AsyncSession = None, callback_success: Callable = None):
        while datetime.datetime.now() < self.expires:
            await asyncio.sleep(10)
            async with open('text.p', 'r', encoding='utf-8') as f:
                if 'fuck' in await f.readline():
                    await callback_success()
                    return

    async def get_message(self) -> str:
        return f"Спасибо {self.user.first_name}, счёт {uuid4().hex} открыт."


class SemiPointsVendor(BaseVendor):
    def __init__(self, user: types.User, action: str, data: Any):
        points, data = data.split('-')
        self.points = int(points)
        super().__init__(
            user,
            action,
            data
        )

    async def check_action(self, session: AsyncSession) -> bool:
        stmt = select(User).where(User.user_id == self.user.id)
        result = (await session.execute(stmt)).scalar()
        print(result.points)
        print(self.points)
        if result.points < self.points:
            return False
        return True

    async def get_message(self, session: AsyncSession = None) -> str | tuple[str, bool]:
        can = await self.check_action(session)
        if can:
            return config['texts']['success'], True
        else:
            return config['texts']['unsuccess'], False

    async def create_transaction(self, session: AsyncSession = None, callback_success: Callable = None):
        stmt = update(User).where(User.user_id == self.user.id).values(
            points=User.points-self.points
        )
        await session.execute(stmt)
        await session.commit()
        await self.user.bot.send_message(
            ADMIN_CHAT,
            f"Скидка пользователю @{self.user.username} ({self.user.full_name}) {self.data}"
        )


class PointsVendor(SemiPointsVendor):
    async def create_transaction(self, session: AsyncSession = None, callback_success: Callable = None):
        stmt = update(User).where(User.user_id == self.user.id).values(
            points=User.points-self.points
        )
        item = await SkinsStorage.get_skin(SkinsStorage.get_url_by_id(int(self.data)))
        await session.execute(stmt)
        await session.commit()
        await self.user.bot.send_message(
            ADMIN_CHAT,
            f"Покупка скина пользователем @{self.user.username} ({self.user.full_name}\n"
            f"Скин {item['name']}, <a href='{item['tp_url']}'>ТП</a>"
        )


class VendorFactory:
    vendor_dict = {
        'text': TextVendor,
        'semipoints': SemiPointsVendor,
        'points': PointsVendor
    }

    @classmethod
    def get_vendor(cls, vendor_name: str) -> Type[BaseVendor]:
        return cls.vendor_dict[vendor_name]