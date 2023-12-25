import asyncio

from aiogram import types, F
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.enums import ChatType
from .core import main_router, config
from aiogram.filters import CommandStart, Command, and_f, Filter, or_f
from .skins import Skin, SkinsStorage
from .vendors import VendorFactory
from .database.methods import session_dec, increment_count, set_added, get_or_create, get_points
from loguru import logger


MAIN_CHAT_ID = -1001743519955


class ChatTypeFilter(Filter):
    def __init__(self, chat_type: ChatType) -> None:
        self.chat_type = chat_type

    async def __call__(self, message, *args, **kwargs):
        return message.chat.type == self.chat_type


cache_points: dict[int, float] = dict()


@session_dec
async def update_cache_points(session: AsyncSession):
    global cache_points
    while True:
        await asyncio.sleep(3600)
        await increment_count(session, cache_points)
        cache_points.clear()


filter_group = or_f(
    ChatTypeFilter(ChatType.GROUP),
    ChatTypeFilter(ChatType.SUPERGROUP),
    ChatTypeFilter(ChatType.SENDER)
)


def command_dialog_filter(command: str):
    return and_f(Command(command), ChatTypeFilter(ChatType.PRIVATE))


### Система подсчета сообщений

###############################


@main_router.message(command_dialog_filter("buy_vip"))
@main_router.callback_query(F.data == 'pod')
async def buy_vip_menu(message: types.Message | types.CallbackQuery):
    if not isinstance(message, types.Message):
        message = message.message
    builder = InlineKeyboardBuilder()
    data = {
        'bets': 'JastieBets',
        'sport': "JastieSport"
    }
    add_text = '\n'
    for i in data.values():
        add_text += f'{i}: 5000 баллов\n'
    for k, v in data.items():
        builder.row(
            InlineKeyboardButton(
                text=f"VIP-канал {v} -50%",
                callback_data=f'pay-semipoints-vip-5000-{k}'
            )
        )
    await message.answer(
        text=config['texts']['buy_vip_menu']+add_text,
        reply_markup=builder.as_markup()
    )


@main_router.message(command_dialog_filter('start'))
@session_dec
async def start(message: types.Message, session: AsyncSession, *args, **kwargs):
    await get_or_create(message.from_user.id, session)
    builder = InlineKeyboardBuilder()
    if message.from_user.id != message.chat.id:
        return
    builder.row(
        InlineKeyboardButton(
            text='Подписка на VIP-канал',
            callback_data='pod'
        )
    )
    builder.row(
        InlineKeyboardButton(
            text='Скины',
            callback_data='skin'
        )
    )
    builder.row(
        InlineKeyboardButton(
            text='Информация о аккаунте',
            callback_data='acc'
        )
    )
    await message.answer(
        text=config['texts']['start'],
        reply_markup=builder.as_markup()
    )


@main_router.message(command_dialog_filter('account'))
@main_router.callback_query(F.data == 'acc')
@session_dec
async def account_info(message: types.Message | types.CallbackQuery, session: AsyncSession, *args, **kwargs):
    global cache_points
    user_id = message.from_user.id
    if not isinstance(message, types.Message):
        message = message.message
    logger.debug(type(session))
    points = await get_points(session, user_id)
    mes: str = config['texts']['account']
    data = {
        'points': points+cache_points.get(user_id, 0),
        'user_name': message.from_user.full_name
    }
    await message.answer(
        text=mes.format_map(
            data
        )
    )


@main_router.message(command_dialog_filter('skins'))
@main_router.callback_query(F.data == 'skin')
async def show_skins(message: types.Message | types.CallbackQuery):
    if not isinstance(message, types.Message):
        message = message.message
    skins: dict[str, int] = config['skins']
    builder = InlineKeyboardBuilder()
    SkinsStorage.fill_urls(skins)
    for i in skins:
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
            caption=skin.item_name+f'\nЦена: {skin.price*config["data"]["one_price"]} баллов',
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


@main_router.message(filter_group)
@session_dec
async def count_messages(message: types.Message, session: AsyncSession, *args, **kwargs):
    global cache_points
    print(message.from_user.id)
    cache_points[message.from_user.id] = cache_points.get(message.from_user.id, 0) + len(message.text)/100
    # await increment_count(session, message)