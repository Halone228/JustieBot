import asyncio

import loguru
from aiogram import types, F
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.enums import ChatType
from .core import main_router, config
from aiogram.filters import CommandStart, Command, and_f, Filter, or_f
from .skins import Skin, SkinsStorage
from .vendors import VendorFactory
from .database.methods import (
    session_dec,
    increment_count,
    set_added,
    get_or_create,
    get_points,
    add_user,
    add_referrer,
    get_referrals,
    get_active_matches, can_bet, set_bid_for_match, get_match, get_user_bids
)
from loguru import logger
from .redis import redis_db


MAIN_CHAT_ID = -1001743519955


class ChatTypeFilter(Filter):
    def __init__(self, chat_type: ChatType) -> None:
        self.chat_type = chat_type

    async def __call__(self, message, *args, **kwargs):
        return message.chat.type == self.chat_type


cache_points: dict[int, float] = dict()

@session_dec
async def update_cache_points(session: AsyncSession):
    while True:
        try:
            cache_points = {}
            async with redis_db.client.client() as client:
                cur = b'0'
                while cur:
                    cur, keys = await client.scan(cur, match='user:*')
                    for i in keys:
                        i: bytes
                        await asyncio.sleep(0)
                        data = await redis_db.client.get(i)
                        i: str = i.decode()
                        await redis_db.client.set(i, 0)
                        cache_points[int(i.split(':')[1])] = float(data)/100
            await asyncio.sleep(30)
            await increment_count(session, cache_points)
            cache_points.clear()
        except Exception as e:
            loguru.logger.exception(e)

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
    await get_or_create(message, session)
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
    await message.answer(config['texts']['help_message'])
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
    points = await get_points(session, user_id)
    mes: str = config['texts']['account']
    data = {
        'points': points+(float((await redis_db.client.get(f'user:{user_id}') or '0'))/100),
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
    skins: dict[str, float] = {}
    new_message = await message.answer('Получаем информацию о скинах...')
    cur = b'0'
    async with redis_db.client.client() as client:
        while cur:
            cur, keys = await client.scan(cur, match='skin:*')
            for i in keys:
                i: bytes
                data = await client.get(i)
                key = i.decode().replace('skin:', '')
                data = float(data)
                skins[key] = data

    builder = InlineKeyboardBuilder()
    SkinsStorage.fill_urls(skins)
    for i in skins:
        i: Skin = await SkinsStorage.get_skin(i)
        builder.row(InlineKeyboardButton(
            text=i.item_name,
            callback_data=f'skin-{i.id}'
        ))
    await new_message.delete()
    await message.answer(
        text='Купить скины за баллы',
        reply_markup=builder.as_markup()
    )


@main_router.message(command_dialog_filter('ref'))
@session_dec
async def ref(message: types.Message, session: AsyncSession, *args, **kwargs):
    args = message.text.split(' ')
    if len(args) == 2:
        try:
            referrer_id = int(args[1])
            res = await add_referrer(session, message.from_user.id, referrer_id)
        except ValueError:
            res = -1
        if res == -1:
            await message.answer('Неверно указан рефер!')
        if res == 0:
            await message.answer('У вас уже есть рефер...')
        if res == 1:
            await message.answer('Вы успешно стали рефералом!')
    else:
        message_text: str = config['texts']['ref_message']
        message_text = message_text.format_map({
            'user_id': message.from_user.id,
            'refs_cnt': await get_referrals(session, message.from_user.id)
        })
        await message.answer(message_text)


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
    message = await vendor.get_message(session)
    await callback.message.answer(message[0])
    if message[1]:
        await vendor.create_transaction(session, None)
    await callback.message.delete()


@main_router.message(command_dialog_filter('bets'))
@main_router.callback_query(F.data.startswith('bets'))
@session_dec
async def show_matches(message: types.Message | types.CallbackQuery, session: AsyncSession, *args, **kwargs):
    if isinstance(message, types.CallbackQuery):
        message = message.message
    matches = await get_active_matches(session)
    data = [i for i in matches]
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text='Посмотреть свои ставки',
        callback_data='view-bids'
    ))
    result_string = "\n".join(repr(mat) for mat in data) if len(data) else "Нет активных матчей"
    help_string = ("Для того чтобы сделать ставку, нужно использовать команду "
                   "/bet <code>{Номер матча}</code> <code>{Ставка в баллах}</code>\nПример: /bet 5 500")
    result_string += '\n' + help_string
    await message.answer(result_string, reply_markup=builder.as_markup())


@main_router.callback_query(F.data == 'view-bids')
@session_dec
async def view_bets(callback: types.CallbackQuery, session: AsyncSession, *args, **kwargs):
    matches = await get_user_bids(session, callback.from_user.id)
    data = [i for i in matches]

    message = '\n'.join((f'{idx}. ' + i.get_info() for idx, i in enumerate(data, start=1))) if data else "У вас нет активных ставок"
    message = 'Вот ваши активные ставки:\n' + message
    await callback.message.answer(message)


@main_router.message(command_dialog_filter('bet'))
@session_dec
async def set_bet(message: types.Message, session: AsyncSession, *args, **kwargs):
    _, match_id, price, *args = message.text.split(' ')
    price = price.replace(',', '.')
    if len(args) > 0:
        await message.answer("Неверный формат введёных данных")
    try:
        match_id = int(match_id)
    except ValueError:
        await message.answer('Номер матча должен быть числом')
    try:
        price = float(price)
    except ValueError:
        await message.answer("Неверный формат количества баллов(формат должен быть действительным числом)")
    answers = {
        0: '',
        -1: 'Нет такого матча.',
        -2: 'Матч уже завершёню',
        -3: 'Время ставок на матч уже закончилось!',
        -4: 'Ставка на этот матч уже присутсвует.'
    }
    can = await can_bet(session, match_id, message.from_user.id)
    answer = answers[can[1]]
    if can[0]:
        match = await get_match(session, match_id)
        keyboard_b = InlineKeyboardBuilder()
        keyboard_b.row(
            InlineKeyboardButton(
                text='Сделать ставку!',
                callback_data=f'pay-bid-set-{price}-{match_id}'
            )
        )
        await message.answer(
            f'{repr(match)}\nСтавка: {price}',
            reply_markup=keyboard_b.as_markup()
        )
    else:
        await message.answer(answer)


@main_router.message()
@session_dec
async def count_messages(message: types.Message, session: AsyncSession, *args, **kwargs):
    if message.new_chat_members:
        await message.answer(config['texts']['help_message'])

        for user in message.new_chat_members:
            await add_user(
                session,
                user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
        return
    name = f"user:{message.from_user.id}"
    if not await redis_db.client.exists(name):
        await redis_db.client.set(name, 0)
    await redis_db.client.incrby(name,
                                 len(message.text) if message.text else message.caption if message.caption else 0)
