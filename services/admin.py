from aiogram import Router, F
from aiogram.filters import Command
from functools import wraps
from aiogram.types import Message, CallbackQuery
import logging
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db.database import execute_query

router = Router()

ADMINS = [
    7803271080,
    7166218892,
    1990691070
]


async def notify_admins(bot, text: str, reply_markup=None, parse_mode=None):
    """Send a message only to admins (used instead of replying in groups)."""
    count = 0
    for admin_id in ADMINS:
        try:
            await bot.send_message(chat_id=admin_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            count += 1
        except Exception as e:
            logging.warning(f"Не удалось отправить админам ({admin_id}): {e}")
    return count


def suppress_group(func):
    """Decorator: if a command is invoked in a group, don't reply in group — notify admins instead."""
    @wraps(func)
    async def wrapper(message, *args, **kwargs):
        try:
            chat_type = message.chat.type
        except Exception:
            chat_type = None

        if chat_type in ("group", "supergroup"):
            text = (
                f"Команда вызвана в группе '{message.chat.title or message.chat.id}':\n"
                f"{message.text or ''}"
            )
            await notify_admins(message.bot, text)
            return

        return await func(message, *args, **kwargs)

    return wrapper


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def register_chat(message: Message):
    chat_id = message.chat.id
    title = message.chat.title or "Без названия"
    
    await execute_query("""
        INSERT INTO chats (chat_id, title) VALUES ($1, $2)
        ON CONFLICT (chat_id) DO UPDATE SET title = EXCLUDED.title
    """, chat_id, title)


def admin_only(func):
    @wraps(func)
    async def wrapper(message_or_call, *args, **kwargs):
        user_id = None
        if isinstance(message_or_call, Message):
            user_id = message_or_call.from_user.id
        elif isinstance(message_or_call, CallbackQuery):
            user_id = message_or_call.from_user.id
        else:
            return

        if user_id not in ADMINS:
            if isinstance(message_or_call, Message):
                await message_or_call.reply("❌ Only admin can use this command")
            elif isinstance(message_or_call, CallbackQuery):
                await message_or_call.answer("❌ Only admin can use this command", show_alert=True)
            return

        return await func(message_or_call, *args, **kwargs)
    return wrapper


@router.callback_query(F.data=="broadcast")
@admin_only
async def broadcast_button(call: CallbackQuery):
    text = "Текст рассылки"  # Можно брать из предыдущего сообщения или заранее задавать
    # Перенаправляем рассылку только администраторам
    count = await notify_admins(call.bot, text)
    await call.message.edit_text(f"✅ Сообщение отправлено админам: {count} пользователя")
    await call.answer()


@router.message(Command("broadcast_drivers"))
@admin_only
async def broadcast_drivers_command(message: Message):
    """Команда для начала рассылки водителям"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Отправить рассылку", callback_data="send_broadcast_drivers")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")]
    ])
    
    await message.reply(
        "📨 Введите текст рассылки для групп водителей:\n\n"
        "Укажите текст сообщения, которое будет отправлено всем группам водителей.",
        reply_markup=keyboard
    )


@router.callback_query(F.data=="send_broadcast_drivers")
@admin_only
async def send_broadcast_drivers(call: CallbackQuery):
    """Рассылка сообщений всем группам водителей"""
    text = call.message.text or "Сообщение для водителей"
    # Отправляем только администраторам вместо групп
    count = await notify_admins(call.bot, text, parse_mode="Markdown")
    failed = len(ADMINS) - count

    await call.message.edit_text(
        f"✅ Рассылка (адм) завершена!\n\n"
        f"📤 Отправлено: {count} админов\n"
        f"❌ Ошибок: {failed}",
        reply_markup=None
    )
    await call.answer("Рассылка завершена!")


@router.callback_query(F.data=="cancel_broadcast")
@admin_only
async def cancel_broadcast(call: CallbackQuery):
    """Отмена рассылки"""
    await call.message.edit_text("❌ Рассылка отменена")
    await call.answer()


@router.message(Command("get_drivers_groups"))
@admin_only
async def get_drivers_groups(message: Message):
    """Получить список всех групп водителей"""
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT chat_id, title 
            FROM chats
            WHERE title LIKE '%driver%' OR title LIKE '%водитель%'
            OR title LIKE '%Driver%' OR title LIKE '%Водитель%'
        """)
        groups = cursor.fetchall()

    if not groups:
        await message.reply("❌ Групп водителей не найдено")
        return

    text = "📋 *Группы водителей:*\n\n"
    for chat_id, title in groups:
        text += f"• {title} (ID: `{chat_id}`)\n"

    await message.reply(text, parse_mode="Markdown")
