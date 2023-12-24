import asyncio

from aiogram import types, F
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.enums import ChatType
from .core import main_router, config
from aiogram.filters import CommandStart, Command, and_f, Filter, or_f
from .skins import Skin, SkinsStorage
from .events import add_event
from .vendors import VendorFactory
from .database.methods import session_dec, increment_count, set_added, get_or_create, get_points
from typing import Iterable


class ChatTypeFilter(Filter):
    def __init__(self, chat_type: ChatType) -> None:
        self.chat_type = chat_type

    async def __call__(self, message, *args, **kwargs):
        print(message.chat.type, self.chat_type)
        return message.chat.type == self.chat_type


filter_group = or_f(ChatTypeFilter(ChatType.GROUP), ChatTypeFilter(ChatType.SUPERGROUP))


def command_dialog_filter(command: str):
    return and_f(Command(command), ChatTypeFilter(ChatType.PRIVATE))


### Система подсчета сообщений
@main_router.message(filter_group)
@session_dec
async def count_messages(message: types.Message, session: AsyncSession, *args, **kwargs):
    await increment_count(session, message)
###############################


@main_router.message(command_dialog_filter("buy_vip"))
async def buy_vip_menu(message: types.Message):
    builder = InlineKeyboardBuilder()
    data = {
        'bets': 'JastieBets',
        'sport': "JastieSport"
    }
    for k,v in data.items():
        builder.row(
            InlineKeyboardButton(
                text=f"Купон на покупку VIP-канал {v}",
                callback_data=f'pay-semipoints-vip-5000-{k}'
            )
        )
    await message.answer(
        text=config['texts']['buy_vip_menu'],
        reply_markup=builder.as_markup()
    )


@main_router.message(command_dialog_filter('start'))
@session_dec
async def start(message: types.Message, session: AsyncSession, *args, **kwargs):
    await get_or_create(message.from_user.id, session)
    if message.from_user.id != message.chat.id:
        return
    builder = InlineKeyboardBuilder()
    for k, v in config['data']['dates'].items():
        builder.row(InlineKeyboardButton(
            text=k, callback_data=f"pay-text-date-{v}" # pay-vendor-action-data
        ))
    await message.answer(
        text=config['texts']['start'],
        reply_markup=builder.as_markup()
    )


@main_router.message(command_dialog_filter('account'))
@session_dec
async def account_info(message: types.Message, session: AsyncSession, *args, **kwargs):
    print(0)
    points = await get_points(session, message.from_user.id)
    mes: str = config['texts']['account']
    data = {
        'points': points,
        'user_name': message.from_user.full_name
    }
    await message.answer(
        text=mes.format_map(
            data
        )
    )


@main_router.message(command_dialog_filter('skins'))
async def show_skins(message: types.Message):
    skins: list[dict[str, int]] = config['data']['skins']
    builder = InlineKeyboardBuilder()
    SkinsStorage.fill_urls(skins)
    for i in skins:
        i = list(i.keys())[0]
        i = await SkinsStorage.get_skin(i)
        builder.row(InlineKeyboardButton(
            text=i.item_name,
            callback_data=f'skin-{i.id}'
        ))
    await message.answer(
        text='Купить скины за баллы',
        reply_markup=builder.as_markup()
    )


@main_router.callback_query(F.data.startswith('skin'))
async def skin_check(callback: types.CallbackQuery):
    _, id_ = callback.data.split('-')
    url = SkinsStorage.get_url_by_id(
        int(id_)
    )
    skin: Skin = await SkinsStorage.get_skin(url)
    cors = [
        callback.message.delete(),
        callback.message.answer_photo(
            skin.image_src,
            caption=skin.item_name,
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text='На торговой площадке',
                        url=skin.url
                    ),
                    InlineKeyboardButton(
                        text='Купить за баллы',
                        callback_data=f'pay-points-skin-{skin.price*config["data"]["one_price"]}-{id_}'
                    )
                ]]
            )
        )
    ]
    for i in cors:
        await i


@main_router.callback_query(F.data.startswith('pay'))
@session_dec
async def pay_callback(callback: types.CallbackQuery, session: AsyncSession, *args, **kwargs):
    _, vendor, action, *data = callback.data.split('-')
    data = "-".join(data)
    vendor = VendorFactory.get_vendor(vendor)(
        user=callback.from_user,
        action=action,
        data=data
    )
    us_id = callback.from_user.id
    message = await vendor.get_message(session)
    await callback.message.answer(message[0])

    async def callback():
        return
    if message[1]:
        await vendor.create_transaction(session, callback)



